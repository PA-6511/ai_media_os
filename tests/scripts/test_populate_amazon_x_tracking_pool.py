from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / ".venv/bin/python"
ALEMBIC = ROOT / ".venv/bin/alembic"
SCRIPT = ROOT / "scripts/populate_amazon_x_tracking_pool.py"
TARGET_REVISION = "d2e7c4a91b30"


def migrated_database(tmp_path: Path) -> Path:
    database = tmp_path / "tracking-pool.db"
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_URL": f"sqlite:///{database}",
            "PYTHONPATH": str(ROOT),
            "AI_MEDIA_OS_TESTING": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    result = subprocess.run(
        [str(ALEMBIC), "upgrade", TARGET_REVISION],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return database


def run_cli(
    database: Path,
    input_path: Path,
    *arguments: str,
    extra_environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_BACKEND": "sqlite",
            "DATABASE_URL": f"sqlite:///{database}",
            "PYTHONPATH": str(ROOT),
            "AI_MEDIA_OS_TESTING": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    environment.update(extra_environment or {})
    return subprocess.run(
        [
            str(PYTHON),
            str(SCRIPT),
            str(input_path),
            "--database",
            str(database),
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def pool_rows(database: Path) -> list[tuple[object, ...]]:
    with sqlite3.connect(database) as connection:
        return connection.execute(
            "SELECT tracking_id,status,experiment_id,variant_id,"
            "wordpress_post_id,assigned_at "
            "FROM amazon_x_tracking_id_pool ORDER BY tracking_id"
        ).fetchall()


def insert_pool_row(
    database: Path,
    *,
    tracking_id: str,
    status: str = "AVAILABLE",
) -> None:
    assigned = status == "ASSIGNED"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO amazon_x_tracking_id_pool "
            "(id,tracking_id,status,experiment_id,variant_id,"
            "wordpress_post_id,registered_at,assigned_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                f"fixture-{tracking_id}",
                tracking_id,
                status,
                "a" * 64 if assigned else None,
                "b" * 64 if assigned else None,
                3417 if assigned else None,
                "2026-10-15 00:00:00+00:00",
                "2026-10-15 00:01:00+00:00" if assigned else None,
            ),
        )


def test_default_dry_run_plans_without_writing(
    tmp_path: Path,
) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "tracking-ids.txt"
    input_path.write_text(
        "x-sale-01\nx-sale-02\n",
        encoding="utf-8",
    )

    result = run_cli(database, input_path)

    assert result.returncode == 0, result.stderr
    assert "MODE=DRY_RUN" in result.stdout
    assert "INPUT_ROWS=2" in result.stdout
    assert "VALID_ROWS=2" in result.stdout
    assert "UNIQUE_TRACKING_IDS=2" in result.stdout
    assert "PLANNED_INSERT_ROWS=2" in result.stdout
    assert pool_rows(database) == []


def test_database_target_must_be_explicit(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "explicit-database.txt"
    input_path.write_text("x-sale-01\n", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "DATABASE_URL": f"sqlite:///{database}",
            "PYTHONPATH": str(ROOT),
            "AI_MEDIA_OS_TESTING": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )

    result = subprocess.run(
        [str(PYTHON), str(SCRIPT), str(input_path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--database" in result.stderr
    assert pool_rows(database) == []


def test_invalid_tracking_id_is_rejected(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "invalid.txt"
    input_path.write_text("not-valid\n", encoding="utf-8")

    result = run_cli(database, input_path)

    assert result.returncode == 2
    assert "INVALID_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert "RESULT=HOLD" in result.stderr
    assert pool_rows(database) == []


def test_blank_input_row_is_rejected_instead_of_ignored(
    tmp_path: Path,
) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "blank-row.txt"
    input_path.write_text(
        "x-sale-01\n   \nx-sale-02\n",
        encoding="utf-8",
    )

    result = run_cli(database, input_path)

    assert result.returncode == 2
    assert "INPUT_ROWS=3" in result.stdout
    assert "VALID_ROWS=2" in result.stdout
    assert "INVALID_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert "RESULT=HOLD" in result.stderr
    assert pool_rows(database) == []


def test_identical_duplicate_is_reported_once(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "duplicates.txt"
    input_path.write_text("x-sale-01\nx-sale-01\n", encoding="utf-8")

    result = run_cli(database, input_path)

    assert result.returncode == 0, result.stderr
    assert "INPUT_ROWS=2" in result.stdout
    assert "VALID_ROWS=2" in result.stdout
    assert "UNIQUE_TRACKING_IDS=1" in result.stdout
    assert "DUPLICATE_INPUT_ROWS=1" in result.stdout
    assert "PLANNED_INSERT_ROWS=1" in result.stdout


def test_line_with_additional_attribute_is_invalid(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "attribute-conflict.txt"
    input_path.write_text(
        "x-sale-01\nx-sale-01,variant-b\n",
        encoding="utf-8",
    )

    result = run_cli(database, input_path)

    assert result.returncode == 2
    assert "INVALID_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert pool_rows(database) == []


def test_existing_available_row_is_noop(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    insert_pool_row(database, tracking_id="x-sale-01")
    before = pool_rows(database)
    input_path = tmp_path / "existing.txt"
    input_path.write_text("x-sale-01\n", encoding="utf-8")

    result = run_cli(database, input_path)

    assert result.returncode == 0, result.stderr
    assert "ALREADY_EXISTING_ROWS=1" in result.stdout
    assert "EXISTING_COMPATIBLE_ROWS=1" in result.stdout
    assert "PLANNED_INSERT_ROWS=0" in result.stdout
    assert "PLANNED_NOOP_ROWS=1" in result.stdout
    assert pool_rows(database) == before


@pytest.mark.parametrize("status", ["ASSIGNED", "DISABLED"])
def test_existing_non_available_row_fails_closed(
    tmp_path: Path,
    status: str,
) -> None:
    database = migrated_database(tmp_path)
    insert_pool_row(database, tracking_id="x-sale-01", status=status)
    before = pool_rows(database)
    input_path = tmp_path / "conflict.txt"
    input_path.write_text("x-sale-01\n", encoding="utf-8")

    result = run_cli(database, input_path)

    assert result.returncode == 2
    assert "EXISTING_CONFLICT_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert pool_rows(database) == before


def test_execute_inserts_available_rows_and_reports_postconditions(
    tmp_path: Path,
) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "execute.txt"
    input_path.write_text("x-sale-01\nx-sale-02\n", encoding="utf-8")

    result = run_cli(database, input_path, "--execute")

    assert result.returncode == 0, result.stderr
    assert "MODE=EXECUTE" in result.stdout
    assert "INSERTED_ROWS=2" in result.stdout
    assert "UNEXPECTED_UPDATES=0" in result.stdout
    assert "UNEXPECTED_DELETES=0" in result.stdout
    assert "TRACKING_IDS_ALLOCATED=0" in result.stdout
    assert "QUICK_CHECK=ok" in result.stdout
    assert "FOREIGN_KEY_CHECK=0" in result.stdout
    assert pool_rows(database) == [
        ("x-sale-01", "AVAILABLE", None, None, None, None),
        ("x-sale-02", "AVAILABLE", None, None, None, None),
    ]


def test_execute_rerun_is_idempotent(tmp_path: Path) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "rerun.txt"
    input_path.write_text("x-sale-01\nx-sale-02\n", encoding="utf-8")
    first = run_cli(database, input_path, "--execute")
    assert first.returncode == 0, first.stderr
    before = pool_rows(database)

    second = run_cli(database, input_path, "--execute")

    assert second.returncode == 0, second.stderr
    assert "PLANNED_INSERT_ROWS=0" in second.stdout
    assert "PLANNED_NOOP_ROWS=2" in second.stdout
    assert "INSERTED_ROWS=0" in second.stdout
    assert pool_rows(database) == before


def test_execute_preserves_preexisting_disabled_pool_state(
    tmp_path: Path,
) -> None:
    database = migrated_database(
        tmp_path
    )

    insert_pool_row(
        database,
        tracking_id="x-disabled-01",
        status="DISABLED",
    )

    before = pool_rows(
        database
    )

    input_path = (
        tmp_path
        / "preexisting-disabled-state.txt"
    )

    input_path.write_text(
        "x-sale-01\n",
        encoding="utf-8",
    )

    sys.path.insert(
        0,
        str(ROOT / "scripts"),
    )

    try:
        import populate_amazon_x_tracking_pool as population
    finally:
        sys.path.pop(0)

    result = population.run_population(
        database_url=f"sqlite:///{database}",
        input_path=input_path,
        execute=True,
    )

    assert result.plan.planned_insert_rows == 1
    assert result.inserted_rows == 1

    after = pool_rows(
        database
    )

    assert len(after) == len(before) + 1

    # Existing lifecycle history is valid state and must
    # survive a later population unchanged.
    assert all(
        row in after
        for row in before
    )


def test_mid_batch_failure_rolls_back_every_insert(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = migrated_database(tmp_path)
    input_path = tmp_path / "rollback.txt"
    input_path.write_text("x-sale-01\nx-sale-02\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_BACKEND", "sqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    monkeypatch.setenv("AI_MEDIA_OS_TESTING", "1")
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import populate_amazon_x_tracking_pool as population
    finally:
        sys.path.pop(0)

    original = population.AmazonXTrackingIdPoolRepository.register_available
    calls = 0

    def fail_on_second(self, *, tracking_id: str):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected-mid-batch-failure")
        return original(self, tracking_id=tracking_id)

    monkeypatch.setattr(
        population.AmazonXTrackingIdPoolRepository,
        "register_available",
        fail_on_second,
    )

    with pytest.raises(RuntimeError, match="injected-mid-batch-failure"):
        population.run_population(
            database_url=f"sqlite:///{database}",
            input_path=input_path,
            execute=True,
        )

    assert pool_rows(database) == []


@pytest.mark.parametrize(
    "tracking_id",
    [
        "ktkr77-22",
        "watermelon2-22",
    ],
)
@pytest.mark.parametrize(
    "execute",
    [
        False,
        True,
    ],
)
def test_shared_tracking_id_is_rejected(
    tmp_path: Path,
    tracking_id: str,
    execute: bool,
) -> None:
    database = migrated_database(
        tmp_path
    )

    input_path = (
        tmp_path
        / "shared-tracking-id.txt"
    )

    input_path.write_text(
        tracking_id + "\n",
        encoding="utf-8",
    )

    arguments = (
        ("--execute",)
        if execute
        else ()
    )

    result = run_cli(
        database,
        input_path,
        *arguments,
    )

    assert result.returncode == 2
    assert "INVALID_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert "RESULT=HOLD" in result.stderr
    assert pool_rows(database) == []


@pytest.mark.parametrize(
    "shared_tracking_id",
    [
        "ktkr77-22",
        "watermelon2-22",
    ],
)
def test_shared_tracking_id_blocks_entire_execute_batch(
    tmp_path: Path,
    shared_tracking_id: str,
) -> None:
    database = migrated_database(
        tmp_path
    )

    input_path = (
        tmp_path
        / "mixed-shared-batch.txt"
    )

    input_path.write_text(
        (
            "x-sale-01\n"
            + shared_tracking_id
            + "\n"
        ),
        encoding="utf-8",
    )

    result = run_cli(
        database,
        input_path,
        "--execute",
    )

    assert result.returncode == 2
    assert "VALID_ROWS=1" in result.stdout
    assert "INVALID_ROWS=1" in result.stdout
    assert "PLANNED_INSERT_ROWS=1" in result.stdout
    assert "PLANNED_CONFLICT_ROWS=1" in result.stdout
    assert "RESULT=HOLD" in result.stderr

    # No partial registration of the otherwise valid row.
    assert pool_rows(database) == []


def test_bulk_execute_allows_preexisting_disabled_row(
    tmp_path: Path,
) -> None:
    import sqlite3

    database = migrated_database(
        tmp_path
    )

    first_input = (
        tmp_path
        / "first-pool-id.txt"
    )

    first_input.write_text(
        "x-sale-01\n",
        encoding="utf-8",
    )

    first = run_cli(
        database,
        first_input,
        "--execute",
    )

    assert first.returncode == 0

    con = sqlite3.connect(
        database
    )

    try:
        con.execute(
            """
            UPDATE amazon_x_tracking_id_pool
            SET status = 'DISABLED'
            WHERE tracking_id = 'x-sale-01'
            """
        )
        con.commit()
    finally:
        con.close()

    second_input = (
        tmp_path
        / "second-pool-id.txt"
    )

    second_input.write_text(
        "x-sale-02\n",
        encoding="utf-8",
    )

    second = run_cli(
        database,
        second_input,
        "--execute",
    )

    assert second.returncode == 0, (
        second.stdout
        + "\n"
        + second.stderr
    )

    con = sqlite3.connect(
        database
    )

    try:
        rows = con.execute(
            """
            SELECT tracking_id, status
            FROM amazon_x_tracking_id_pool
            ORDER BY tracking_id
            """
        ).fetchall()
    finally:
        con.close()

    assert rows == [
        (
            "x-sale-01",
            "DISABLED",
        ),
        (
            "x-sale-02",
            "AVAILABLE",
        ),
    ]


def test_bulk_execute_allows_preexisting_assigned_row(
    tmp_path: Path,
) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.db.repositories.amazon_x_tracking_id_pool_repository import (
        AmazonXTrackingIdPoolRepository,
    )

    database = migrated_database(
        tmp_path
    )

    first_input = (
        tmp_path
        / "assigned-pool-id.txt"
    )

    first_input.write_text(
        "x-sale-01\n",
        encoding="utf-8",
    )

    first = run_cli(
        database,
        first_input,
        "--execute",
    )

    assert first.returncode == 0

    engine = create_engine(
        f"sqlite:///{database}"
    )

    try:
        with Session(
            engine
        ) as session:
            repo = (
                AmazonXTrackingIdPoolRepository(
                    session
                )
            )

            repo.assign_next_available(
                experiment_id="a" * 64,
                variant_id="b" * 64,
                wordpress_post_id=3417,
            )

            session.commit()
    finally:
        engine.dispose()

    second_input = (
        tmp_path
        / "after-assignment.txt"
    )

    second_input.write_text(
        "x-sale-02\n",
        encoding="utf-8",
    )

    second = run_cli(
        database,
        second_input,
        "--execute",
    )

    assert second.returncode == 0, (
        second.stdout
        + "\n"
        + second.stderr
    )

    import sqlite3

    con = sqlite3.connect(
        database
    )

    try:
        rows = con.execute(
            """
            SELECT tracking_id, status
            FROM amazon_x_tracking_id_pool
            ORDER BY tracking_id
            """
        ).fetchall()
    finally:
        con.close()

    assert rows == [
        (
            "x-sale-01",
            "ASSIGNED",
        ),
        (
            "x-sale-02",
            "AVAILABLE",
        ),
    ]
