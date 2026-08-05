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
from scripts.build_x_r11_one_shot_import_final_gate import (
    recheck_duplicates,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WAL-COMPATIBLE-IMPORT-RECOVERY-FINAL-GATE"
)

EXPECTED_RUNNER_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-RUNNER"
)

EXPECTED_FAILED_STATUS = (
    "FAILED_ROLLED_BACK"
)

EXPECTED_CERTIFICATE_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "ONE-SHOT-IMPORT-EXPLICIT-APPROVAL"
)

EXPECTED_CERTIFICATE_STATUS = (
    "APPROVAL_ISSUED_NOT_CONSUMED"
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

REQUIRED_RECOVERY_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_MANUAL_INTAKE_"
    "CANDIDATE_1_WAL_RECOVERY_ONE_SHOT_IMPORT_ONLY"
)

AUTHORIZED_NEXT_PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WAL-RECOVERY-EXPLICIT-APPROVAL"
)


class XR11WalRecoveryFinalGateError(
    RuntimeError
):
    """Raised when WAL recovery preparation is unsafe."""


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise XR11WalRecoveryFinalGateError(
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
        raise XR11WalRecoveryFinalGateError(
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


def inspect_database(
    database_path: Path,
    *,
    planned_ebook_id: str,
    planned_offer_ids: list[str],
) -> dict[str, Any]:
    connection = open_read_only(
        database_path
    )

    try:
        journal_mode = str(
            connection.execute(
                "PRAGMA journal_mode"
            ).fetchone()[0]
        ).lower()

        integrity_check = str(
            connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        )

        ebook_schema = read_table_schema(
            connection,
            "ebook_items",
        )
        offer_schema = read_table_schema(
            connection,
            "store_offers",
        )

        ebook_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM ebook_items
                WHERE id = ?
                """,
                (planned_ebook_id,),
            ).fetchall()
        ]

        offer_rows: list[dict[str, Any]] = []

        for offer_id in planned_offer_ids:
            offer_rows.extend(
                dict(row)
                for row in connection.execute(
                    """
                    SELECT *
                    FROM store_offers
                    WHERE id = ?
                    """,
                    (offer_id,),
                ).fetchall()
            )

        return {
            "journal_mode": journal_mode,
            "integrity_check": integrity_check,
            "ebook_items_count": int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM ebook_items
                    """
                ).fetchone()[0]
            ),
            "store_offers_count": int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM store_offers
                    """
                ).fetchone()[0]
            ),
            "planned_ebook_row_count": (
                len(ebook_rows)
            ),
            "planned_offer_row_count": (
                len(offer_rows)
            ),
            "planned_ebook_rows": ebook_rows,
            "planned_offer_rows": offer_rows,
            "schema_snapshot": {
                "ebook_items": ebook_schema,
                "store_offers": offer_schema,
            },
        }
    finally:
        connection.close()


def create_snapshot_backup(
    source_path: Path,
    snapshot_path: Path,
) -> None:
    require(
        not snapshot_path.exists(),
        (
            "snapshot path already exists: "
            f"{snapshot_path}"
        ),
    )

    source = open_read_only(
        source_path
    )
    destination = sqlite3.connect(
        snapshot_path
    )

    try:
        source.backup(destination)

        integrity = destination.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        require(
            integrity is not None
            and integrity[0] == "ok",
            "recovery snapshot integrity failed",
        )
    finally:
        destination.close()
        source.close()


def run_recovery_final_gate(
    *,
    failed_result_path: Path,
    failed_lock_path: Path,
    failed_backup_path: Path,
    consumed_certificate_path: Path,
    production_database_path: Path,
    expected_production_database_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    failed_result_path = (
        failed_result_path.resolve()
    )
    failed_lock_path = (
        failed_lock_path.resolve()
    )
    failed_backup_path = (
        failed_backup_path.resolve()
    )
    consumed_certificate_path = (
        consumed_certificate_path.resolve()
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
        "production database is missing",
    )
    require(
        failed_backup_path.is_file(),
        "failed-run backup is missing",
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    failed_result = load_json_object(
        failed_result_path
    )
    failed_lock = load_json_object(
        failed_lock_path
    )
    certificate = load_json_object(
        consumed_certificate_path
    )

    certificate_digest = verify_digest(
        certificate,
        digest_field=(
            "approval_certificate_digest_sha256"
        ),
        label="consumed approval certificate",
    )

    require(
        failed_result.get("phase")
        == EXPECTED_RUNNER_PHASE,
        "failed result phase is invalid",
    )
    require(
        failed_result.get("status")
        == EXPECTED_FAILED_STATUS,
        "failed result status is invalid",
    )
    require(
        failed_result.get(
            "database_commit_completed"
        )
        is False,
        (
            "failed result unexpectedly "
            "reports a committed database write"
        ),
    )
    require(
        failed_result.get(
            "approval_consumed"
        )
        is True,
        (
            "failed result must record "
            "consumed approval"
        ),
    )
    require(
        failed_result.get(
            "reexecution_allowed"
        )
        is False,
        (
            "failed result must prohibit "
            "certificate replay"
        ),
    )

    require(
        failed_lock.get("phase")
        == EXPECTED_RUNNER_PHASE,
        "failed lock phase is invalid",
    )
    require(
        failed_lock.get("status")
        == EXPECTED_FAILED_STATUS,
        "failed lock status is invalid",
    )
    require(
        failed_lock.get(
            "database_write_started"
        )
        is False,
        (
            "recovery gate only supports "
            "failure before database write start"
        ),
    )
    require(
        failed_lock.get(
            "database_commit_completed"
        )
        is False,
        (
            "failed lock unexpectedly reports "
            "a committed database write"
        ),
    )
    require(
        failed_lock.get(
            "approval_consumed"
        )
        is True,
        (
            "failed lock must record "
            "consumed approval"
        ),
    )
    require(
        failed_lock.get(
            "reexecution_allowed"
        )
        is False,
        (
            "failed lock must prohibit replay"
        ),
    )
    require(
        failed_lock.get(
            "approval_certificate_digest_sha256"
        )
        == certificate_digest,
        (
            "failed lock certificate digest "
            "does not match"
        ),
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
        certificate.get("approval_issued")
        is True,
        "certificate was not issued",
    )
    require(
        certificate.get("approval_consumed")
        is False,
        (
            "certificate artifact must remain "
            "immutable; consumption is held "
            "in the failed lock"
        ),
    )

    original_final_gate_path = Path(
        certificate[
            "final_gate_pack_path"
        ]
    ).resolve()

    original_final_gate = load_json_object(
        original_final_gate_path
    )

    original_final_gate_digest = (
        verify_digest(
            original_final_gate,
            digest_field=(
                "final_gate_pack_digest_sha256"
            ),
            label="original Final Gate",
        )
    )

    require(
        original_final_gate.get("phase")
        == EXPECTED_FINAL_GATE_PHASE,
        "original Final Gate phase is invalid",
    )
    require(
        original_final_gate.get("status")
        == EXPECTED_FINAL_GATE_STATUS,
        "original Final Gate status is invalid",
    )
    require(
        original_final_gate.get("gate_state")
        == EXPECTED_FINAL_GATE_STATE,
        "original Final Gate state is invalid",
    )
    require(
        original_final_gate.get(
            "duplicate_match_count"
        )
        == 0,
        "original Final Gate contains duplicates",
    )
    require(
        certificate.get(
            "final_gate_pack_digest_sha256"
        )
        == original_final_gate_digest,
        (
            "certificate Final Gate digest "
            "does not match"
        ),
    )

    planned_ebook_id = str(
        certificate["planned_ebook_id"]
    )
    planned_offer_ids = [
        str(value)
        for value in certificate[
            "planned_offer_ids"
        ]
    ]

    require(
        len(planned_offer_ids) == 1,
        (
            "recovery gate permits exactly "
            "one planned store offer"
        ),
    )

    required_database_sha = str(
        certificate[
            "required_pre_execution_database_sha256"
        ]
    )

    database_sha_before = sha256_file(
        production_database_path
    )

    require(
        database_sha_before
        == required_database_sha,
        (
            "production database changed "
            "after the consumed approval"
        ),
    )

    wal_path = Path(
        str(production_database_path)
        + "-wal"
    )
    shm_path = Path(
        str(production_database_path)
        + "-shm"
    )

    wal_size_before = (
        wal_path.stat().st_size
        if wal_path.exists()
        else 0
    )

    require(
        wal_size_before == 0,
        (
            "WAL recovery gate requires "
            "an absent or empty WAL file"
        ),
    )

    database_inspection = inspect_database(
        production_database_path,
        planned_ebook_id=planned_ebook_id,
        planned_offer_ids=planned_offer_ids,
    )

    require(
        database_inspection["journal_mode"]
        == "wal",
        (
            "WAL recovery gate requires "
            "journal_mode=wal"
        ),
    )
    require(
        database_inspection["integrity_check"]
        == "ok",
        "production database integrity failed",
    )
    require(
        database_inspection[
            "planned_ebook_row_count"
        ]
        == 0,
        (
            "planned ebook row already exists"
        ),
    )
    require(
        database_inspection[
            "planned_offer_row_count"
        ]
        == 0,
        (
            "planned store-offer row already exists"
        ),
    )

    require(
        canonical_digest(
            database_inspection[
                "schema_snapshot"
            ]
        )
        == canonical_digest(
            original_final_gate[
                "schema_snapshot"
            ]
        ),
        (
            "production schema changed "
            "after original Final Gate"
        ),
    )

    connection = open_read_only(
        production_database_path
    )

    try:
        duplicate_matches = (
            recheck_duplicates(
                connection,
                pack=original_final_gate,
                ebook_schema=(
                    database_inspection[
                        "schema_snapshot"
                    ]["ebook_items"]
                ),
                offer_schema=(
                    database_inspection[
                        "schema_snapshot"
                    ]["store_offers"]
                ),
            )
        )
    finally:
        connection.close()

    require(
        duplicate_matches == [],
        (
            "duplicate detected during "
            "WAL recovery preparation"
        ),
    )

    backup_inspection = inspect_database(
        failed_backup_path,
        planned_ebook_id=planned_ebook_id,
        planned_offer_ids=planned_offer_ids,
    )

    require(
        backup_inspection["integrity_check"]
        == "ok",
        "failed-run backup integrity failed",
    )
    require(
        backup_inspection[
            "planned_ebook_row_count"
        ]
        == 0,
        "failed-run backup contains planned ebook",
    )
    require(
        backup_inspection[
            "planned_offer_row_count"
        ]
        == 0,
        (
            "failed-run backup contains "
            "planned store offer"
        ),
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    snapshot_path = (
        output_root
        / "ebook_affiliate.wal_recovery_snapshot.db"
    )

    create_snapshot_backup(
        production_database_path,
        snapshot_path,
    )

    snapshot_sha256 = sha256_file(
        snapshot_path
    )

    snapshot_inspection = inspect_database(
        snapshot_path,
        planned_ebook_id=planned_ebook_id,
        planned_offer_ids=planned_offer_ids,
    )

    require(
        snapshot_inspection[
            "integrity_check"
        ]
        == "ok",
        "recovery snapshot integrity failed",
    )
    require(
        snapshot_inspection[
            "planned_ebook_row_count"
        ]
        == 0,
        "recovery snapshot contains planned ebook",
    )
    require(
        snapshot_inspection[
            "planned_offer_row_count"
        ]
        == 0,
        (
            "recovery snapshot contains "
            "planned store offer"
        ),
    )

    database_sha_after = sha256_file(
        production_database_path
    )

    wal_size_after = (
        wal_path.stat().st_size
        if wal_path.exists()
        else 0
    )

    require(
        database_sha_after
        == database_sha_before,
        (
            "production database changed "
            "during WAL recovery preparation"
        ),
    )
    require(
        wal_size_after == 0,
        (
            "WAL file changed during "
            "recovery preparation"
        ),
    )

    failed_lock_digest = canonical_digest(
        failed_lock
    )

    recovery_identity_payload = {
        "failed_lock_digest_sha256": (
            failed_lock_digest
        ),
        "consumed_certificate_digest_sha256": (
            certificate_digest
        ),
        "original_final_gate_digest_sha256": (
            original_final_gate_digest
        ),
        "recovery_snapshot_sha256": (
            snapshot_sha256
        ),
        "production_database_sha256": (
            database_sha_after
        ),
    }

    recovery_identity_digest = (
        canonical_digest(
            recovery_identity_payload
        )
    )

    recovery_request_id = (
        "xr11-wal-recovery-"
        + recovery_identity_digest[:24]
    )

    recovery_pack_payload = {
        "phase": PHASE,
        "status": (
            "WAL_RECOVERY_FINAL_GATE_READY"
        ),
        "gate_state": (
            "WAL_RECOVERY_READY_NOT_EXECUTABLE"
        ),
        "recovery_request_id": (
            recovery_request_id
        ),
        "source_failed_result_path": str(
            failed_result_path
        ),
        "source_failed_result_sha256": (
            sha256_file(
                failed_result_path
            )
        ),
        "source_failed_lock_path": str(
            failed_lock_path
        ),
        "source_failed_lock_digest_sha256": (
            failed_lock_digest
        ),
        "source_failed_backup_path": str(
            failed_backup_path
        ),
        "source_failed_backup_sha256": (
            sha256_file(
                failed_backup_path
            )
        ),
        "consumed_certificate_path": str(
            consumed_certificate_path
        ),
        "consumed_certificate_digest_sha256": (
            certificate_digest
        ),
        "consumed_certificate_replay_allowed": (
            False
        ),
        "original_final_gate_path": str(
            original_final_gate_path
        ),
        "original_final_gate_digest_sha256": (
            original_final_gate_digest
        ),
        "candidate": (
            original_final_gate["candidate"]
        ),
        "candidate_digest_sha256": (
            original_final_gate[
                "candidate_digest_sha256"
            ]
        ),
        "planned_ebook_id": (
            planned_ebook_id
        ),
        "planned_offer_ids": (
            planned_offer_ids
        ),
        "planned_ebook_item_values": (
            original_final_gate[
                "planned_ebook_item_values"
            ]
        ),
        "planned_store_offers": (
            original_final_gate[
                "planned_store_offers"
            ]
        ),
        "schema_snapshot": (
            original_final_gate[
                "schema_snapshot"
            ]
        ),
        "schema_snapshot_digest_sha256": (
            canonical_digest(
                original_final_gate[
                    "schema_snapshot"
                ]
            )
        ),
        "duplicate_matches": [],
        "duplicate_match_count": 0,
        "production_database_path": str(
            production_database_path
        ),
        "required_pre_execution_database_sha256": (
            database_sha_after
        ),
        "required_journal_mode": "wal",
        "required_pre_execution_wal_size": 0,
        "wal_path": str(wal_path),
        "shm_path": str(shm_path),
        "shm_exists": shm_path.exists(),
        "shm_size": (
            shm_path.stat().st_size
            if shm_path.exists()
            else 0
        ),
        "recovery_snapshot_path": str(
            snapshot_path
        ),
        "recovery_snapshot_sha256": (
            snapshot_sha256
        ),
        "recovery_snapshot_integrity_check": (
            "ok"
        ),
        "ebook_items_count_before": (
            database_inspection[
                "ebook_items_count"
            ]
        ),
        "store_offers_count_before": (
            database_inspection[
                "store_offers_count"
            ]
        ),
        "required_approval_label": (
            REQUIRED_RECOVERY_APPROVAL_LABEL
        ),
        "approval_scope": (
            "WAL_RECOVERY_ONE_SHOT_IMPORT_ONLY"
        ),
        "approval_issued": False,
        "approval_consumed": False,
        "maximum_ebook_insert_count": 1,
        "maximum_store_offer_insert_count": 1,
        "transaction_required": True,
        "begin_immediate_required": True,
        "wal_mode_allowed": True,
        "manual_wal_deletion_allowed": False,
        "manual_journal_mode_change_allowed": (
            False
        ),
        "checkpoint_before_execution_allowed": (
            False
        ),
        "rollback_on_any_failure": True,
        "post_commit_read_only_verification_required": (
            True
        ),
        "post_commit_main_file_sha_change_required": (
            False
        ),
        "post_commit_logical_row_verification_required": (
            True
        ),
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
            AUTHORIZED_NEXT_PHASE
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "WAL_RECOVERY_FINAL_GATE_"
            "NO_EXECUTION"
        ),
    }

    recovery_pack_digest = (
        canonical_digest(
            recovery_pack_payload
        )
    )

    recovery_pack = {
        **recovery_pack_payload,
        "recovery_final_gate_digest_sha256": (
            recovery_pack_digest
        ),
    }

    pack_path = (
        output_root
        / "x_r11_wal_recovery_final_gate_pack.json"
    )
    result_path = (
        output_root
        / "x_r11_wal_recovery_final_gate_result.json"
    )

    atomic_write_json(
        pack_path,
        recovery_pack,
    )

    result = {
        "phase": PHASE,
        "status": (
            "PASS_WAL_RECOVERY_FINAL_GATE_"
            "READY_AWAITING_EXPLICIT_APPROVAL"
        ),
        "gate_state": (
            "WAL_RECOVERY_READY_NOT_EXECUTABLE"
        ),
        "recovery_request_id": (
            recovery_request_id
        ),
        "candidate_digest_sha256": (
            recovery_pack[
                "candidate_digest_sha256"
            ]
        ),
        "planned_ebook_id": (
            planned_ebook_id
        ),
        "planned_offer_ids": (
            planned_offer_ids
        ),
        "duplicate_match_count": 0,
        "journal_mode": "wal",
        "wal_size": 0,
        "production_database_sha256": (
            database_sha_after
        ),
        "production_database_unchanged": True,
        "recovery_snapshot_sha256": (
            snapshot_sha256
        ),
        "recovery_final_gate_digest_sha256": (
            recovery_pack_digest
        ),
        "required_approval_label": (
            REQUIRED_RECOVERY_APPROVAL_LABEL
        ),
        "approval_scope": (
            "WAL_RECOVERY_ONE_SHOT_IMPORT_ONLY"
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
            AUTHORIZED_NEXT_PHASE
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "WAL_RECOVERY_FINAL_GATE_"
            "NO_EXECUTION"
        ),
        "recovery_final_gate_pack_path": str(
            pack_path
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
        "--failed-result",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--failed-lock",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--failed-backup",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--consumed-certificate",
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
        result = run_recovery_final_gate(
            failed_result_path=(
                args.failed_result
            ),
            failed_lock_path=(
                args.failed_lock
            ),
            failed_backup_path=(
                args.failed_backup
            ),
            consumed_certificate_path=(
                args.consumed_certificate
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
                    "status": (
                        "FAIL_WAL_RECOVERY_FINAL_GATE"
                    ),
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
