from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "MANUAL-INTAKE-HUMAN-REVIEW-PACK"
)

EXPECTED_MANIFEST_PHASE = (
    "X-R11-MANUAL-REAL-SOURCE-DATA-ENTRY"
)

EXPECTED_MANIFEST_STATUS = (
    "ONE_VALID_REAL_SOURCE_ROW_ENTERED_"
    "AWAITING_HUMAN_REVIEW"
)

EXPECTED_VALIDATION_PHASE = (
    "X-R11-MANUAL-REAL-SOURCE-INTAKE-PREP"
)

EXPECTED_VALIDATION_STATUS = (
    "PASS_MANUAL_REAL_SOURCE_INTAKE_"
    "ONE_VALID_CANDIDATE_REVIEW_REQUIRED"
)

REQUIRED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_IMPORT_PREP_ONLY"
)

PRODUCTION_DATABASE_PATH = (
    REPOSITORY_ROOT
    / "data/database/ebook_affiliate.db"
).resolve()

CSV_HEADER = [
    "intake_id",
    "title",
    "volume_label",
    "release_date",
    "publisher",
    "authors",
    "category",
    "source_discovery_url",
    "publisher_confirmation_url",
    "amazon_url",
    "rakuten_kobo_url",
    "dmm_url",
    "description_mode",
    "human_review_state",
]

RETAIL_URL_FIELDS = (
    "amazon_url",
    "rakuten_kobo_url",
    "dmm_url",
)


