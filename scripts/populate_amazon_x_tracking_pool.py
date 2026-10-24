from __future__ import annotations

"""Manually plan or execute initial Amazon X Tracking ID pool population."""

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.db.models.amazon_x_tracking_id_pool import AmazonXTrackingIdPool
from app.db.access_guard import assert_database_target_allowed
from app.db.repositories.amazon_x_tracking_id_pool_repository import (
    AmazonXTrackingIdPoolError,
    AmazonXTrackingIdPoolRepository,
    validate_controlled_tracking_id,
)


@dataclass(frozen=True)
class PopulationPlan:
    input_rows: int
    valid_rows: int
    unique_tracking_ids: int
    duplicate_input_rows: int
    invalid_rows: int
    already_existing_rows: int
    existing_compatible_rows: int
    existing_conflict_rows: int
    planned_insert_rows: int
    planned_noop_rows: int
    planned_conflict_rows: int


@dataclass(frozen=True)
class PopulationExecution:
    plan: PopulationPlan
    inserted_rows: int
    unexpected_updates: int
    unexpected_deletes: int
    tracking_ids_allocated: int
    quick_check: str
    foreign_key_check: int


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Populate the Amazon X Tracking ID pool; dry-run by default."
    )
    parser.add_argument("input", type=Path, help="UTF-8 text file, one Tracking ID per line.")
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Explicit SQLite database path.",
    )
    parser.add_argument("--execute", action="store_true", help="Commit the planned inserts.")
    return parser.parse_args(argv)


