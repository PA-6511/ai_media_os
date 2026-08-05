from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.build_x_r11_manual_intake_import_prep import (
    read_table_schema,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)
from scripts.run_x_r11_wal_recovery_one_shot_import import (
    EXPECTED_APPROVAL_LABEL,
    EXPECTED_APPROVAL_SCOPE,
    EXPECTED_CERTIFICATE_PHASE,
    EXPECTED_CERTIFICATE_STATUS,
    EXPECTED_GATE_PHASE,
    EXPECTED_GATE_STATE,
    EXPECTED_GATE_STATUS,
    XR11WalRecoveryImportError,
    run_wal_recovery_import,
)


EBOOK_ID = (
    "3e4158c3-1c19-5a07-"
    "a5ed-5234a9446db9"
)

OFFER_ID = (
    "983647ba-0203-5873-"
    "aea8-f7073401dcf9"
)

CANDIDATE_DIGEST = (
    "d233e7afa9a33dab0c9ee797"
    "f2ee6ebde6f29809075cf741"
    "9ec0bf98af3294fd"
)


def sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def create_database(path: Path) -> None:
    connection = sqlite3.connect(path)

    try:
        connection.executescript(
            """
            CREATE TABLE ebook_items (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_item_id TEXT NOT NULL,
                title TEXT NOT NULL,
                volume_label TEXT,
                release_date TEXT,
                publisher_name TEXT,
                author_name TEXT,
                item_type TEXT NOT NULL,
                is_excluded INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                wordpress_status TEXT
                    DEFAULT 'NOT_CREATED'
                    NOT NULL,
                UNIQUE (
                    source_name,
                    source_item_id
                )
            );

            CREATE TABLE store_offers (
                id TEXT PRIMARY KEY,
                ebook_item_id TEXT NOT NULL,
                store_name TEXT NOT NULL,
                store_item_id TEXT NOT NULL,
                product_url TEXT,
                affiliate_url TEXT,
                last_checked_at TEXT NOT NULL,
                FOREIGN KEY (
                    ebook_item_id
                )
                REFERENCES ebook_items(id)
                    ON DELETE CASCADE,
                UNIQUE (
                    ebook_item_id,
                    store_name,
                    store_item_id
                )
            );
            """
        )

        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.commit()
    finally:
        connection.close()


def schema_snapshot(database: Path) -> dict:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row

    try:
        return {
            "ebook_items": read_table_schema(
                connection,
                "ebook_items",
            ),
            "store_offers": read_table_schema(
                connection,
                "store_offers",
            ),
        }
    finally:
        connection.close()


