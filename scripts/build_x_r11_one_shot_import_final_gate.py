from __future__ import annotations

import argparse
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
from scripts.build_x_r11_manual_intake_import_prep import (
    PRODUCTION_DATABASE_PATH,
    read_table_schema,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-FINAL-GATE"
)

EXPECTED_SOURCE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "MANUAL-INTAKE-IMPORT-PREP"
)

EXPECTED_SOURCE_STATUS = (
    "IMPORT_PREP_PACK_READY"
)

EXPECTED_SOURCE_STATE = (
    "IMPORT_PLAN_READY_NOT_EXECUTABLE"
)

REQUIRED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_ONE_SHOT_IMPORT_ONLY"
)

AUTHORIZED_NEXT_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-EXPLICIT-APPROVAL"
)


class XR11OneShotImportFinalGateError(
    RuntimeError
):
    """Raised when the one-shot final gate fails."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11OneShotImportFinalGateError(
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
        raise XR11OneShotImportFinalGateError(
            f"JSON is invalid: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def quote_identifier(
    value: str,
) -> str:
    return '"' + value.replace('"', '""') + '"'


def verify_pack_digest(
    pack: dict[str, Any],
) -> str:
    recorded_digest = pack.get(
        "import_prep_pack_digest_sha256"
    )

    require(
        isinstance(recorded_digest, str)
        and recorded_digest,
        "Import Prep pack digest is missing",
    )

    payload = {
        key: value
        for key, value in pack.items()
        if key
        != "import_prep_pack_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == recorded_digest,
        (
            "Import Prep pack digest "
            "verification failed"
        ),
    )

    return recorded_digest


def table_columns(
    schema: dict[str, Any],
) -> set[str]:
    return {
        str(column["name"])
        for column in schema["columns"]
    }


def query_matches(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    conditions: dict[str, Any],
    match_type: str,
) -> list[dict[str, Any]]:
    if not conditions:
        return []

    where_clause = " AND ".join(
        (
            f"{quote_identifier(column)} "
            "IS NULL"
            if value is None
            else
            f"{quote_identifier(column)} = ?"
        )
        for column, value
        in conditions.items()
    )

    parameters = [
        value
        for value in conditions.values()
        if value is not None
    ]

    rows = connection.execute(
        (
            f"SELECT * FROM "
            f"{quote_identifier(table_name)} "
            f"WHERE {where_clause} "
            "LIMIT 20"
        ),
        parameters,
    ).fetchall()

    return [
        {
            "match_type": match_type,
            "conditions": conditions,
            "row": dict(row),
        }
        for row in rows
    ]


def recheck_duplicates(
    connection: sqlite3.Connection,
    *,
    pack: dict[str, Any],
    ebook_schema: dict[str, Any],
    offer_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    ebook_columns = table_columns(
        ebook_schema
    )
    offer_columns = table_columns(
        offer_schema
    )

    ebook_values = pack[
        "planned_ebook_item_values"
    ]

    if "id" in ebook_columns:
        matches.extend(
            query_matches(
                connection,
                table_name="ebook_items",
                conditions={
                    "id": ebook_values["id"],
                },
                match_type=(
                    "PLANNED_EBOOK_ID_EXISTS"
                ),
            )
        )

    source_identity_columns = {
        "source_name",
        "source_item_id",
    }

    if source_identity_columns.issubset(
        ebook_columns
    ):
        matches.extend(
            query_matches(
                connection,
                table_name="ebook_items",
                conditions={
                    "source_name": (
                        ebook_values[
                            "source_name"
                        ]
                    ),
                    "source_item_id": (
                        ebook_values[
                            "source_item_id"
                        ]
                    ),
                },
                match_type=(
                    "SOURCE_IDENTITY_EXISTS"
                ),
            )
        )

    if {
        "title",
        "release_date",
    }.issubset(ebook_columns):
        matches.extend(
            query_matches(
                connection,
                table_name="ebook_items",
                conditions={
                    "title": (
                        ebook_values["title"]
                    ),
                    "release_date": (
                        ebook_values[
                            "release_date"
                        ]
                    ),
                },
                match_type=(
                    "TITLE_RELEASE_DATE_EXISTS"
                ),
            )
        )

    for offer in pack[
        "planned_store_offers"
    ]:
        values = offer["values"]

        if "id" in offer_columns:
            matches.extend(
                query_matches(
                    connection,
                    table_name="store_offers",
                    conditions={
                        "id": values["id"],
                    },
                    match_type=(
                        "PLANNED_OFFER_ID_EXISTS"
                    ),
                )
            )

        identity_columns = {
            "ebook_item_id",
            "store_name",
            "store_item_id",
        }

        if identity_columns.issubset(
            offer_columns
        ):
            matches.extend(
                query_matches(
                    connection,
                    table_name="store_offers",
                    conditions={
                        "ebook_item_id": (
                            values[
                                "ebook_item_id"
                            ]
                        ),
                        "store_name": (
                            values[
                                "store_name"
                            ]
                        ),
                        "store_item_id": (
                            values[
                                "store_item_id"
                            ]
                        ),
                    },
                    match_type=(
                        "STORE_OFFER_IDENTITY_EXISTS"
                    ),
                )
            )

        if (
            "product_url" in offer_columns
            and values.get("product_url")
        ):
            matches.extend(
                query_matches(
                    connection,
                    table_name="store_offers",
                    conditions={
                        "product_url": (
                            values[
                                "product_url"
                            ]
                        ),
                    },
                    match_type=(
                        "PRODUCT_URL_EXISTS"
                    ),
                )
            )

    return matches


def validate_planned_values(
    pack: dict[str, Any],
) -> None:
    ebook = pack.get(
        "planned_ebook_item_values"
    )

    require(
        isinstance(ebook, dict),
        "planned ebook values are missing",
    )

    expected_ebook_values = {
        "id": (
            "3e4158c3-1c19-5a07-"
            "a5ed-5234a9446db9"
        ),
        "source_name": (
            "x_r11_manual_intake"
        ),
        "source_item_id": (
            "x-r11-real-20260717-"
            "noa-senpai-11"
        ),
        "title": "のあ先輩はともだち。",
        "volume_label": "第11巻",
        "release_date": "2026-07-17",
        "publisher_name": "集英社",
        "author_name": "あきやまえんま",
        "item_type": "tankobon",
        "wordpress_status": "NOT_CREATED",
        "is_excluded": 0,
    }

    for field, expected in (
        expected_ebook_values.items()
    ):
        require(
            ebook.get(field) == expected,
            (
                "planned ebook value mismatch: "
                f"{field}={ebook.get(field)!r}"
            ),
        )

    offers = pack.get(
        "planned_store_offers"
    )

    require(
        isinstance(offers, list)
        and len(offers) == 1,
        (
            "exactly one planned store offer "
            "is required"
        ),
    )

    offer = offers[0]
    values = offer.get("values")

    require(
        isinstance(values, dict),
        "planned store offer values are missing",
    )

    expected_offer_values = {
        "id": (
            "983647ba-0203-5873-"
            "aea8-f7073401dcf9"
        ),
        "ebook_item_id": (
            "3e4158c3-1c19-5a07-"
            "a5ed-5234a9446db9"
        ),
        "store_name": "rakuten_kobo",
        "store_item_id": (
            "6ffa7a8daf403477a5936eb1279e0478"
        ),
        "product_url": (
            "https://books.rakuten.co.jp/"
            "rk/"
            "6ffa7a8daf403477a5936eb1279e0478/"
        ),
        "affiliate_url": None,
    }

    for field, expected in (
        expected_offer_values.items()
    ):
        require(
            values.get(field) == expected,
            (
                "planned store offer mismatch: "
                f"{field}={values.get(field)!r}"
            ),
        )

    require(
        isinstance(
            values.get("last_checked_at"),
            str,
        )
        and values["last_checked_at"],
        (
            "planned last_checked_at "
            "must be present"
        ),
    )

    require(
        offer.get("retail_url_semantics")
        == (
            "PRODUCT_URL_NOT_AFFILIATE_URL"
        ),
        (
            "retail URL semantics "
            "must remain fixed"
        ),
    )


def run_final_gate(
    *,
    import_prep_pack_path: Path,
    production_database_path: Path,
    expected_production_database_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    import_prep_pack_path = (
        import_prep_pack_path.resolve()
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

    pack = load_json_object(
        import_prep_pack_path
    )

    source_pack_digest = (
        verify_pack_digest(pack)
    )

    require(
        pack.get("phase")
        == EXPECTED_SOURCE_PHASE,
        "Import Prep pack phase is invalid",
    )
    require(
        pack.get("status")
        == EXPECTED_SOURCE_STATUS,
        "Import Prep pack status is invalid",
    )
    require(
        pack.get("prep_state")
        == EXPECTED_SOURCE_STATE,
        "Import Prep state is invalid",
    )
    require(
        pack.get("schema_blockers")
        == [],
        (
            "Import Prep pack contains "
            "schema blockers"
        ),
    )
    require(
        pack.get("duplicate_match_count")
        == 0,
        (
            "Import Prep pack contains "
            "duplicate matches"
        ),
    )
    require(
        pack.get(
            "required_next_approval_label"
        )
        == REQUIRED_APPROVAL_LABEL,
        (
            "required approval label "
            "is invalid"
        ),
    )
    require(
        pack.get(
            "one_shot_import_approval_issued"
        )
        is False,
        (
            "one-shot import approval "
            "must remain unissued"
        ),
    )
    require(
        pack.get("execution_allowed")
        is False,
        (
            "source Import Prep must not "
            "allow execution"
        ),
    )
    require(
        pack.get(
            "database_import_allowed"
        )
        is False,
        (
            "source Import Prep must not "
            "allow database import"
        ),
    )
    require(
        pack.get("database_write")
        is False,
        (
            "source Import Prep must not "
            "allow database writes"
        ),
    )
    require(
        pack.get("wordpress_write")
        is False,
        (
            "source Import Prep must not "
            "allow WordPress writes"
        ),
    )
    require(
        pack.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "source Import Prep must not "
            "allow normal X-FB writes"
        ),
    )
    require(
        pack.get("production_status")
        == "NO_GO",
        (
            "source Import Prep production "
            "status must remain NO_GO"
        ),
    )

    approval_evidence = pack.get(
        "approval_evidence"
    )

    require(
        isinstance(
            approval_evidence,
            dict,
        ),
        "Import Prep approval evidence missing",
    )
    require(
        approval_evidence.get(
            "authorizes_import_prep"
        )
        is True,
        (
            "Import Prep approval evidence "
            "is invalid"
        ),
    )
    require(
        approval_evidence.get(
            "authorizes_database_write"
        )
        is False,
        (
            "Import Prep approval must not "
            "authorize database writes"
        ),
    )

    validate_planned_values(pack)

    recorded_database_sha = pack.get(
        "production_database_sha256"
    )

    require(
        isinstance(
            recorded_database_sha,
            str,
        )
        and recorded_database_sha,
        (
            "recorded production database "
            "SHA is missing"
        ),
    )

    database_sha_before = sha256_file(
        production_database_path
    )

    require(
        database_sha_before
        == recorded_database_sha,
        (
            "production database SHA changed "
            "after Import Prep"
        ),
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

        current_ebook_schema = (
            read_table_schema(
                connection,
                "ebook_items",
            )
        )
        current_offer_schema = (
            read_table_schema(
                connection,
                "store_offers",
            )
        )

        current_schema_snapshot = {
            "ebook_items": (
                current_ebook_schema
            ),
            "store_offers": (
                current_offer_schema
            ),
        }

        require(
            canonical_digest(
                current_schema_snapshot
            )
            == canonical_digest(
                pack["schema_snapshot"]
            ),
            (
                "production schema changed "
                "after Import Prep"
            ),
        )

        duplicate_matches = (
            recheck_duplicates(
                connection,
                pack=pack,
                ebook_schema=(
                    current_ebook_schema
                ),
                offer_schema=(
                    current_offer_schema
                ),
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
            "during final gate"
        ),
    )

    duplicate_match_count = len(
        duplicate_matches
    )

    if duplicate_match_count:
        status = (
            "BLOCKED_ONE_SHOT_IMPORT_"
            "FINAL_GATE_DUPLICATE_FOUND"
        )
        gate_state = (
            "DUPLICATE_REQUIRES_RESOLUTION"
        )
        authorized_next_phase = None
    else:
        status = (
            "PASS_ONE_SHOT_IMPORT_FINAL_GATE_"
            "READY_AWAITING_EXPLICIT_APPROVAL"
        )
        gate_state = (
            "FINAL_GATE_READY_NOT_EXECUTABLE"
        )
        authorized_next_phase = (
            AUTHORIZED_NEXT_PHASE
        )

    final_gate_request_id = (
        "xr11-import-gate-"
        + source_pack_digest[:24]
    )

    final_gate_payload = {
        "phase": PHASE,
        "status": (
            "ONE_SHOT_IMPORT_FINAL_GATE_READY"
        ),
        "gate_state": gate_state,
        "final_gate_request_id": (
            final_gate_request_id
        ),
        "source_import_prep_pack_path": str(
            import_prep_pack_path
        ),
        "source_import_prep_pack_sha256": (
            sha256_file(
                import_prep_pack_path
            )
        ),
        "source_import_prep_pack_digest_sha256": (
            source_pack_digest
        ),
        "candidate": pack["candidate"],
        "candidate_digest_sha256": (
            pack[
                "candidate_digest_sha256"
            ]
        ),
        "planned_ebook_id": (
            pack["planned_ebook_id"]
        ),
        "planned_ebook_item_values": (
            pack[
                "planned_ebook_item_values"
            ]
        ),
        "planned_store_offers": (
            pack["planned_store_offers"]
        ),
        "ebook_insert_preview": (
            pack["ebook_insert_preview"]
        ),
        "store_offer_insert_previews": (
            pack[
                "store_offer_insert_previews"
            ]
        ),
        "transaction_plan": (
            pack["transaction_plan"]
        ),
        "rollback_preview": (
            pack["rollback_preview"]
        ),
        "schema_snapshot": (
            pack["schema_snapshot"]
        ),
        "schema_snapshot_digest_sha256": (
            canonical_digest(
                pack["schema_snapshot"]
            )
        ),
        "duplicate_matches": (
            duplicate_matches
        ),
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_pre_execution_database_sha256": (
            database_sha_after
        ),
        "production_database_unchanged": True,
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "approval_scope": (
            "ONE_SHOT_IMPORT_ONLY"
        ),
        "approval_issued": False,
        "approval_consumed": False,
        "approval_expires_on_database_change": (
            True
        ),
        "approval_expires_on_schema_change": (
            True
        ),
        "approval_expires_on_plan_change": (
            True
        ),
        "maximum_ebook_insert_count": 1,
        "maximum_store_offer_insert_count": 1,
        "exact_planned_ebook_id_required": True,
        "exact_planned_offer_ids_required": True,
        "transaction_required": True,
        "rollback_on_any_failure": True,
        "post_insert_verification_required": True,
        "workflow_write_allowed": False,
        "wordpress_write_allowed": False,
        "normal_x_fb_write_allowed": False,
        "x_api_call_allowed": False,
        "x_post_allowed": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "production_execution": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SHOT_IMPORT_FINAL_GATE_"
            "NO_EXECUTION"
        ),
    }

    final_gate_digest = canonical_digest(
        final_gate_payload
    )

    final_gate_pack = {
        **final_gate_payload,
        "final_gate_pack_digest_sha256": (
            final_gate_digest
        ),
    }

    result = {
        "phase": PHASE,
        "status": status,
        "gate_state": gate_state,
        "final_gate_request_id": (
            final_gate_request_id
        ),
        "candidate_digest_sha256": (
            pack[
                "candidate_digest_sha256"
            ]
        ),
        "planned_ebook_id": (
            pack["planned_ebook_id"]
        ),
        "planned_store_offer_count": len(
            pack["planned_store_offers"]
        ),
        "duplicate_match_count": (
            duplicate_match_count
        ),
        "required_pre_execution_database_sha256": (
            database_sha_after
        ),
        "production_database_unchanged": True,
        "final_gate_pack_digest_sha256": (
            final_gate_digest
        ),
        "required_approval_label": (
            REQUIRED_APPROVAL_LABEL
        ),
        "approval_scope": (
            "ONE_SHOT_IMPORT_ONLY"
        ),
        "approval_issued": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "normal_x_fb_write_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "production_execution": False,
        "authorized_next_phase": (
            authorized_next_phase
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SHOT_IMPORT_FINAL_GATE_"
            "NO_EXECUTION"
        ),
    }

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    pack_path = (
        output_root
        / "x_r11_one_shot_import_final_gate_pack.json"
    )
    result_path = (
        output_root
        / "x_r11_one_shot_import_final_gate_result.json"
    )

    atomic_write_json(
        pack_path,
        final_gate_pack,
    )

    result[
        "final_gate_pack_path"
    ] = str(pack_path)

    atomic_write_json(
        result_path,
        result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--import-prep-pack",
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
        result = run_final_gate(
            import_prep_pack_path=(
                args.import_prep_pack
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
                    "execution_allowed": False,
                    "database_import_allowed": False,
                    "database_write": False,
                    "wordpress_write": False,
                    "normal_x_fb_write_allowed": False,
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
