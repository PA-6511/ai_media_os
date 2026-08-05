from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.build_x_r11_manual_intake_import_prep import (
    read_table_schema,
)
from scripts.build_x_r11_wal_recovery_final_gate import (
    EXPECTED_CERTIFICATE_PHASE,
    EXPECTED_CERTIFICATE_STATUS,
    EXPECTED_FAILED_STATUS,
    EXPECTED_FINAL_GATE_PHASE,
    EXPECTED_FINAL_GATE_STATE,
    EXPECTED_FINAL_GATE_STATUS,
    EXPECTED_RUNNER_PHASE,
    XR11WalRecoveryFinalGateError,
    run_recovery_final_gate,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
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


def create_database(
    path: Path,
    *,
    wal_mode: bool,
) -> None:
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

        if wal_mode:
            connection.execute(
                "PRAGMA journal_mode = WAL"
            )

        connection.commit()
    finally:
        connection.close()


def schema_snapshot(
    database: Path,
) -> dict:
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
    *,
    wal_mode: bool = True,
) -> dict[str, Path]:
    database = tmp_path / "production.db"
    backup = tmp_path / "failed.backup.db"
    final_gate_path = tmp_path / "gate.json"
    certificate_path = tmp_path / "certificate.json"
    failed_result_path = tmp_path / "failed-result.json"
    failed_lock_path = tmp_path / "failed-lock.json"

    create_database(
        database,
        wal_mode=wal_mode,
    )

    source = sqlite3.connect(database)
    destination = sqlite3.connect(backup)

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

    database_sha = sha256_file(
        database
    )

    final_gate_payload = {
        "phase": EXPECTED_FINAL_GATE_PHASE,
        "status": EXPECTED_FINAL_GATE_STATUS,
        "gate_state": EXPECTED_FINAL_GATE_STATE,
        "final_gate_request_id": (
            "xr11-import-gate-test"
        ),
        "candidate": {
            "title": "のあ先輩はともだち。"
        },
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "planned_ebook_id": EBOOK_ID,
        "planned_ebook_item_values": ebook,
        "planned_store_offers": [
            {
                "store": "rakuten_kobo",
                "planned_offer_id": OFFER_ID,
                "retail_url_semantics": (
                    "PRODUCT_URL_NOT_AFFILIATE_URL"
                ),
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
        "approval_issued": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "production_status": "NO_GO",
    }

    final_gate = {
        **final_gate_payload,
        "final_gate_pack_digest_sha256": (
            canonical_digest(
                final_gate_payload
            )
        ),
    }

    final_gate_path.write_text(
        json.dumps(final_gate),
        encoding="utf-8",
    )

    certificate_payload = {
        "phase": EXPECTED_CERTIFICATE_PHASE,
        "status": EXPECTED_CERTIFICATE_STATUS,
        "approval_state": (
            "ISSUED_NOT_CONSUMED"
        ),
        "final_gate_pack_path": str(
            final_gate_path.resolve()
        ),
        "final_gate_pack_sha256": (
            sha256_file(final_gate_path)
        ),
        "final_gate_pack_digest_sha256": (
            final_gate[
                "final_gate_pack_digest_sha256"
            ]
        ),
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "planned_ebook_id": EBOOK_ID,
        "planned_offer_ids": [
            OFFER_ID
        ],
        "required_pre_execution_database_sha256": (
            database_sha
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "production_status": "NO_GO",
    }

    certificate = {
        **certificate_payload,
        "approval_certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    certificate_path.write_text(
        json.dumps(certificate),
        encoding="utf-8",
    )

    certificate_digest = certificate[
        "approval_certificate_digest_sha256"
    ]

    failed_result = {
        "phase": EXPECTED_RUNNER_PHASE,
        "status": EXPECTED_FAILED_STATUS,
        "approval_consumed": True,
        "database_commit_completed": False,
        "reexecution_allowed": False,
        "production_status": "NO_GO",
    }

    failed_result_path.write_text(
        json.dumps(failed_result),
        encoding="utf-8",
    )

    failed_lock = {
        "phase": EXPECTED_RUNNER_PHASE,
        "status": EXPECTED_FAILED_STATUS,
        "approval_certificate_digest_sha256": (
            certificate_digest
        ),
        "database_write_started": False,
        "database_commit_completed": False,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "production_status": "NO_GO",
    }

    failed_lock_path.write_text(
        json.dumps(failed_lock),
        encoding="utf-8",
    )

    return {
        "database": database,
        "backup": backup,
        "gate": final_gate_path,
        "certificate": certificate_path,
        "result": failed_result_path,
        "lock": failed_lock_path,
    }


def run_gate(
    tmp_path: Path,
    paths: dict[str, Path],
) -> dict:
    return run_recovery_final_gate(
        failed_result_path=paths["result"],
        failed_lock_path=paths["lock"],
        failed_backup_path=paths["backup"],
        consumed_certificate_path=(
            paths["certificate"]
        ),
        production_database_path=(
            paths["database"]
        ),
        expected_production_database_path=(
            paths["database"]
        ),
        output_root=tmp_path / "output",
    )


def test_valid_wal_recovery_gate_has_no_write(
    tmp_path: Path,
) -> None:
    paths = prepare(tmp_path)

    before = paths["database"].read_bytes()

    result = run_gate(
        tmp_path,
        paths,
    )

    assert result["status"] == (
        "PASS_WAL_RECOVERY_FINAL_GATE_"
        "READY_AWAITING_EXPLICIT_APPROVAL"
    )
    assert result["journal_mode"] == "wal"
    assert result["wal_size"] == 0
    assert result[
        "duplicate_match_count"
    ] == 0
    assert result[
        "approval_issued"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert paths[
        "database"
    ].read_bytes() == before


def test_non_wal_database_is_rejected(
    tmp_path: Path,
) -> None:
    paths = prepare(
        tmp_path,
        wal_mode=False,
    )

    with pytest.raises(
        XR11WalRecoveryFinalGateError,
        match="journal_mode=wal",
    ):
        run_gate(
            tmp_path,
            paths,
        )


def test_nonempty_wal_is_rejected(
    tmp_path: Path,
) -> None:
    paths = prepare(tmp_path)

    wal_path = Path(
        str(paths["database"])
        + "-wal"
    )

    wal_path.write_bytes(b"not-empty")

    with pytest.raises(
        XR11WalRecoveryFinalGateError,
        match="absent or empty WAL",
    ):
        run_gate(
            tmp_path,
            paths,
        )


def test_write_started_failure_is_rejected(
    tmp_path: Path,
) -> None:
    paths = prepare(tmp_path)

    lock = json.loads(
        paths["lock"].read_text()
    )

    lock["database_write_started"] = True

    paths["lock"].write_text(
        json.dumps(lock),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11WalRecoveryFinalGateError,
        match="before database write start",
    ):
        run_gate(
            tmp_path,
            paths,
        )


def test_nonfailed_lock_is_rejected(
    tmp_path: Path,
) -> None:
    paths = prepare(tmp_path)

    lock = json.loads(
        paths["lock"].read_text()
    )

    lock["status"] = "CONSUMED_COMMITTED"

    paths["lock"].write_text(
        json.dumps(lock),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11WalRecoveryFinalGateError,
        match="failed lock status is invalid",
    ):
        run_gate(
            tmp_path,
            paths,
        )