class XR11HumanReviewPackError(RuntimeError):
    """Raised when human-review pack validation fails."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11HumanReviewPackError(
            message
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise XR11HumanReviewPackError(
            f"JSON is invalid: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def load_single_csv_row(
    path: Path,
) -> dict[str, str]:
    require(
        path.is_file(),
        f"input CSV is missing: {path}",
    )

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        require(
            list(reader.fieldnames or [])
            == CSV_HEADER,
            (
                "input CSV header does not match "
                "the fixed contract"
            ),
        )

        rows = [
            {
                key: str(
                    row.get(key) or ""
                ).strip()
                for key in CSV_HEADER
            }
            for row in reader
            if any(
                str(value or "").strip()
                for value in row.values()
            )
        ]

    require(
        len(rows) == 1,
        (
            "input CSV must contain exactly "
            "one candidate row"
        ),
    )

    return rows[0]


def quote_identifier(
    value: str,
) -> str:
    return '"' + value.replace('"', '""') + '"'


def read_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:
    quoted_table = quote_identifier(
        table_name
    )

    rows = connection.execute(
        (
            "PRAGMA table_info("
            f"{quoted_table}"
            ")"
        )
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def find_book_duplicates(
    connection: sqlite3.Connection,
    candidate: dict[str, str],
) -> list[dict[str, Any]]:
    if not table_exists(
        connection,
        "ebook_items",
    ):
        return []

    columns = read_table_columns(
        connection,
        "ebook_items",
    )

    required_columns = {
        "title",
        "release_date",
    }

    if not required_columns.issubset(
        set(columns)
    ):
        return []

    selected_columns = [
        column
        for column in (
            "id",
            "title",
            "release_date",
            "publisher",
            "wordpress_post_id",
            "wordpress_status",
            "excluded",
        )
        if column in columns
    ]

    select_clause = ", ".join(
        quote_identifier(column)
        for column in selected_columns
    )

    statement = (
        f"SELECT {select_clause} "
        "FROM ebook_items "
        "WHERE TRIM(title) = ? "
        "AND TRIM(release_date) = ? "
        "LIMIT 20"
    )

    rows = connection.execute(
        statement,
        (
            candidate["title"],
            candidate["release_date"],
        ),
    ).fetchall()

    return [
        {
            column: row[column]
            for column in selected_columns
        }
        for row in rows
    ]


def find_url_duplicates(
    connection: sqlite3.Connection,
    candidate: dict[str, str],
) -> list[dict[str, Any]]:
    if not table_exists(
        connection,
        "store_offers",
    ):
        return []

    columns = read_table_columns(
        connection,
        "store_offers",
    )

    url_columns = [
        column
        for column in columns
        if "url" in column.lower()
    ]

    if not url_columns:
        return []

    candidate_urls = [
        candidate[field]
        for field in RETAIL_URL_FIELDS
        if candidate.get(field)
    ]

    matches: list[dict[str, Any]] = []

    selected_columns = [
        column
        for column in (
            "id",
            "ebook_item_id",
            "store",
            "store_name",
            "provider",
            *url_columns,
        )
        if column in columns
    ]

    for url_value in candidate_urls:
        for url_column in url_columns:
            select_clause = ", ".join(
                quote_identifier(column)
                for column in selected_columns
            )

            statement = (
                f"SELECT {select_clause} "
                "FROM store_offers "
                f"WHERE {quote_identifier(url_column)} = ? "
                "LIMIT 20"
            )

            rows = connection.execute(
                statement,
                (url_value,),
            ).fetchall()

            for row in rows:
                matches.append(
                    {
                        "matched_url_column": (
                            url_column
                        ),
                        "matched_url": url_value,
                        "row": {
                            column: row[column]
                            for column
                            in selected_columns
                        },
                    }
                )

    return matches


def run_human_review_pack(
    *,
    input_csv_path: Path,
    policy_path: Path,
    manifest_path: Path,
    validation_result_path: Path,
    production_database_path: Path,
    expected_production_database_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    input_csv_path = (
        input_csv_path.resolve()
    )
    policy_path = policy_path.resolve()
    manifest_path = manifest_path.resolve()
    validation_result_path = (
        validation_result_path.resolve()
    )
    production_database_path = (
        production_database_path.resolve()
    )
    expected_production_database_path = (
        expected_production_database_path.resolve()
    )
    output_root = output_root.resolve()

    require(
        production_database_path
        == expected_production_database_path,
        (
            "production database path must "
            "exactly match the fixed path"
        ),
    )
    require(
        production_database_path.is_file(),
        (
            "production database is missing: "
            f"{production_database_path}"
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

    policy = load_json_object(
        policy_path
    )
    manifest = load_json_object(
        manifest_path
    )
    validation = load_json_object(
        validation_result_path
    )
    candidate = load_single_csv_row(
        input_csv_path
    )

    require(
        manifest.get("phase")
        == EXPECTED_MANIFEST_PHASE,
        "manifest phase is invalid",
    )
    require(
        manifest.get("status")
        == EXPECTED_MANIFEST_STATUS,
        "manifest status is invalid",
    )
    require(
        manifest.get("row_entered")
        is True,
        "manifest row_entered must be true",
    )
    require(
        manifest.get("candidate_selected")
        is False,
        (
            "manifest candidate_selected "
            "must be false"
        ),
    )
    require(
        manifest.get("production_status")
        == "NO_GO",
        (
            "manifest production_status "
            "must remain NO_GO"
        ),
    )
    require(
        manifest.get(
            "database_import_allowed"
        )
        is False,
        (
            "manifest database_import_allowed "
            "must be false"
        ),
    )
    require(
        manifest.get(
            "wordpress_draft_creation_allowed"
        )
        is False,
        (
            "manifest WordPress write "
            "must remain prohibited"
        ),
    )
    require(
        manifest.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "manifest normal X-FB write "
            "must remain prohibited"
        ),
    )

    input_csv_sha256 = sha256_file(
        input_csv_path
    )
    policy_file_sha256 = sha256_file(
        policy_path
    )

    require(
        manifest.get(
            "input_csv_current_sha256"
        )
        == input_csv_sha256,
        (
            "input CSV SHA does not match "
            "the manifest"
        ),
    )
    require(
        manifest.get(
            "policy_snapshot_sha256"
        )
        == policy_file_sha256,
        (
            "policy file SHA does not match "
            "the manifest"
        ),
    )

    require(
        validation.get("phase")
        == EXPECTED_VALIDATION_PHASE,
        "validation phase is invalid",
    )
    require(
        validation.get("status")
        == EXPECTED_VALIDATION_STATUS,
        "validation status is invalid",
    )
    require(
        validation.get(
            "valid_candidate_count"
        )
        == 1,
        (
            "validation must contain exactly "
            "one valid candidate"
        ),
    )
    require(
        validation.get(
            "candidate_selected"
        )
        is False,
        (
            "validation candidate_selected "
            "must be false"
        ),
    )
    require(
        validation.get(
            "database_import_allowed"
        )
        is False,
        (
            "validation database import "
            "must remain prohibited"
        ),
    )
    require(
        validation.get(
            "production_status"
        )
        == "NO_GO",
        (
            "validation production_status "
            "must remain NO_GO"
        ),
    )

    assessments = validation.get(
        "candidate_assessments"
    )

    require(
        isinstance(assessments, list)
        and len(assessments) == 1,
        (
            "validation must contain exactly "
            "one candidate assessment"
        ),
    )

    assessment = assessments[0]

    require(
        isinstance(assessment, dict),
        (
            "candidate assessment must "
            "be an object"
        ),
    )
    require(
        assessment.get("valid")
        is True,
        (
            "candidate assessment must "
            "be valid"
        ),
    )

    validated_candidate = assessment.get(
        "candidate"
    )

    require(
        validated_candidate == candidate,
        (
            "input CSV candidate differs "
            "from validated candidate"
        ),
    )

    candidate_digest = canonical_digest(
        candidate
    )

    require(
        assessment.get(
            "candidate_digest_sha256"
        )
        == candidate_digest,
        (
            "candidate digest differs "
            "from validation result"
        ),
    )
    require(
        manifest.get(
            "candidate_digest_sha256"
        )
        == candidate_digest,
        (
            "candidate digest differs "
            "from manifest"
        ),
    )

    policy_digest = canonical_digest(
        policy
    )

    require(
        validation.get(
            "policy_digest_sha256"
        )
        == policy_digest,
        (
            "policy canonical digest differs "
            "from validation result"
        ),
    )

    validation_file_sha256 = sha256_file(
        validation_result_path
    )

    database_sha_before = sha256_file(
        production_database_path
    )

    connection = sqlite3.connect(
        (
            "file:"
            + quote(
                str(production_database_path)
            )
            + "?mode=ro"
        ),
        uri=True,
    )
    connection.row_factory = sqlite3.Row

    try:
        connection.execute(
            "PRAGMA query_only = ON"
        )

        book_duplicates = (
            find_book_duplicates(
                connection,
                candidate,
            )
        )
        url_duplicates = (
            find_url_duplicates(
                connection,
                candidate,
            )
        )
    finally:
        connection.close()

    database_sha_after = sha256_file(
        production_database_path
    )

    require(
        database_sha_before
        == database_sha_after,
        (
            "production database changed "
            "during read-only duplicate check"
        ),
    )

    duplicate_match_count = (
        len(book_duplicates)
        + len(url_duplicates)
    )

    if duplicate_match_count > 0:
        status = (
            "BLOCKED_HUMAN_REVIEW_PACK_"
            "DUPLICATE_FOUND"
        )
        review_state = (
            "DUPLICATE_REQUIRES_RESOLUTION"
        )
        authorized_next_phase = None
    else:
        status = (
            "PASS_HUMAN_REVIEW_PACK_READY_"
            "AWAITING_EXPLICIT_APPROVAL"
        )
        review_state = (
            "AWAITING_EXPLICIT_HUMAN_APPROVAL"
        )
        authorized_next_phase = (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "MANUAL-INTAKE-EXPLICIT-APPROVAL"
        )

    review_request_id = (
        "xr11-manual-review-"
        + candidate_digest[:24]
    )

    review_checklist = [
        {
            "check_id": (
                "PUBLISHER_TITLE_VOLUME_MATCH"
            ),
            "state": (
                "PENDING_HUMAN_CONFIRMATION"
            ),
            "expected": (
                f"{candidate['title']} "
                f"{candidate['volume_label']}"
            ).strip(),
            "source_url": candidate[
                "publisher_confirmation_url"
            ],
        },
        {
            "check_id": (
                "PUBLISHER_RELEASE_DATE_MATCH"
            ),
            "state": (
                "PENDING_HUMAN_CONFIRMATION"
            ),
            "expected": candidate[
                "release_date"
            ],
            "source_url": candidate[
                "publisher_confirmation_url"
            ],
        },
        {
            "check_id": (
                "PUBLISHER_AND_AUTHOR_MATCH"
            ),
            "state": (
                "PENDING_HUMAN_CONFIRMATION"
            ),
            "expected_publisher": (
                candidate["publisher"]
            ),
            "expected_authors": (
                candidate["authors"]
            ),
            "source_url": candidate[
                "publisher_confirmation_url"
            ],
        },
        {
            "check_id": (
                "RETAIL_PAGE_IS_EBOOK"
            ),
            "state": (
                "PENDING_HUMAN_CONFIRMATION"
            ),
            "source_url": (
                candidate[
                    "rakuten_kobo_url"
                ]
                or candidate["amazon_url"]
                or candidate["dmm_url"]
            ),
        },
        {
            "check_id": (
                "AFFILIATE_TRACKING_ID_READY"
            ),
            "state": "NOT_VERIFIED",
            "required_before": (
                "WORDPRESS_DRAFT_CREATION"
            ),
        },
        {
            "check_id": (
                "PR_DISCLOSURE_READY"
            ),
            "state": "NOT_VERIFIED",
            "required_before": (
                "WORDPRESS_DRAFT_CREATION"
            ),
        },
    ]

    pack_payload = {
        "phase": PHASE,
        "status": (
            "HUMAN_REVIEW_PACK_READY"
        ),
        "review_state": review_state,
        "review_request_id": (
            review_request_id
        ),
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "input_csv_path": str(
            input_csv_path
        ),
        "input_csv_sha256": (
            input_csv_sha256
        ),
        "policy_path": str(
            policy_path
        ),
        "policy_file_sha256": (
            policy_file_sha256
        ),
        "policy_digest_sha256": (
            policy_digest
        ),
        "manifest_path": str(
            manifest_path
        ),
        "manifest_sha256": sha256_file(
            manifest_path
        ),
        "validation_result_path": str(
            validation_result_path
        ),
        "validation_result_sha256": (
            validation_file_sha256
        ),
        "candidate": candidate,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "production_database_sha256": (
            database_sha_after
        ),
        "production_database_unchanged": (
            True
        ),
        "book_duplicate_matches": (
            book_duplicates
        ),
        "url_duplicate_matches": (
            url_duplicates
        ),
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "review_checklist": (
            review_checklist
        ),
        "human_review_required": True,
        "explicit_approval_required": True,
        "approval_issued": False,
        "approval_consumed": False,
        "candidate_selected": False,
        "automatic_selection_allowed": False,
        "database_import_allowed": False,
        "workflow_update_allowed": False,
        "approval_request_creation_allowed": (
            False
        ),
        "wordpress_draft_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "HUMAN_REVIEW_PACK_ONLY"
        ),
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    pack = {
        **pack_payload,
        "human_review_pack_digest_sha256": (
            pack_digest
        ),
    }

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    pack_path = (
        output_root
        / (
            "x_r11_manual_intake_"
            "human_review_pack.json"
        )
    )
    result_path = (
        output_root
        / (
            "x_r11_manual_intake_"
            "human_review_result.json"
        )
    )

    atomic_write_json(
        pack_path,
        pack,
    )

    result = {
        "phase": PHASE,
        "status": status,
        "review_state": review_state,
        "review_request_id": (
            review_request_id
        ),
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "book_duplicate_match_count": (
            len(book_duplicates)
        ),
        "url_duplicate_match_count": (
            len(url_duplicates)
        ),
        "production_database_sha256_before": (
            database_sha_before
        ),
        "production_database_sha256_after": (
            database_sha_after
        ),
        "production_database_unchanged": (
            True
        ),
        "human_review_pack_path": str(
            pack_path
        ),
        "human_review_pack_digest_sha256": (
            pack_digest
        ),
        "human_review_required": True,
        "explicit_approval_required": True,
        "approval_issued": False,
        "candidate_selected": False,
        "database_import_allowed": False,
        "wordpress_draft_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "approval_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "HUMAN_REVIEW_PACK_ONLY"
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
        "--input-csv",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--policy",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--manifest",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--validation-result",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--expected-production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_human_review_pack(
            input_csv_path=args.input_csv,
            policy_path=args.policy,
            manifest_path=args.manifest,
            validation_result_path=(
                args.validation_result
            ),
            production_database_path=(
                args.production_db
            ),
            expected_production_database_path=(
                args.expected_production_db
            ),
            output_root=args.output_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "approval_issued": False,
                    "candidate_selected": False,
                    "database_import_allowed": False,
                    "wordpress_draft_creation_allowed": (
                        False
                    ),
                    "normal_x_fb_write_allowed": False,
                    "database_write": False,
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
