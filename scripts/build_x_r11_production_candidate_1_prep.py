from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
    normalize_wordpress_base_url,
)
from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
    json_storage_snapshot,
    sqlite_read_only_url,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)


ROOT = REPOSITORY_ROOT

PRODUCTION_DATABASE_PATH = (
    ROOT / "data/database/ebook_affiliate.db"
).resolve()

PHASE = "X-R11-PRODUCTION-CANDIDATE-1-PREP"

APPROVAL_TABLE = "workflow_approval_requests"

RELEVANT_TABLE_TOKENS = (
    "workflow",
    "approval",
    "review",
    "ebook",
    "item",
    "wordpress",
    "publication",
    "offer",
)

IDENTIFIER_GROUPS = {
    "approval_request_id": (
        "approval_request_id",
        "request_id",
    ),
    "ebook_item_id": (
        "ebook_item_id",
        "item_id",
    ),
    "workflow_id": (
        "workflow_id",
    ),
}

MAX_APPROVAL_ROWS = 50
MAX_RELATED_ROWS_PER_TABLE = 3


class XR11ProductionCandidatePrepError(
    RuntimeError
):
    """Raised when candidate preparation fails."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11ProductionCandidatePrepError(
            message
        )


def is_within(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.resolve().relative_to(
            parent.resolve()
        )
    except ValueError:
        return False

    return True


def assert_diagnostic_output(
    output_root: Path,
    normal_x_fb_root: Path,
) -> None:
    forbidden_roots = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback",
        normal_x_fb_root
        / "exchange/archive/x_post_feedback",
        normal_x_fb_root
        / "exchange/logs",
    )

    for forbidden_root in forbidden_roots:
        require(
            not is_within(
                output_root,
                forbidden_root,
            ),
            (
                "output_root must not be inside "
                "normal X-FB storage"
            ),
        )


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def json_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    if isinstance(value, bytes):
        return value.hex()

    if isinstance(
        value,
        (datetime, date),
    ):
        return value.isoformat()

    return str(value)


def normalize_row(
    row: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: json_value(value)
        for key, value in row.items()
    }


def choose_order_column(
    columns: set[str],
) -> str | None:
    for candidate in (
        "updated_at",
        "created_at",
        "approved_at",
        "requested_at",
        "id",
    ):
        if candidate in columns:
            return candidate

    return None


def read_recent_rows(
    connection: Connection,
    *,
    table_name: str,
    columns: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    order_column = choose_order_column(
        columns
    )

    statement = (
        f"SELECT * FROM "
        f"{quote_identifier(table_name)}"
    )

    if order_column is not None:
        statement += (
            " ORDER BY "
            f"{quote_identifier(order_column)} "
            "DESC"
        )

    statement += " LIMIT :limit"

    rows = connection.execute(
        text(statement),
        {"limit": limit},
    ).mappings().all()

    return [
        normalize_row(dict(row))
        for row in rows
    ]


def extract_identifier_values(
    approval_row: dict[str, Any],
) -> dict[str, Any]:
    values: dict[str, Any] = {}

    for semantic_name, aliases in (
        IDENTIFIER_GROUPS.items()
    ):
        for alias in aliases:
            value = approval_row.get(alias)

            if value not in (
                None,
                "",
            ):
                values[semantic_name] = value
                break

    if (
        "approval_request_id"
        not in values
        and approval_row.get("id")
        not in (None, "")
    ):
        values["approval_request_id"] = (
            approval_row["id"]
        )

    return values


def read_related_rows(
    connection: Connection,
    *,
    table_columns: dict[str, set[str]],
    identifiers: dict[str, Any],
) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []

    for table_name, columns in (
        table_columns.items()
    ):
        lower_table = table_name.lower()

        if not any(
            token in lower_table
            for token in RELEVANT_TABLE_TOKENS
        ):
            continue

        clauses: list[str] = []
        parameters: dict[str, Any] = {}

        for semantic_name, value in (
            identifiers.items()
        ):
            aliases = IDENTIFIER_GROUPS.get(
                semantic_name,
                (),
            )

            for alias in aliases:
                if alias not in columns:
                    continue

                parameter_name = (
                    f"p_{len(parameters)}"
                )
                clauses.append(
                    f"{quote_identifier(alias)} "
                    f"= :{parameter_name}"
                )
                parameters[parameter_name] = (
                    value
                )

        if not clauses:
            continue

        statement = (
            f"SELECT * FROM "
            f"{quote_identifier(table_name)} "
            f"WHERE {' OR '.join(clauses)} "
            "LIMIT :row_limit"
        )
        parameters["row_limit"] = (
            MAX_RELATED_ROWS_PER_TABLE
        )

        rows = connection.execute(
            text(statement),
            parameters,
        ).mappings().all()

        for row in rows:
            related.append(
                {
                    "table": table_name,
                    "row": normalize_row(
                        dict(row)
                    ),
                }
            )

    return related


def first_value(
    rows: list[dict[str, Any]],
    *,
    column_names: tuple[str, ...],
    table_filter: Callable[[str], bool]
    | None = None,
) -> Any:
    for entry in rows:
        table_name = str(
            entry["table"]
        ).lower()

        if (
            table_filter is not None
            and not table_filter(table_name)
        ):
            continue

        row = entry["row"]

        for column_name in column_names:
            value = row.get(column_name)

            if value not in (
                None,
                "",
            ):
                return value

    return None


def derive_candidate_summary(
    *,
    approval_row: dict[str, Any],
    related_rows: list[dict[str, Any]],
    repository_eligible_ids: set[str],
) -> dict[str, Any]:
    approval_request_id = (
        approval_row.get(
            "approval_request_id"
        )
        or approval_row.get("request_id")
        or approval_row.get("id")
    )

    all_rows = [
        {
            "table": APPROVAL_TABLE,
            "row": approval_row,
        },
        *related_rows,
    ]

    approval_status = (
        approval_row.get(
            "approval_status"
        )
        or approval_row.get("status")
    )
    approval_type = (
        approval_row.get("approval_type")
        or approval_row.get("request_type")
        or approval_row.get("type")
    )

    workflow_state = first_value(
        all_rows,
        column_names=(
            "workflow_state",
            "state",
            "status",
        ),
        table_filter=lambda table: (
            "workflow" in table
            and "approval" not in table
        ),
    )

    review_state = first_value(
        all_rows,
        column_names=(
            "review_state",
            "review_status",
        ),
    )

    if review_state is None:
        review_state = first_value(
            all_rows,
            column_names=(
                "state",
                "status",
            ),
            table_filter=lambda table: (
                "review" in table
            ),
        )

    wordpress_status = first_value(
        all_rows,
        column_names=(
            "wordpress_status",
            "wp_status",
        ),
    )
    wordpress_post_id = first_value(
        all_rows,
        column_names=(
            "wordpress_post_id",
            "wp_post_id",
        ),
    )
    excluded = first_value(
        all_rows,
        column_names=(
            "excluded",
            "is_excluded",
        ),
    )
    title = first_value(
        all_rows,
        column_names=(
            "title",
            "book_title",
            "product_title",
        ),
    )
    release_date = first_value(
        all_rows,
        column_names=(
            "release_date",
            "publication_date",
        ),
    )
    ebook_item_id = first_value(
        all_rows,
        column_names=(
            "ebook_item_id",
            "item_id",
        ),
    )

    repository_eligible = (
        str(approval_request_id)
        in repository_eligible_ids
    )

    blockers: list[str] = []

    if approval_status != "APPROVED":
        blockers.append(
            "APPROVAL_STATUS_NOT_APPROVED"
        )

    if approval_type != "REVIEW_READY":
        blockers.append(
            "APPROVAL_TYPE_NOT_REVIEW_READY"
        )

    if workflow_state != "READY":
        blockers.append(
            "WORKFLOW_STATE_NOT_READY_OR_UNKNOWN"
        )

    if review_state != "APPROVED":
        blockers.append(
            "REVIEW_STATE_NOT_APPROVED_OR_UNKNOWN"
        )

    if wordpress_status != "DRAFT":
        blockers.append(
            "WORDPRESS_STATUS_NOT_DRAFT_OR_UNKNOWN"
        )

    try:
        normalized_post_id = int(
            str(wordpress_post_id).strip()
        )
    except (
        TypeError,
        ValueError,
    ):
        normalized_post_id = 0

    if normalized_post_id <= 0:
        blockers.append(
            "WORDPRESS_POST_ID_MISSING_OR_INVALID"
        )

    if excluded in (
        True,
        1,
        "1",
        "true",
        "TRUE",
        "True",
    ):
        blockers.append(
            "CANDIDATE_EXCLUDED"
        )

    if (
        not repository_eligible
        and not blockers
    ):
        blockers.append(
            "REPOSITORY_FILTER_MISMATCH_"
            "OR_UNRESOLVED_RELATION"
        )

    return {
        "approval_request_id": (
            approval_request_id
        ),
        "ebook_item_id": ebook_item_id,
        "title": title,
        "release_date": release_date,
        "approval_status": approval_status,
        "approval_type": approval_type,
        "workflow_state": workflow_state,
        "review_state": review_state,
        "wordpress_status": (
            wordpress_status
        ),
        "wordpress_post_id": (
            wordpress_post_id
        ),
        "excluded": excluded,
        "repository_eligible": (
            repository_eligible
        ),
        "classification": (
            "ELIGIBLE"
            if repository_eligible
            else "BLOCKED_OR_INCOMPLETE"
        ),
        "blockers": blockers,
        "related_rows": related_rows,
    }


def run_x_r11_production_candidate_1_prep(
    *,
    source_database_path: Path,
    expected_production_database_path: Path,
    wordpress_base_url: str,
    output_root: Path,
    normal_x_fb_root: Path = ROOT,
) -> dict[str, Any]:
    source_database_path = (
        source_database_path.resolve()
    )
    expected_production_database_path = (
        expected_production_database_path.resolve()
    )
    output_root = output_root.resolve()
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    require(
        source_database_path
        == expected_production_database_path,
        (
            "source database must exactly match "
            "the fixed production database path"
        ),
    )
    require(
        source_database_path.is_file(),
        (
            "production database is missing: "
            f"{source_database_path}"
        ),
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    assert_diagnostic_output(
        output_root,
        normal_x_fb_root,
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_base_url = (
        normalize_wordpress_base_url(
            wordpress_base_url
        )
    )

    database_sha_before = sha256_file(
        source_database_path
    )
    normal_snapshot_before = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    engine = create_engine(
        sqlite_read_only_url(
            source_database_path
        ),
        connect_args={
            "check_same_thread": False,
        },
    )

    try:
        inspector = inspect(engine)

        table_names = sorted(
            inspector.get_table_names()
        )

        require(
            APPROVAL_TABLE in table_names,
            (
                "workflow_approval_requests "
                "table is missing"
            ),
        )

        table_columns = {
            table_name: {
                str(column["name"])
                for column in (
                    inspector.get_columns(
                        table_name
                    )
                )
            }
            for table_name in table_names
        }

        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            read_service = (
                WorkflowApprovedXDraftReadService(
                    session,
                    wordpress_base_url=(
                        normalized_base_url
                    ),
                )
            )

            repository_eligible_ids = {
                str(value)
                for value in (
                    read_service
                    .find_latest_candidate_ids(
                        limit=10
                    )
                )
            }

            require(
                not session.new,
                "read-only session has new objects",
            )
            require(
                not session.dirty,
                "read-only session has dirty objects",
            )
            require(
                not session.deleted,
                (
                    "read-only session has "
                    "deleted objects"
                ),
            )

        with engine.connect() as connection:
            connection.execute(
                text("PRAGMA query_only = ON")
            )

            approval_rows = read_recent_rows(
                connection,
                table_name=APPROVAL_TABLE,
                columns=table_columns[
                    APPROVAL_TABLE
                ],
                limit=MAX_APPROVAL_ROWS,
            )

            candidates = []

            for approval_row in approval_rows:
                identifiers = (
                    extract_identifier_values(
                        approval_row
                    )
                )
                related_rows = (
                    read_related_rows(
                        connection,
                        table_columns=(
                            table_columns
                        ),
                        identifiers=identifiers,
                    )
                )
                candidates.append(
                    derive_candidate_summary(
                        approval_row=approval_row,
                        related_rows=related_rows,
                        repository_eligible_ids=(
                            repository_eligible_ids
                        ),
                    )
                )

    finally:
        engine.dispose()

    candidates.sort(
        key=lambda candidate: (
            not candidate[
                "repository_eligible"
            ],
            str(
                candidate.get(
                    "release_date"
                )
                or ""
            ),
            str(
                candidate.get(
                    "approval_request_id"
                )
                or ""
            ),
        )
    )

    eligible_candidates = [
        candidate
        for candidate in candidates
        if candidate[
            "repository_eligible"
        ]
    ]

    database_sha_after = sha256_file(
        source_database_path
    )

    require(
        database_sha_before
        == database_sha_after,
        (
            "production database changed "
            "during candidate preparation"
        ),
    )

    normal_snapshot_after = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    require(
        normal_snapshot_before
        == normal_snapshot_after,
        (
            "normal X-FB storage changed "
            "during candidate preparation"
        ),
    )

    if not eligible_candidates:
        status = (
            "PASS_CANDIDATE_PREP_"
            "NO_ELIGIBLE_PRODUCTION_CANDIDATE"
        )
        candidate_state = (
            "NO_ELIGIBLE_CANDIDATE_"
            "BLOCKERS_REPORTED"
        )
    elif len(eligible_candidates) == 1:
        status = (
            "PASS_CANDIDATE_PREP_"
            "ONE_ELIGIBLE_REVIEW_REQUIRED"
        )
        candidate_state = (
            "ONE_ELIGIBLE_CANDIDATE_"
            "NOT_SELECTED"
        )
    else:
        status = (
            "BLOCKED_MULTIPLE_ELIGIBLE_"
            "PRODUCTION_CANDIDATES"
        )
        candidate_state = (
            "MULTIPLE_ELIGIBLE_CANDIDATES_"
            "NO_AUTOMATIC_SELECTION"
        )

    pack_payload = {
        "phase": PHASE,
        "status": (
            "PRODUCTION_CANDIDATE_1_"
            "PREPARATION_PACK_READY"
        ),
        "candidate_state": candidate_state,
        "database_scope": (
            "PRODUCTION_READ_ONLY"
        ),
        "source_database_path": str(
            source_database_path
        ),
        "source_database_sha256": (
            database_sha_after
        ),
        "repository_eligible_candidate_ids": (
            sorted(repository_eligible_ids)
        ),
        "repository_eligible_candidate_count": (
            len(repository_eligible_ids)
        ),
        "approval_request_rows_examined": (
            len(approval_rows)
        ),
        "candidate_summaries": candidates,
        "human_selection_required": True,
        "automatic_selection_allowed": False,
        "candidate_selected": False,
        "candidate_selection_write_allowed": False,
        "workflow_update_allowed": False,
        "approval_update_allowed": False,
        "wordpress_draft_creation_allowed": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "HUMAN-SELECTION"
            if len(eligible_candidates) == 1
            else None
        ),
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CANDIDATE_PREP_"
            "READ_ONLY"
        ),
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    pack = {
        **pack_payload,
        "candidate_prep_pack_digest_sha256": (
            pack_digest
        ),
    }

    pack_path = (
        output_root
        / (
            "x_r11_production_candidate_1_"
            "prep_pack.json"
        )
    )
    result_path = (
        output_root
        / (
            "x_r11_production_candidate_1_"
            "prep_result.json"
        )
    )

    atomic_write_json(
        pack_path,
        pack,
    )

    result = {
        "phase": PHASE,
        "status": status,
        "candidate_state": candidate_state,
        "database_scope": (
            "PRODUCTION_READ_ONLY"
        ),
        "source_database_path": str(
            source_database_path
        ),
        "source_database_sha256_before": (
            database_sha_before
        ),
        "source_database_sha256_after": (
            database_sha_after
        ),
        "source_database_unchanged": True,
        "approval_request_rows_examined": (
            len(approval_rows)
        ),
        "repository_eligible_candidate_count": (
            len(repository_eligible_ids)
        ),
        "repository_eligible_candidate_ids": (
            sorted(repository_eligible_ids)
        ),
        "candidate_prep_pack_path": str(
            pack_path
        ),
        "candidate_prep_pack_digest_sha256": (
            pack_digest
        ),
        "human_selection_required": True,
        "automatic_selection_allowed": False,
        "candidate_selected": False,
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "normal_x_fb_storage_modified": False,
        "normal_x_fb_write_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_CANDIDATE_PREP_"
            "READ_ONLY"
        ),
    }

    atomic_write_json(
        result_path,
        result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--expected-production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--wordpress-base-url",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--normal-x-fb-root",
        type=Path,
        default=ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            run_x_r11_production_candidate_1_prep(
                source_database_path=(
                    args.source_db
                ),
                expected_production_database_path=(
                    args.expected_production_db
                ),
                wordpress_base_url=(
                    args.wordpress_base_url
                ),
                output_root=args.output_root,
                normal_x_fb_root=(
                    args.normal_x_fb_root
                ),
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "candidate_selected": False,
                    "database_write": False,
                    "workflow_write": False,
                    "approval_write": False,
                    "wordpress_write": False,
                    "normal_x_fb_write_allowed": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_execution": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