def read_tracking_ids(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def _is_valid_controlled_tracking_id(
    value: str,
) -> bool:
    try:
        validate_controlled_tracking_id(
            value
        )
    except AmazonXTrackingIdPoolError:
        return False

    return True


def build_plan(session: Session, tracking_ids: list[str]) -> PopulationPlan:
    counts = Counter(tracking_ids)
    unique_ids = list(counts)
    valid_ids = [
        value
        for value in unique_ids
        if _is_valid_controlled_tracking_id(
            value
        )
    ]
    invalid_rows = sum(
        counts[value]
        for value in unique_ids
        if value not in valid_ids
    )
    existing = {
        row.tracking_id: row
        for row in session.scalars(
            select(AmazonXTrackingIdPool).where(
                AmazonXTrackingIdPool.tracking_id.in_(valid_ids)
            )
        )
    } if valid_ids else {}
    compatible = {
        value
        for value, row in existing.items()
        if row.status == "AVAILABLE"
        and row.experiment_id is None
        and row.variant_id is None
        and row.wordpress_post_id is None
        and row.assigned_at is None
    }
    conflicts = set(existing) - compatible
    inserts = set(valid_ids) - set(existing)
    return PopulationPlan(
        input_rows=len(tracking_ids),
        valid_rows=sum(counts[value] for value in valid_ids),
        unique_tracking_ids=len(valid_ids),
        duplicate_input_rows=sum(count - 1 for count in counts.values() if count > 1),
        invalid_rows=invalid_rows,
        already_existing_rows=len(existing),
        existing_compatible_rows=len(compatible),
        existing_conflict_rows=len(conflicts),
        planned_insert_rows=len(inserts),
        planned_noop_rows=len(compatible),
        planned_conflict_rows=len(conflicts) + invalid_rows,
    )


def print_plan(plan: PopulationPlan, *, execute: bool) -> None:
    print(f"MODE={'EXECUTE' if execute else 'DRY_RUN'}")
    for field in plan.__dataclass_fields__:
        print(f"{field.upper()}={getattr(plan, field)}")


def _row_state(row: AmazonXTrackingIdPool) -> tuple[object, ...]:
    return (
        row.tracking_id,
        row.status,
        row.experiment_id,
        row.variant_id,
        row.wordpress_post_id,
        row.registered_at,
        row.assigned_at,
    )


def run_population(
    *,
    database_url: str,
    input_path: Path,
    execute: bool,
) -> PopulationPlan | PopulationExecution:
    tracking_ids = read_tracking_ids(input_path)
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            if not execute:
                return build_plan(session, tracking_ids)

            with session.begin():
                plan = build_plan(session, tracking_ids)
                if plan.invalid_rows or plan.existing_conflict_rows:
                    raise ValueError("population_plan_conflict")

                before_rows = {
                    row.id: _row_state(row)
                    for row in session.scalars(select(AmazonXTrackingIdPool))
                }
                repo = AmazonXTrackingIdPoolRepository(session)
                inserted = 0
                for tracking_id in dict.fromkeys(tracking_ids):
                    if not _is_valid_controlled_tracking_id(
                        tracking_id
                    ):
                        continue

                    _, created = repo.register_available(
                        tracking_id=tracking_id
                    )
                    inserted += int(created)

                after = list(session.scalars(select(AmazonXTrackingIdPool)))
                after_by_id = {row.id: _row_state(row) for row in after}
                unexpected_updates = sum(
                    after_by_id.get(row_id) != state
                    for row_id, state in before_rows.items()
                    if row_id in after_by_id
                )
                unexpected_deletes = sum(
                    row_id not in after_by_id for row_id in before_rows
                )
                new_rows = [
                    row
                    for row in after
                    if row.id not in before_rows
                ]
                allocated = sum(
                    row.status == "ASSIGNED"
                    or row.variant_id is not None
                    or row.assigned_at is not None
                    for row in new_rows
                )
                non_available = sum(
                    row.status != "AVAILABLE" for row in new_rows
                )
                quick_check = str(
                    session.execute(text("PRAGMA quick_check")).scalar_one()
                )
                foreign_key_check = len(
                    session.execute(text("PRAGMA foreign_key_check")).all()
                )
                if (
                    inserted != plan.planned_insert_rows
                    or len(new_rows) != inserted
                    or unexpected_updates
                    or unexpected_deletes
                    or allocated
                    or non_available
                    or quick_check != "ok"
                    or foreign_key_check
                ):
                    raise RuntimeError("population_postcondition_failed")

            return PopulationExecution(
                plan=plan,
                inserted_rows=inserted,
                unexpected_updates=unexpected_updates,
                unexpected_deletes=unexpected_deletes,
                tracking_ids_allocated=allocated,
                quick_check=quick_check,
                foreign_key_check=foreign_key_check,
            )
    finally:
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    database_path = args.database.expanduser().resolve(strict=False)
    assert_database_target_allowed(
        database_path,
        operation="tracking pool population CLI",
    )
    database_url = f"sqlite:///{database_path}"
    try:
        result = run_population(
            database_url=database_url,
            input_path=args.input,
            execute=args.execute,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        if str(exc) == "population_plan_conflict":
            dry_run = run_population(
                database_url=database_url,
                input_path=args.input,
                execute=False,
            )
            assert isinstance(dry_run, PopulationPlan)
            print_plan(dry_run, execute=args.execute)
            print("RESULT=HOLD", file=sys.stderr)
            return 2
        print(f"ERROR={type(exc).__name__}:{exc}", file=sys.stderr)
        return 2

    plan = result.plan if isinstance(result, PopulationExecution) else result
    print_plan(plan, execute=args.execute)
    if plan.invalid_rows or plan.existing_conflict_rows:
        print("RESULT=HOLD", file=sys.stderr)
        return 2
    if isinstance(result, PopulationExecution):
        print(f"INSERTED_ROWS={result.inserted_rows}")
        print(f"UNEXPECTED_UPDATES={result.unexpected_updates}")
        print(f"UNEXPECTED_DELETES={result.unexpected_deletes}")
        print(f"TRACKING_IDS_ALLOCATED={result.tracking_ids_allocated}")
        print(f"QUICK_CHECK={result.quick_check}")
        print(f"FOREIGN_KEY_CHECK={result.foreign_key_check}")
    print("RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
