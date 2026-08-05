from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
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
from scripts.build_x_r11_one_shot_import_final_gate import (
    recheck_duplicates,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-RUNNER"
)

EXPECTED_CERTIFICATE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-EXPLICIT-APPROVAL"
)

EXPECTED_CERTIFICATE_STATUS = (
    "APPROVAL_ISSUED_NOT_CONSUMED"
)

EXPECTED_CERTIFICATE_STATE = (
    "ISSUED_NOT_CONSUMED"
)

EXPECTED_FINAL_GATE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-FINAL-GATE"
)

EXPECTED_FINAL_GATE_STATUS = (
    "ONE_SHOT_IMPORT_FINAL_GATE_READY"
)

EXPECTED_FINAL_GATE_STATE = (
    "FINAL_GATE_READY_NOT_EXECUTABLE"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_ONE_SHOT_IMPORT_ONLY"
)

EXPECTED_APPROVAL_SCOPE = (
    "ONE_SHOT_IMPORT_ONLY"
)

DEFAULT_LOCK_ROOT = (
    REPOSITORY_ROOT
    / "exchange/locks/x_r11_one_shot_import"
).resolve()


class XR11OneShotImportRunnerError(
    RuntimeError
):
    """Raised when the one-shot import cannot run safely."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11OneShotImportRunnerError(
            message
        )


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


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
        raise XR11OneShotImportRunnerError(
            f"JSON is invalid: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    label: str,
) -> str:
    recorded_digest = value.get(
        digest_field
    )

    require(
        isinstance(recorded_digest, str)
        and recorded_digest,
        f"{label} digest is missing",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == recorded_digest,
        f"{label} digest verification failed",
    )

    return recorded_digest


def create_exclusive_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        descriptor = os.open(
            path,
            (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
            ),
            0o600,
        )
    except FileExistsError as exc:
        raise XR11OneShotImportRunnerError(
            (
                "approval certificate has already "
                "been claimed or consumed: "
                f"{path}"
            )
        ) from exc

    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                value,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
    except Exception:
        path.unlink(
            missing_ok=True
        )
        raise


def create_database_backup(
    source_path: Path,
    backup_path: Path,
) -> None:
    require(
        not backup_path.exists(),
        (
            "backup path already exists: "
            f"{backup_path}"
        ),
    )

    source = sqlite3.connect(
        (
            "file:"
            + quote(str(source_path))
            + "?mode=ro"
        ),
        uri=True,
    )

    destination = sqlite3.connect(
        backup_path
    )

    try:
        source.backup(destination)

        integrity = destination.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        require(
            integrity is not None
            and integrity[0] == "ok",
            "pre-import database backup is invalid",
        )
    finally:
        destination.close()
        source.close()


def table_count(
    connection: sqlite3.Connection,
    table_name: str,
) -> int:
    row = connection.execute(
        f'SELECT COUNT(*) FROM "{table_name}"'
    ).fetchone()

    return int(row[0])


def insert_exact(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    values: dict[str, Any],
) -> None:
    require(
        values,
        (
            "planned INSERT values are empty: "
            f"{table_name}"
        ),
    )

    columns = list(values)

    quoted_columns = ", ".join(
        f'"{column}"'
        for column in columns
    )

    placeholders = ", ".join(
        "?"
        for _ in columns
    )

    cursor = connection.execute(
        (
            f'INSERT INTO "{table_name}" '
            f"({quoted_columns}) "
            f"VALUES ({placeholders})"
        ),
        [
            values[column]
            for column in columns
        ],
    )

    require(
        cursor.rowcount == 1,
        (
            "unexpected INSERT row count: "
            f"{table_name}:{cursor.rowcount}"
        ),
    )


def verify_exact_row(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    values: dict[str, Any],
) -> None:
    require(
        "id" in values,
        (
            "planned row does not contain "
            f"an ID: {table_name}"
        ),
    )

    row = connection.execute(
        (
            f'SELECT * FROM "{table_name}" '
            'WHERE "id" = ? '
            "LIMIT 1"
        ),
        (values["id"],),
    ).fetchone()

    require(
        row is not None,
        (
            "inserted row was not found: "
            f"{table_name}:{values['id']}"
        ),
    )

    for column, expected in values.items():
        require(
            column in row.keys(),
            (
                "inserted row column is missing: "
                f"{table_name}.{column}"
            ),
        )

        actual = row[column]

        require(
            actual == expected,
            (
                "inserted value mismatch: "
                f"{table_name}.{column}: "
                f"actual={actual!r}, "
                f"expected={expected!r}"
            ),
        )


def validate_source_contracts(
    *,
    certificate: dict[str, Any],
    certificate_path: Path,
    final_gate: dict[str, Any],
    final_gate_path: Path,
    production_database_path: Path,
) -> tuple[str, str]:
    certificate_digest = verify_digest(
        certificate,
        digest_field=(
            "approval_certificate_digest_sha256"
        ),
        label="approval certificate",
    )

    final_gate_digest = verify_digest(
        final_gate,
        digest_field=(
            "final_gate_pack_digest_sha256"
        ),
        label="Final Gate pack",
    )

    require(
        certificate.get("phase")
        == EXPECTED_CERTIFICATE_PHASE,
        "approval certificate phase is invalid",
    )
    require(
        certificate.get("status")
        == EXPECTED_CERTIFICATE_STATUS,
        "approval certificate status is invalid",
    )
    require(
        certificate.get("approval_state")
        == EXPECTED_CERTIFICATE_STATE,
        "approval certificate state is invalid",
    )
    require(
        certificate.get("approval_issued")
        is True,
        "approval certificate is not issued",
    )
    require(
        certificate.get("approval_consumed")
        is False,
        "approval certificate is already consumed",
    )
    require(
        certificate.get("approval_label")
        == EXPECTED_APPROVAL_LABEL,
        "approval label is invalid",
    )
    require(
        certificate.get("approval_scope")
        == EXPECTED_APPROVAL_SCOPE,
        "approval scope is invalid",
    )
    require(
        certificate.get(
            "authorizes_one_shot_database_import"
        )
        is True,
        (
            "certificate does not authorize "
            "one-shot database import"
        ),
    )
    require(
        certificate.get(
            "authorizes_database_write"
        )
        is True,
        (
            "certificate does not authorize "
            "the bounded database write"
        ),
    )
    require(
        certificate.get(
            "authorizes_workflow_write"
        )
        is False,
        (
            "certificate must not authorize "
            "Workflow writes"
        ),
    )
    require(
        certificate.get(
            "authorizes_wordpress_write"
        )
        is False,
        (
            "certificate must not authorize "
            "WordPress writes"
        ),
    )
    require(
        certificate.get(
            "authorizes_normal_x_fb_write"
        )
        is False,
        (
            "certificate must not authorize "
            "normal X-FB writes"
        ),
    )
    require(
        certificate.get("execution_allowed")
        is False,
        (
            "pre-consumption certificate "
            "execution_allowed must be false"
        ),
    )
    require(
        certificate.get(
            "database_import_allowed"
        )
        is False,
        (
            "pre-consumption certificate "
            "database_import_allowed must be false"
        ),
    )
    require(
        certificate.get("production_status")
        == "NO_GO",
        (
            "certificate production status "
            "must remain NO_GO"
        ),
    )

    require(
        final_gate.get("phase")
        == EXPECTED_FINAL_GATE_PHASE,
        "Final Gate phase is invalid",
    )
    require(
        final_gate.get("status")
        == EXPECTED_FINAL_GATE_STATUS,
        "Final Gate status is invalid",
    )
    require(
        final_gate.get("gate_state")
        == EXPECTED_FINAL_GATE_STATE,
        "Final Gate state is invalid",
    )
    require(
        final_gate.get(
            "duplicate_match_count"
        )
        == 0,
        "Final Gate contains duplicates",
    )
    require(
        final_gate.get("approval_issued")
        is False,
        (
            "source Final Gate approval state "
            "must remain unissued"
        ),
    )
    require(
        final_gate.get("execution_allowed")
        is False,
        "source Final Gate must not be executable",
    )
    require(
        final_gate.get(
            "database_import_allowed"
        )
        is False,
        (
            "source Final Gate must not directly "
            "allow database import"
        ),
    )
    require(
        final_gate.get("database_write")
        is False,
        (
            "source Final Gate must not directly "
            "allow database writes"
        ),
    )

    resolved_certificate_gate_path = Path(
        certificate["final_gate_pack_path"]
    ).resolve()

    require(
        resolved_certificate_gate_path
        == final_gate_path,
        (
            "certificate Final Gate path "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "final_gate_pack_sha256"
        )
        == sha256_file(final_gate_path),
        (
            "certificate Final Gate file SHA "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "final_gate_pack_digest_sha256"
        )
        == final_gate_digest,
        (
            "certificate Final Gate digest "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "final_gate_request_id"
        )
        == final_gate.get(
            "final_gate_request_id"
        ),
        (
            "Final Gate request ID mismatch "
            "between certificate and pack"
        ),
    )
    require(
        certificate.get(
            "candidate_digest_sha256"
        )
        == final_gate.get(
            "candidate_digest_sha256"
        ),
        (
            "candidate digest mismatch "
            "between certificate and pack"
        ),
    )
    require(
        certificate.get("planned_ebook_id")
        == final_gate.get("planned_ebook_id"),
        (
            "planned ebook ID mismatch "
            "between certificate and pack"
        ),
    )

    planned_offer_ids = [
        offer["values"]["id"]
        for offer in final_gate[
            "planned_store_offers"
        ]
    ]

    require(
        certificate.get("planned_offer_ids")
        == planned_offer_ids,
        (
            "planned offer IDs mismatch "
            "between certificate and pack"
        ),
    )
    require(
        certificate.get(
            "maximum_ebook_insert_count"
        )
        == 1,
        (
            "maximum ebook INSERT count "
            "must be exactly 1"
        ),
    )
    require(
        certificate.get(
            "maximum_store_offer_insert_count"
        )
        == 1,
        (
            "maximum store-offer INSERT count "
            "must be exactly 1"
        ),
    )
    require(
        len(
            final_gate[
                "planned_store_offers"
            ]
        )
        == 1,
        (
            "Final Gate must contain exactly "
            "one planned store offer"
        ),
    )

    required_database_sha = certificate.get(
        "required_pre_execution_database_sha256"
    )

    require(
        required_database_sha
        == final_gate.get(
            "required_pre_execution_database_sha256"
        ),
        (
            "required database SHA mismatch "
            "between certificate and pack"
        ),
    )
    require(
        sha256_file(
            production_database_path
        )
        == required_database_sha,
        (
            "production database changed after "
            "approval certificate issuance"
        ),
    )

    wal_path = Path(
        str(production_database_path)
        + "-wal"
    )

    require(
        (
            not wal_path.exists()
            or wal_path.stat().st_size == 0
        ),
        (
            "non-empty SQLite WAL file exists; "
            "one-shot import is blocked"
        ),
    )

    return (
        certificate_digest,
        final_gate_digest,
    )


def run_one_shot_import(
    *,
    approval_certificate_path: Path,
    production_database_path: Path,
    expected_production_database_path: Path,
    output_root: Path,
    lock_root: Path = DEFAULT_LOCK_ROOT,
    failure_injection_step: str | None = None,
) -> dict[str, Any]:
    approval_certificate_path = (
        approval_certificate_path.resolve()
    )
    production_database_path = (
        production_database_path.resolve()
    )
    expected_production_database_path = (
        expected_production_database_path.resolve()
    )
    output_root = output_root.resolve()
    lock_root = lock_root.resolve()

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

    certificate = load_json_object(
        approval_certificate_path
    )

    certificate_digest_precheck = (
        verify_digest(
            certificate,
            digest_field=(
                "approval_certificate_digest_sha256"
            ),
            label="approval certificate",
        )
    )

    preexisting_lock_path = (
        lock_root
        / f"{certificate_digest_precheck}.json"
    )

    require(
        not preexisting_lock_path.exists(),
        (
            "approval certificate has already "
            "been claimed or consumed: "
            f"{preexisting_lock_path}"
        ),
    )

    final_gate_path = Path(
        certificate.get(
            "final_gate_pack_path",
            "",
        )
    ).resolve()

    final_gate = load_json_object(
        final_gate_path
    )

    (
        certificate_digest,
        final_gate_digest,
    ) = validate_source_contracts(
        certificate=certificate,
        certificate_path=(
            approval_certificate_path
        ),
        final_gate=final_gate,
        final_gate_path=final_gate_path,
        production_database_path=(
            production_database_path
        ),
    )

    current_schema_connection = (
        sqlite3.connect(
            (
                "file:"
                + quote(
                    str(
                        production_database_path
                    )
                )
                + "?mode=ro"
            ),
            uri=True,
        )
    )
    current_schema_connection.row_factory = (
        sqlite3.Row
    )

    try:
        current_schema = {
            "ebook_items": read_table_schema(
                current_schema_connection,
                "ebook_items",
            ),
            "store_offers": read_table_schema(
                current_schema_connection,
                "store_offers",
            ),
        }

        require(
            canonical_digest(current_schema)
            == canonical_digest(
                final_gate["schema_snapshot"]
            ),
            (
                "production schema changed "
                "after Final Gate"
            ),
        )

        preclaim_duplicates = (
            recheck_duplicates(
                current_schema_connection,
                pack=final_gate,
                ebook_schema=(
                    current_schema[
                        "ebook_items"
                    ]
                ),
                offer_schema=(
                    current_schema[
                        "store_offers"
                    ]
                ),
            )
        )

        require(
            preclaim_duplicates == [],
            (
                "duplicate detected before "
                "approval consumption"
            ),
        )
    finally:
        current_schema_connection.close()

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_path = (
        lock_root
        / f"{certificate_digest}.json"
    )

    claim = {
        "phase": PHASE,
        "status": "CLAIMED_NOT_EXECUTED",
        "claimed_at": utc_now(),
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate_digest
        ),
        "final_gate_pack_path": str(
            final_gate_path
        ),
        "final_gate_pack_digest_sha256": (
            final_gate_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_pre_execution_database_sha256": (
            certificate[
                "required_pre_execution_database_sha256"
            ]
        ),
        "planned_ebook_id": (
            certificate["planned_ebook_id"]
        ),
        "planned_offer_ids": (
            certificate["planned_offer_ids"]
        ),
        "database_write_started": False,
        "database_commit_completed": False,
        "approval_consumed": False,
        "production_status": "NO_GO",
    }

    create_exclusive_json(
        lock_path,
        claim,
    )

    backup_path = (
        output_root
        / "ebook_affiliate.pre_import.backup.db"
    )
    result_path = (
        output_root
        / "x_r11_one_shot_import_result.json"
    )
    receipt_path = (
        output_root
        / "x_r11_one_shot_import_receipt.json"
    )

    database_sha_before = sha256_file(
        production_database_path
    )
    committed = False
    connection: sqlite3.Connection | None = None

    try:
        require(
            database_sha_before
            == certificate[
                "required_pre_execution_database_sha256"
            ],
            (
                "production database SHA changed "
                "before backup"
            ),
        )

        create_database_backup(
            production_database_path,
            backup_path,
        )

        backup_sha256 = sha256_file(
            backup_path
        )

        require(
            sha256_file(
                production_database_path
            )
            == database_sha_before,
            (
                "production database changed "
                "while creating backup"
            ),
        )

        connection = sqlite3.connect(
            production_database_path,
            isolation_level=None,
            timeout=30,
        )
        connection.row_factory = sqlite3.Row

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        journal_mode = str(
            connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        ).lower()

        require(
            journal_mode != "wal",
            (
                "SQLite WAL mode is not allowed "
                "for this one-shot runner"
            ),
        )

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        require(
            sha256_file(
                production_database_path
            )
            == database_sha_before,
            (
                "production database changed "
                "before transaction execution"
            ),
        )

        claim[
            "database_write_started"
        ] = True
        claim[
            "transaction_started_at"
        ] = utc_now()

        atomic_write_json(
            lock_path,
            claim,
        )

        transaction_schema = {
            "ebook_items": read_table_schema(
                connection,
                "ebook_items",
            ),
            "store_offers": read_table_schema(
                connection,
                "store_offers",
            ),
        }

        require(
            canonical_digest(
                transaction_schema
            )
            == canonical_digest(
                final_gate["schema_snapshot"]
            ),
            (
                "production schema changed "
                "before INSERT"
            ),
        )

        transaction_duplicates = (
            recheck_duplicates(
                connection,
                pack=final_gate,
                ebook_schema=(
                    transaction_schema[
                        "ebook_items"
                    ]
                ),
                offer_schema=(
                    transaction_schema[
                        "store_offers"
                    ]
                ),
            )
        )

        require(
            transaction_duplicates == [],
            (
                "duplicate detected inside "
                "the one-shot transaction"
            ),
        )

        ebook_count_before = table_count(
            connection,
            "ebook_items",
        )
        offer_count_before = table_count(
            connection,
            "store_offers",
        )

        ebook_values = final_gate[
            "planned_ebook_item_values"
        ]

        planned_offers = final_gate[
            "planned_store_offers"
        ]

        require(
            len(planned_offers) == 1,
            (
                "exactly one store offer "
                "must be planned"
            ),
        )

        insert_exact(
            connection,
            table_name="ebook_items",
            values=ebook_values,
        )

        if (
            failure_injection_step
            == "AFTER_EBOOK_INSERT"
        ):
            raise RuntimeError(
                "test failure after ebook INSERT"
            )

        for offer in planned_offers:
            insert_exact(
                connection,
                table_name="store_offers",
                values=offer["values"],
            )

        verify_exact_row(
            connection,
            table_name="ebook_items",
            values=ebook_values,
        )

        for offer in planned_offers:
            verify_exact_row(
                connection,
                table_name="store_offers",
                values=offer["values"],
            )

        ebook_count_after = table_count(
            connection,
            "ebook_items",
        )
        offer_count_after = table_count(
            connection,
            "store_offers",
        )

        require(
            ebook_count_after
            == ebook_count_before + 1,
            (
                "ebook_items count did not "
                "increase by exactly 1"
            ),
        )
        require(
            offer_count_after
            == offer_count_before + 1,
            (
                "store_offers count did not "
                "increase by exactly 1"
            ),
        )

        foreign_key_errors = [
            dict(row)
            for row in connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
        ]

        require(
            foreign_key_errors == [],
            (
                "foreign-key verification failed: "
                f"{foreign_key_errors}"
            ),
        )

        connection.execute(
            "COMMIT"
        )
        committed = True

        database_sha_after = sha256_file(
            production_database_path
        )

        require(
            database_sha_after
            != database_sha_before,
            (
                "production database SHA did not "
                "change after committed INSERTs"
            ),
        )

        verification_connection = (
            sqlite3.connect(
                (
                    "file:"
                    + quote(
                        str(
                            production_database_path
                        )
                    )
                    + "?mode=ro"
                ),
                uri=True,
            )
        )
        verification_connection.row_factory = (
            sqlite3.Row
        )

        try:
            verify_exact_row(
                verification_connection,
                table_name="ebook_items",
                values=ebook_values,
            )

            for offer in planned_offers:
                verify_exact_row(
                    verification_connection,
                    table_name="store_offers",
                    values=offer["values"],
                )
        finally:
            verification_connection.close()

        receipt_payload = {
            "phase": PHASE,
            "status": (
                "ONE_SHOT_IMPORT_COMMITTED"
            ),
            "committed_at": utc_now(),
            "approval_certificate_path": str(
                approval_certificate_path
            ),
            "approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "final_gate_pack_path": str(
                final_gate_path
            ),
            "final_gate_pack_digest_sha256": (
                final_gate_digest
            ),
            "consumption_lock_path": str(
                lock_path
            ),
            "approval_consumed": True,
            "database_import_committed": True,
            "production_database_path": str(
                production_database_path
            ),
            "production_database_sha256_before": (
                database_sha_before
            ),
            "production_database_sha256_after": (
                database_sha_after
            ),
            "backup_path": str(
                backup_path
            ),
            "backup_sha256": (
                backup_sha256
            ),
            "inserted_ebook_count": 1,
            "inserted_store_offer_count": 1,
            "inserted_ebook_id": (
                ebook_values["id"]
            ),
            "inserted_offer_ids": [
                offer["values"]["id"]
                for offer in planned_offers
            ],
            "ebook_items_count_before": (
                ebook_count_before
            ),
            "ebook_items_count_after": (
                ebook_count_after
            ),
            "store_offers_count_before": (
                offer_count_before
            ),
            "store_offers_count_after": (
                offer_count_after
            ),
            "foreign_key_check_passed": True,
            "workflow_write": False,
            "approval_request_write": False,
            "wordpress_write": False,
            "normal_x_fb_write": False,
            "x_api_call": False,
            "x_post": False,
            "next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "POST-IMPORT-VERIFICATION"
            ),
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_SHOT_IMPORT_COMMITTED_"
                "NEXT_WRITES_BLOCKED"
            ),
        }

        receipt = {
            **receipt_payload,
            "execution_receipt_digest_sha256": (
                canonical_digest(
                    receipt_payload
                )
            ),
        }

        atomic_write_json(
            receipt_path,
            receipt,
        )

        result = {
            "phase": PHASE,
            "status": (
                "PASS_ONE_SHOT_IMPORT_COMMITTED"
            ),
            "approval_consumed": True,
            "database_import_committed": True,
            "inserted_ebook_count": 1,
            "inserted_store_offer_count": 1,
            "inserted_ebook_id": (
                ebook_values["id"]
            ),
            "inserted_offer_ids": (
                receipt[
                    "inserted_offer_ids"
                ]
            ),
            "production_database_sha256_before": (
                database_sha_before
            ),
            "production_database_sha256_after": (
                database_sha_after
            ),
            "backup_path": str(
                backup_path
            ),
            "backup_sha256": (
                backup_sha256
            ),
            "execution_receipt_path": str(
                receipt_path
            ),
            "execution_receipt_digest_sha256": (
                receipt[
                    "execution_receipt_digest_sha256"
                ]
            ),
            "consumption_lock_path": str(
                lock_path
            ),
            "workflow_write": False,
            "wordpress_write": False,
            "normal_x_fb_write": False,
            "x_api_call": False,
            "x_post": False,
            "execution_allowed": False,
            "database_import_allowed": False,
            "production_execution": False,
            "authorized_next_phase": (
                "X-R11-PRODUCTION-CANDIDATE-1-"
                "POST-IMPORT-VERIFICATION"
            ),
            "production_status": "NO_GO",
            "safety_state": (
                "ONE_SHOT_IMPORT_COMMITTED_"
                "NEXT_WRITES_BLOCKED"
            ),
        }

        atomic_write_json(
            result_path,
            result,
        )

        consumed_lock = {
            **claim,
            "status": "CONSUMED_COMMITTED",
            "approval_consumed": True,
            "database_commit_completed": True,
            "committed_at": (
                receipt["committed_at"]
            ),
            "production_database_sha256_after": (
                database_sha_after
            ),
            "execution_receipt_path": str(
                receipt_path
            ),
            "execution_receipt_digest_sha256": (
                receipt[
                    "execution_receipt_digest_sha256"
                ]
            ),
            "production_status": "NO_GO",
        }

        atomic_write_json(
            lock_path,
            consumed_lock,
        )

        return result

    except Exception as exc:
        if connection is not None:
            try:
                if not committed:
                    connection.execute(
                        "ROLLBACK"
                    )
            except sqlite3.Error:
                pass

        failure_state = (
            "COMMITTED_RECEIPT_FAILURE_"
            "REQUIRES_MANUAL_REVIEW"
            if committed
            else
            "FAILED_ROLLED_BACK"
        )

        failure = {
            **claim,
            "status": failure_state,
            "failed_at": utc_now(),
            "error": str(exc),
            "approval_consumed": True,
            "database_commit_completed": (
                committed
            ),
            "reexecution_allowed": False,
            "production_status": "NO_GO",
        }

        atomic_write_json(
            lock_path,
            failure,
        )

        atomic_write_json(
            result_path,
            {
                "phase": PHASE,
                "status": failure_state,
                "error": str(exc),
                "approval_consumed": True,
                "database_commit_completed": (
                    committed
                ),
                "reexecution_allowed": False,
                "database_import_allowed": False,
                "workflow_write": False,
                "wordpress_write": False,
                "normal_x_fb_write": False,
                "x_api_call": False,
                "x_post": False,
                "production_status": "NO_GO",
                "consumption_lock_path": str(
                    lock_path
                ),
            },
        )

        raise XR11OneShotImportRunnerError(
            str(exc)
        ) from exc

    finally:
        if connection is not None:
            connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--approval-certificate",
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
    parser.add_argument(
        "--lock-root",
        type=Path,
        default=DEFAULT_LOCK_ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_one_shot_import(
            approval_certificate_path=(
                args.approval_certificate
            ),
            production_database_path=(
                args.production_db
            ),
            expected_production_database_path=(
                args.expected_production_db
            ),
            output_root=args.output_root,
            lock_root=args.lock_root,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_ONE_SHOT_IMPORT",
                    "error": str(exc),
                    "execution_allowed": False,
                    "database_import_allowed": False,
                    "workflow_write": False,
                    "wordpress_write": False,
                    "normal_x_fb_write": False,
                    "x_api_call": False,
                    "x_post": False,
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