def prepare(
    tmp_path: Path,
) -> tuple[Path, Path]:
    database = tmp_path / "production.db"
    gate_path = tmp_path / "recovery-gate.json"
    certificate_path = (
        tmp_path / "recovery-certificate.json"
    )
    snapshot_path = tmp_path / "snapshot.db"
    failed_lock_path = tmp_path / "old-lock.json"

    create_database(database)

    source = sqlite3.connect(database)
    destination = sqlite3.connect(
        snapshot_path
    )

    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    timestamp = (
        "2026-07-17 16:16:03.507558"
    )

    ebook = {
        "id": EBOOK_ID,
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
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    offer = {
        "id": OFFER_ID,
        "ebook_item_id": EBOOK_ID,
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
        "last_checked_at": timestamp,
    }

    failed_lock = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "ONE-SHOT-IMPORT-RUNNER"
        ),
        "status": "FAILED_ROLLED_BACK",
        "approval_consumed": True,
        "reexecution_allowed": False,
        "database_write_started": False,
        "database_commit_completed": False,
    }

    failed_lock_path.write_text(
        json.dumps(failed_lock),
        encoding="utf-8",
    )

    database_sha = sha256_file(database)

    gate_payload = {
        "phase": EXPECTED_GATE_PHASE,
        "status": EXPECTED_GATE_STATUS,
        "gate_state": EXPECTED_GATE_STATE,
        "recovery_request_id": (
            "xr11-wal-recovery-test"
        ),
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "planned_ebook_id": EBOOK_ID,
        "planned_offer_ids": [
            OFFER_ID
        ],
        "planned_ebook_item_values": ebook,
        "planned_store_offers": [
            {
                "store": "rakuten_kobo",
                "planned_offer_id": OFFER_ID,
                "values": offer,
            }
        ],
        "schema_snapshot": (
            schema_snapshot(database)
        ),
        "duplicate_match_count": 0,
        "required_pre_execution_database_sha256": (
            database_sha
        ),
        "required_pre_execution_wal_size": 0,
        "required_journal_mode": "wal",
        "recovery_snapshot_path": str(
            snapshot_path.resolve()
        ),
        "recovery_snapshot_sha256": (
            sha256_file(snapshot_path)
        ),
        "source_failed_lock_path": str(
            failed_lock_path.resolve()
        ),
        "source_failed_lock_digest_sha256": (
            canonical_digest(failed_lock)
        ),
        "approval_issued": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "production_status": "NO_GO",
    }

    gate = {
        **gate_payload,
        "recovery_final_gate_digest_sha256": (
            canonical_digest(gate_payload)
        ),
    }

    gate_path.write_text(
        json.dumps(gate),
        encoding="utf-8",
    )

    certificate_payload = {
        "phase": EXPECTED_CERTIFICATE_PHASE,
        "status": EXPECTED_CERTIFICATE_STATUS,
        "approval_state": (
            "ISSUED_NOT_CONSUMED"
        ),
        "recovery_final_gate_path": str(
            gate_path.resolve()
        ),
        "recovery_final_gate_file_sha256": (
            sha256_file(gate_path)
        ),
        "recovery_final_gate_digest_sha256": (
            gate[
                "recovery_final_gate_digest_sha256"
            ]
        ),
        "recovery_request_id": (
            gate["recovery_request_id"]
        ),
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "required_pre_execution_database_sha256": (
            database_sha
        ),
        "required_pre_execution_wal_size": 0,
        "required_journal_mode": "wal",
        "recovery_snapshot_path": str(
            snapshot_path.resolve()
        ),
        "recovery_snapshot_sha256": (
            sha256_file(snapshot_path)
        ),
        "approval_label": (
            EXPECTED_APPROVAL_LABEL
        ),
        "approval_scope": (
            EXPECTED_APPROVAL_SCOPE
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "planned_ebook_id": EBOOK_ID,
        "planned_offer_ids": [
            OFFER_ID
        ],
        "maximum_ebook_insert_count": 1,
        "maximum_store_offer_insert_count": 1,
        "wal_mode_allowed": True,
        "manual_wal_deletion_allowed": False,
        "manual_journal_mode_change_allowed": False,
        "authorizes_wal_recovery_import": True,
        "authorizes_database_write": True,
        "authorizes_workflow_write": False,
        "authorizes_wordpress_write": False,
        "authorizes_normal_x_fb_write": False,
        "old_certificate_replay_allowed": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "production_status": "NO_GO",
    }

    certificate = {
        **certificate_payload,
        "wal_recovery_approval_certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    certificate_path.write_text(
        json.dumps(certificate),
        encoding="utf-8",
    )

    return database, certificate_path


def test_valid_wal_import_commits_exact_rows(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    result = run_wal_recovery_import(
        approval_certificate_path=certificate,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "execution",
        lock_root=tmp_path / "locks",
    )

    assert result["status"] == (
        "PASS_WAL_RECOVERY_"
        "ONE_SHOT_IMPORT_COMMITTED"
    )
    assert result[
        "inserted_ebook_count"
    ] == 1
    assert result[
        "inserted_store_offer_count"
    ] == 1
    assert result[
        "logical_row_verification_passed"
    ] is True

    connection = sqlite3.connect(database)

    try:
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM ebook_items
            WHERE id = ?
            """,
            (EBOOK_ID,),
        ).fetchone()[0] == 1

        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM store_offers
            WHERE id = ?
            """,
            (OFFER_ID,),
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_replay_is_blocked(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    run_wal_recovery_import(
        approval_certificate_path=certificate,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "first",
        lock_root=tmp_path / "locks",
    )

    with pytest.raises(
        XR11WalRecoveryImportError,
        match="already been claimed or consumed",
    ):
        run_wal_recovery_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "second",
            lock_root=tmp_path / "locks",
        )


def test_failure_after_ebook_insert_rolls_back(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    with pytest.raises(
        XR11WalRecoveryImportError,
        match="test failure after ebook INSERT",
    ):
        run_wal_recovery_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "execution",
            lock_root=tmp_path / "locks",
            failure_injection_step=(
                "AFTER_EBOOK_INSERT"
            ),
        )

    connection = sqlite3.connect(database)

    try:
        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM ebook_items
            """
        ).fetchone()[0] == 0

        assert connection.execute(
            """
            SELECT COUNT(*)
            FROM store_offers
            """
        ).fetchone()[0] == 0
    finally:
        connection.close()


def test_tampered_certificate_is_rejected(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    value = json.loads(
        certificate.read_text(
            encoding="utf-8"
        )
    )

    value["planned_ebook_id"] = "tampered"

    certificate.write_text(
        json.dumps(value),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11WalRecoveryImportError,
        match="digest verification failed",
    ):
        run_wal_recovery_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "execution",
            lock_root=tmp_path / "locks",
        )


def test_nonempty_wal_blocks_before_claim(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    wal_path = Path(
        str(database) + "-wal"
    )

    wal_path.write_bytes(
        b"non-empty-test-wal"
    )

    with pytest.raises(
        XR11WalRecoveryImportError,
        match="WAL file is non-empty",
    ):
        run_wal_recovery_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "execution",
            lock_root=tmp_path / "locks",
        )

    assert not (
        tmp_path / "locks"
    ).exists()
