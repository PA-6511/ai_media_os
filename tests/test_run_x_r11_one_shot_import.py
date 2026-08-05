from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import quote

import pytest

from scripts.build_x_r11_manual_intake_import_prep import (
    read_table_schema,
)
from scripts.build_x_r11_one_shot_import_final_gate import (
    run_final_gate,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)
from scripts.run_x_r11_one_shot_import import (
    EXPECTED_APPROVAL_LABEL,
    EXPECTED_APPROVAL_SCOPE,
    EXPECTED_CERTIFICATE_PHASE,
    XR11OneShotImportRunnerError,
    run_one_shot_import,
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
        connection.commit()
    finally:
        connection.close()


def schema_snapshot(
    database: Path,
) -> dict:
    connection = sqlite3.connect(
        (
            "file:"
            + quote(str(database))
            + "?mode=ro"
        ),
        uri=True,
    )
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


def create_import_prep_pack(
    path: Path,
    database: Path,
) -> None:
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

    payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "MANUAL-INTAKE-IMPORT-PREP"
        ),
        "status": "IMPORT_PREP_PACK_READY",
        "prep_state": (
            "IMPORT_PLAN_READY_NOT_EXECUTABLE"
        ),
        "approval_evidence": {
            "authorizes_import_prep": True,
            "authorizes_database_write": False,
        },
        "candidate": {
            "intake_id": (
                "x-r11-real-20260717-"
                "noa-senpai-11"
            ),
            "title": "のあ先輩はともだち。",
            "volume_label": "第11巻",
            "release_date": "2026-07-17",
            "publisher": "集英社",
            "authors": "あきやまえんま",
            "category": "comic",
        },
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "planned_ebook_id": EBOOK_ID,
        "planned_ebook_item_values": (
            ebook
        ),
        "planned_store_offers": [
            {
                "store": "rakuten_kobo",
                "planned_offer_id": OFFER_ID,
                "planned_store_item_id": (
                    offer["store_item_id"]
                ),
                "retail_url_semantics": (
                    "PRODUCT_URL_NOT_AFFILIATE_URL"
                ),
                "values": offer,
            }
        ],
        "ebook_insert_preview": {
            "table": "ebook_items",
            "execution_allowed": False,
        },
        "store_offer_insert_previews": [
            {
                "table": "store_offers",
                "execution_allowed": False,
            }
        ],
        "transaction_plan": [],
        "rollback_preview": {
            "execution_allowed": False,
            "planned_ebook_id": EBOOK_ID,
            "planned_offer_ids": [
                OFFER_ID
            ],
        },
        "schema_snapshot": (
            schema_snapshot(database)
        ),
        "schema_blockers": [],
        "duplicate_match_count": 0,
        "production_database_sha256": (
            sha256_file(database)
        ),
        "required_next_approval_label": (
            EXPECTED_APPROVAL_LABEL
        ),
        "one_shot_import_approval_issued": (
            False
        ),
        "execution_allowed": False,
        "database_import_allowed": False,
        "database_write": False,
        "wordpress_write": False,
        "normal_x_fb_write_allowed": False,
        "production_status": "NO_GO",
    }

    pack = {
        **payload,
        "import_prep_pack_digest_sha256": (
            canonical_digest(payload)
        ),
    }

    path.write_text(
        json.dumps(
            pack,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def create_certificate(
    path: Path,
    final_gate_path: Path,
) -> None:
    final_gate = json.loads(
        final_gate_path.read_text(
            encoding="utf-8"
        )
    )

    payload = {
        "phase": EXPECTED_CERTIFICATE_PHASE,
        "status": (
            "APPROVAL_ISSUED_NOT_CONSUMED"
        ),
        "approval_state": (
            "ISSUED_NOT_CONSUMED"
        ),
        "issued_at": (
            "2026-07-18T00:00:00+00:00"
        ),
        "final_gate_pack_path": str(
            final_gate_path.resolve()
        ),
        "final_gate_pack_sha256": (
            sha256_file(final_gate_path)
        ),
        "final_gate_request_id": (
            final_gate[
                "final_gate_request_id"
            ]
        ),
        "candidate_digest_sha256": (
            CANDIDATE_DIGEST
        ),
        "final_gate_pack_digest_sha256": (
            final_gate[
                "final_gate_pack_digest_sha256"
            ]
        ),
        "required_pre_execution_database_sha256": (
            final_gate[
                "required_pre_execution_database_sha256"
            ]
        ),
        "approval_label": (
            EXPECTED_APPROVAL_LABEL
        ),
        "approval_scope": (
            EXPECTED_APPROVAL_SCOPE
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "approval_expires_on_database_change": True,
        "approval_expires_on_schema_change": True,
        "approval_expires_on_plan_change": True,
        "planned_ebook_id": EBOOK_ID,
        "planned_offer_ids": [
            OFFER_ID
        ],
        "maximum_ebook_insert_count": 1,
        "maximum_store_offer_insert_count": 1,
        "one_transaction_required": True,
        "rollback_on_any_failure": True,
        "post_insert_verification_required": True,
        "authorizes_one_shot_database_import": True,
        "authorizes_database_write": True,
        "authorizes_workflow_write": False,
        "authorizes_wordpress_write": False,
        "authorizes_normal_x_fb_write": False,
        "authorizes_x_api_call": False,
        "authorizes_x_post": False,
        "execution_allowed": False,
        "database_import_allowed": False,
        "production_execution": False,
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "ONE-SHOT-IMPORT-RUNNER"
        ),
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SHOT_IMPORT_APPROVAL_"
            "ISSUED_NOT_CONSUMED"
        ),
    }

    certificate = {
        **payload,
        "approval_certificate_digest_sha256": (
            canonical_digest(payload)
        ),
    }

    path.write_text(
        json.dumps(
            certificate,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def prepare(
    tmp_path: Path,
) -> tuple[Path, Path]:
    database = tmp_path / "production.db"
    prep_path = tmp_path / "prep.json"
    gate_root = tmp_path / "gate"
    certificate_path = (
        tmp_path / "certificate.json"
    )

    create_database(database)
    create_import_prep_pack(
        prep_path,
        database,
    )

    gate_result = run_final_gate(
        import_prep_pack_path=prep_path,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=gate_root,
    )

    create_certificate(
        certificate_path,
        Path(
            gate_result[
                "final_gate_pack_path"
            ]
        ),
    )

    return database, certificate_path


def test_valid_import_commits_exact_rows(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    result = run_one_shot_import(
        approval_certificate_path=certificate,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "execution",
        lock_root=tmp_path / "locks",
    )

    assert result["status"] == (
        "PASS_ONE_SHOT_IMPORT_COMMITTED"
    )
    assert result[
        "inserted_ebook_count"
    ] == 1
    assert result[
        "inserted_store_offer_count"
    ] == 1

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

    run_one_shot_import(
        approval_certificate_path=certificate,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "first",
        lock_root=tmp_path / "locks",
    )

    with pytest.raises(
        XR11OneShotImportRunnerError,
        match="already been claimed or consumed",
    ):
        run_one_shot_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "second",
            lock_root=tmp_path / "locks",
        )


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

    before = database.read_bytes()

    with pytest.raises(
        XR11OneShotImportRunnerError,
        match="digest verification failed",
    ):
        run_one_shot_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "execution",
            lock_root=tmp_path / "locks",
        )

    assert database.read_bytes() == before


def test_database_change_invalidates_approval(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    connection = sqlite3.connect(database)

    try:
        connection.execute(
            """
            INSERT INTO ebook_items (
                id,
                source_name,
                source_item_id,
                title,
                item_type,
                is_excluded,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "other",
                "other",
                "other",
                "他作品",
                "tankobon",
                0,
                "2026-07-18 00:00:00",
                "2026-07-18 00:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        XR11OneShotImportRunnerError,
        match="database changed",
    ):
        run_one_shot_import(
            approval_certificate_path=certificate,
            production_database_path=database,
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "execution",
            lock_root=tmp_path / "locks",
        )


def test_failure_after_ebook_insert_rolls_back(
    tmp_path: Path,
) -> None:
    database, certificate = prepare(
        tmp_path
    )

    with pytest.raises(
        XR11OneShotImportRunnerError,
        match="test failure after ebook INSERT",
    ):
        run_one_shot_import(
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
