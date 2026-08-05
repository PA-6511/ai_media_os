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
    "WAL-COMPATIBLE-ONE-SHOT-IMPORT-RUNNER"
)

EXPECTED_CERTIFICATE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WAL-RECOVERY-EXPLICIT-APPROVAL"
)

EXPECTED_CERTIFICATE_STATUS = (
    "WAL_RECOVERY_APPROVAL_ISSUED_NOT_CONSUMED"
)

EXPECTED_GATE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WAL-COMPATIBLE-IMPORT-RECOVERY-FINAL-GATE"
)

EXPECTED_GATE_STATUS = (
    "WAL_RECOVERY_FINAL_GATE_READY"
)

EXPECTED_GATE_STATE = (
    "WAL_RECOVERY_READY_NOT_EXECUTABLE"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_WAL_RECOVERY_"
    "ONE_SHOT_IMPORT_ONLY"
)

EXPECTED_APPROVAL_SCOPE = (
    "WAL_RECOVERY_ONE_SHOT_IMPORT_ONLY"
)

DEFAULT_LOCK_ROOT = (
    REPOSITORY_ROOT
    / "exchange/locks/x_r11_wal_recovery_import"
).resolve()


class XR11WalRecoveryImportError(
    RuntimeError
):
    """Raised when the WAL recovery import is unsafe."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11WalRecoveryImportError(
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


def wal_size(database_path: Path) -> int:
    wal_path = Path(
        str(database_path) + "-wal"
    )

    if not wal_path.exists():
        return 0

    return wal_path.stat().st_size


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
        raise XR11WalRecoveryImportError(
            f"invalid JSON: {path}: {exc}"
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
        raise XR11WalRecoveryImportError(
            (
                "WAL recovery approval has already "
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


def open_read_only(
    database_path: Path,
) -> sqlite3.Connection:
    connection = sqlite3.connect(
        (
            "file:"
            + quote(str(database_path))
            + "?mode=ro"
        ),
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    connection.execute(
        "PRAGMA query_only = ON"
    )

    return connection


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

    source = open_read_only(
        source_path
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
            "pre-import backup integrity failed",
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
            "planned row has no ID: "
            f"{table_name}"
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


def verify_source_contracts(
    *,
    certificate: dict[str, Any],
    certificate_path: Path,
    gate: dict[str, Any],
    gate_path: Path,
    production_database_path: Path,
) -> tuple[str, str]:
    certificate_digest = verify_digest(
        certificate,
        digest_field=(
            "wal_recovery_approval_"
            "certificate_digest_sha256"
        ),
        label="WAL recovery certificate",
    )

    gate_digest = verify_digest(
        gate,
        digest_field=(
            "recovery_final_gate_digest_sha256"
        ),
        label="WAL recovery Final Gate",
    )

    require(
        certificate.get("phase")
        == EXPECTED_CERTIFICATE_PHASE,
        "certificate phase is invalid",
    )
    require(
        certificate.get("status")
        == EXPECTED_CERTIFICATE_STATUS,
        "certificate status is invalid",
    )
    require(
        certificate.get("approval_state")
        == "ISSUED_NOT_CONSUMED",
        "certificate state is invalid",
    )
    require(
        certificate.get("approval_issued")
        is True,
        "recovery approval was not issued",
    )
    require(
        certificate.get("approval_consumed")
        is False,
        "recovery approval is already consumed",
    )
    require(
        certificate.get("approval_label")
        == EXPECTED_APPROVAL_LABEL,
        "recovery approval label is invalid",
    )
    require(
        certificate.get("approval_scope")
        == EXPECTED_APPROVAL_SCOPE,
        "recovery approval scope is invalid",
    )
    require(
        certificate.get(
            "authorizes_wal_recovery_import"
        )
        is True,
        (
            "certificate does not authorize "
            "WAL recovery import"
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
        "Workflow write authorization is invalid",
    )
    require(
        certificate.get(
            "authorizes_wordpress_write"
        )
        is False,
        "WordPress write authorization is invalid",
    )
    require(
        certificate.get(
            "authorizes_normal_x_fb_write"
        )
        is False,
        "normal X-FB authorization is invalid",
    )
    require(
        certificate.get(
            "old_certificate_replay_allowed"
        )
        is False,
        "old certificate replay must be blocked",
    )
    require(
        certificate.get("execution_allowed")
        is False,
        (
            "pre-consumption certificate "
            "must not directly allow execution"
        ),
    )
    require(
        certificate.get(
            "database_import_allowed"
        )
        is False,
        (
            "pre-consumption certificate "
            "must not directly allow import"
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
        gate.get("phase")
        == EXPECTED_GATE_PHASE,
        "recovery Final Gate phase is invalid",
    )
    require(
        gate.get("status")
        == EXPECTED_GATE_STATUS,
        "recovery Final Gate status is invalid",
    )
    require(
        gate.get("gate_state")
        == EXPECTED_GATE_STATE,
        "recovery Final Gate state is invalid",
    )
    require(
        gate.get("duplicate_match_count")
        == 0,
        "recovery Final Gate contains duplicates",
    )
    require(
        gate.get("approval_issued")
        is False,
        (
            "source recovery Final Gate "
            "must remain unissued"
        ),
    )
    require(
        gate.get("execution_allowed")
        is False,
        "source gate must not be executable",
    )
    require(
        gate.get("database_import_allowed")
        is False,
        "source gate must not allow import",
    )
    require(
        gate.get("database_write")
        is False,
        "source gate must not allow DB writes",
    )

    require(
        Path(
            certificate[
                "recovery_final_gate_path"
            ]
        ).resolve()
        == gate_path,
        "certificate recovery gate path mismatch",
    )
    require(
        certificate.get(
            "recovery_final_gate_file_sha256"
        )
        == sha256_file(gate_path),
        "recovery gate file SHA mismatch",
    )
    require(
        certificate.get(
            "recovery_final_gate_digest_sha256"
        )
        == gate_digest,
        "recovery gate digest mismatch",
    )
    require(
        certificate.get("recovery_request_id")
        == gate.get("recovery_request_id"),
        "recovery request ID mismatch",
    )
    require(
        certificate.get(
            "candidate_digest_sha256"
        )
        == gate.get(
            "candidate_digest_sha256"
        ),
        "candidate digest mismatch",
    )
    require(
        certificate.get("planned_ebook_id")
        == gate.get("planned_ebook_id"),
        "planned ebook ID mismatch",
    )
    require(
        certificate.get("planned_offer_ids")
        == gate.get("planned_offer_ids"),
        "planned offer IDs mismatch",
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
            gate["planned_store_offers"]
        )
        == 1,
        (
            "exactly one store offer "
            "must be planned"
        ),
    )

    require(
        certificate.get(
            "required_pre_execution_database_sha256"
        )
        == gate.get(
            "required_pre_execution_database_sha256"
        ),
        "required database SHA mismatch",
    )
    require(
        certificate.get(
            "required_pre_execution_wal_size"
        )
        == 0,
        "required WAL size must be zero",
    )
    require(
        certificate.get(
            "required_journal_mode"
        )
        == "wal",
        "required journal mode must be WAL",
    )
    require(
        certificate.get("wal_mode_allowed")
        is True,
        "certificate must explicitly allow WAL",
    )
    require(
        certificate.get(
            "manual_wal_deletion_allowed"
        )
        is False,
        "manual WAL deletion must remain blocked",
    )
    require(
        certificate.get(
            "manual_journal_mode_change_allowed"
        )
        is False,
        (
            "manual journal-mode changes "
            "must remain blocked"
        ),
    )

    snapshot_path = Path(
        certificate[
            "recovery_snapshot_path"
        ]
    ).resolve()

    require(
        snapshot_path.is_file(),
        "recovery snapshot is missing",
    )
    require(
        sha256_file(snapshot_path)
        == certificate.get(
            "recovery_snapshot_sha256"
        ),
        "recovery snapshot SHA mismatch",
    )
    require(
        certificate.get(
            "recovery_snapshot_sha256"
        )
        == gate.get(
            "recovery_snapshot_sha256"
        ),
        (
            "recovery snapshot mismatch "
            "between certificate and gate"
        ),
    )

    required_database_sha = certificate[
        "required_pre_execution_database_sha256"
    ]

    require(
        sha256_file(
            production_database_path
        )
        == required_database_sha,
        (
            "production database changed "
            "after recovery approval issuance"
        ),
    )
    require(
        wal_size(production_database_path)
        == 0,
        (
            "WAL file is non-empty before "
            "approval consumption"
        ),
    )

    failed_lock_path = Path(
        gate["source_failed_lock_path"]
    ).resolve()

    failed_lock = load_json_object(
        failed_lock_path
    )

    require(
        canonical_digest(failed_lock)
        == gate.get(
            "source_failed_lock_digest_sha256"
        ),
        "old failed lock digest mismatch",
    )
    require(
        failed_lock.get("status")
        == "FAILED_ROLLED_BACK",
        "old failed lock status is invalid",
    )
    require(
        failed_lock.get("approval_consumed")
        is True,
        "old approval consumption is missing",
    )
    require(
        failed_lock.get("reexecution_allowed")
        is False,
        "old certificate replay is not blocked",
    )

    return certificate_digest, gate_digest


def run_wal_recovery_import(
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
        "production database is missing",
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
                "wal_recovery_approval_"
                "certificate_digest_sha256"
            ),
            label="WAL recovery certificate",
        )
    )

    lock_path = (
        lock_root
        / f"{certificate_digest_precheck}.json"
    )

    require(
        not lock_path.exists(),
        (
            "WAL recovery approval has already "
            "been claimed or consumed: "
            f"{lock_path}"
        ),
    )

    gate_path = Path(
        certificate.get(
            "recovery_final_gate_path",
            "",
        )
    ).resolve()

    gate = load_json_object(
        gate_path
    )

    (
        certificate_digest,
        gate_digest,
    ) = verify_source_contracts(
        certificate=certificate,
        certificate_path=(
            approval_certificate_path
        ),
        gate=gate,
        gate_path=gate_path,
        production_database_path=(
            production_database_path
        ),
    )

    precheck_connection = open_read_only(
        production_database_path
    )

    try:
        journal_mode = str(
            precheck_connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        ).lower()

        integrity = str(
            precheck_connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        )

        require(
            journal_mode == "wal",
            "production database is not in WAL mode",
        )
        require(
            integrity == "ok",
            "production database integrity failed",
        )

        current_schema = {
            "ebook_items": read_table_schema(
                precheck_connection,
                "ebook_items",
            ),
            "store_offers": read_table_schema(
                precheck_connection,
                "store_offers",
            ),
        }

        require(
            canonical_digest(current_schema)
            == canonical_digest(
                gate["schema_snapshot"]
            ),
            (
                "production schema changed "
                "after recovery Final Gate"
            ),
        )

        preclaim_duplicates = (
            recheck_duplicates(
                precheck_connection,
                pack=gate,
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
                "recovery approval consumption"
            ),
        )
    finally:
        precheck_connection.close()

    require(
        wal_size(production_database_path)
        == 0,
        (
            "WAL file became non-empty before "
            "approval consumption"
        ),
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    claim = {
        "phase": PHASE,
        "status": "CLAIMED_NOT_EXECUTED",
        "claimed_at": utc_now(),
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "wal_recovery_approval_certificate_digest_sha256": (
            certificate_digest
        ),
        "recovery_final_gate_path": str(
            gate_path
        ),
        "recovery_final_gate_digest_sha256": (
            gate_digest
        ),
        "production_database_path": str(
            production_database_path
        ),
        "required_pre_execution_database_sha256": (
            certificate[
                "required_pre_execution_database_sha256"
            ]
        ),
        "required_pre_execution_wal_size": 0,
        "planned_ebook_id": (
            certificate["planned_ebook_id"]
        ),
        "planned_offer_ids": (
            certificate["planned_offer_ids"]
        ),
        "transaction_started": False,
        "database_write_started": False,
        "database_commit_completed": False,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "production_status": "NO_GO",
    }

    create_exclusive_json(
        lock_path,
        claim,
    )

    backup_path = (
        output_root
        / "ebook_affiliate.wal_pre_import.backup.db"
    )
    result_path = (
        output_root
        / "x_r11_wal_recovery_import_result.json"
    )
    receipt_path = (
        output_root
        / "x_r11_wal_recovery_import_receipt.json"
    )

    database_sha_before = sha256_file(
        production_database_path
    )
    wal_size_before = wal_size(
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
                "production database changed "
                "before recovery backup"
            ),
        )
        require(
            wal_size_before == 0,
            (
                "WAL file is non-empty "
                "before recovery backup"
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
                "while creating recovery backup"
            ),
        )
        require(
            wal_size(
                production_database_path
            )
            == 0,
            (
                "WAL file changed while "
                "creating recovery backup"
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
        connection.execute(
            "PRAGMA busy_timeout = 30000"
        )

        current_journal_mode = str(
            connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        ).lower()

        require(
            current_journal_mode == "wal",
            (
                "journal mode changed before "
                "WAL recovery transaction"
            ),
        )

        connection.execute(
            "BEGIN IMMEDIATE"
        )

        claim["transaction_started"] = True
        claim["transaction_started_at"] = (
            utc_now()
        )

        atomic_write_json(
            lock_path,
            claim,
        )

        require(
            sha256_file(
                production_database_path
            )
            == database_sha_before,
            (
                "production database changed "
                "before recovery INSERT"
            ),
        )
        require(
            wal_size(
                production_database_path
            )
            == 0,
            (
                "WAL file became non-empty "
                "before recovery INSERT"
            ),
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
                gate["schema_snapshot"]
            ),
            (
                "production schema changed "
                "before recovery INSERT"
            ),
        )

        transaction_duplicates = (
            recheck_duplicates(
                connection,
                pack=gate,
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
                "WAL recovery transaction"
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

        ebook_values = gate[
            "planned_ebook_item_values"
        ]
        planned_offers = gate[
            "planned_store_offers"
        ]

        require(
            len(planned_offers) == 1,
            (
                "exactly one store offer "
                "must be planned"
            ),
        )

        claim["database_write_started"] = True
        claim["database_write_started_at"] = (
            utc_now()
        )

        atomic_write_json(
            lock_path,
            claim,
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

        post_connection = open_read_only(
            production_database_path
        )

        try:
            post_integrity = str(
                post_connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
            )

            require(
                post_integrity == "ok",
                (
                    "post-import database "
                    "integrity check failed"
                ),
            )

            verify_exact_row(
                post_connection,
                table_name="ebook_items",
                values=ebook_values,
            )

            for offer in planned_offers:
                verify_exact_row(
                    post_connection,
                    table_name="store_offers",
                    values=offer["values"],
                )

            post_ebook_count = table_count(
                post_connection,
                "ebook_items",
            )
            post_offer_count = table_count(
                post_connection,
                "store_offers",
            )

            post_fk_errors = [
                dict(row)
                for row
                in post_connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall()
            ]

            require(
                post_fk_errors == [],
                (
                    "post-import foreign-key "
                    "verification failed"
                ),
            )
            require(
                post_ebook_count
                == ebook_count_before + 1,
                (
                    "post-import ebook count "
                    "is invalid"
                ),
            )
            require(
                post_offer_count
                == offer_count_before + 1,
                (
                    "post-import offer count "
                    "is invalid"
                ),
            )
        finally:
            post_connection.close()

        database_sha_after = sha256_file(
            production_database_path
        )
        wal_size_after = wal_size(
            production_database_path
        )

        receipt_payload = {
            "phase": PHASE,
            "status": (
                "WAL_RECOVERY_IMPORT_COMMITTED"
            ),
            "committed_at": utc_now(),
            "approval_certificate_path": str(
                approval_certificate_path
            ),
            "wal_recovery_approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "recovery_final_gate_path": str(
                gate_path
            ),
            "recovery_final_gate_digest_sha256": (
                gate_digest
            ),
            "consumption_lock_path": str(
                lock_path
            ),
            "approval_consumed": True,
            "database_import_committed": True,
            "journal_mode": "wal",
            "production_database_path": str(
                production_database_path
            ),
            "production_database_sha256_before": (
                database_sha_before
            ),
            "production_database_sha256_after": (
                database_sha_after
            ),
            "wal_size_before": (
                wal_size_before
            ),
            "wal_size_after": (
                wal_size_after
            ),
            "main_file_sha_change_required": False,
            "logical_row_verification_passed": True,
            "database_integrity_check_passed": True,
            "foreign_key_check_passed": True,
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
                post_ebook_count
            ),
            "store_offers_count_before": (
                offer_count_before
            ),
            "store_offers_count_after": (
                post_offer_count
            ),
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
                "WAL_RECOVERY_IMPORT_COMMITTED_"
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
                "PASS_WAL_RECOVERY_"
                "ONE_SHOT_IMPORT_COMMITTED"
            ),
            "approval_consumed": True,
            "database_import_committed": True,
            "journal_mode": "wal",
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
            "wal_size_before": (
                wal_size_before
            ),
            "wal_size_after": (
                wal_size_after
            ),
            "logical_row_verification_passed": (
                True
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
                "WAL_RECOVERY_IMPORT_COMMITTED_"
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
            "wal_size_after": (
                wal_size_after
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

        failure_status = (
            "COMMITTED_RECEIPT_FAILURE_"
            "REQUIRES_MANUAL_REVIEW"
            if committed
            else
            "FAILED_ROLLED_BACK"
        )

        failure_lock = {
            **claim,
            "status": failure_status,
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
            failure_lock,
        )

        atomic_write_json(
            result_path,
            {
                "phase": PHASE,
                "status": failure_status,
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

        raise XR11WalRecoveryImportError(
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
        result = run_wal_recovery_import(
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
                    "status": (
                        "FAIL_WAL_RECOVERY_IMPORT"
                    ),
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
