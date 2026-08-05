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
    REQUIRED_APPROVAL_LABEL,
    XR11OneShotImportFinalGateError,
    run_final_gate,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
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
) -> dict:
    generated_at = (
        "2026-07-17 16:16:03.507558"
    )

    ebook_values = {
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
        "created_at": generated_at,
        "updated_at": generated_at,
    }

    offer_values = {
        "id": (
            "983647ba-0203-5873-"
            "aea8-f7073401dcf9"
        ),
        "ebook_item_id": ebook_values["id"],
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
        "last_checked_at": generated_at,
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
            "d233e7afa9a33dab0c9ee797"
            "f2ee6ebde6f29809075cf741"
            "9ec0bf98af3294fd"
        ),
        "planned_ebook_id": (
            ebook_values["id"]
        ),
        "planned_ebook_item_values": (
            ebook_values
        ),
        "planned_store_offers": [
            {
                "store": "rakuten_kobo",
                "planned_offer_id": (
                    offer_values["id"]
                ),
                "planned_store_item_id": (
                    offer_values[
                        "store_item_id"
                    ]
                ),
                "retail_url_semantics": (
                    "PRODUCT_URL_NOT_AFFILIATE_URL"
                ),
                "values": offer_values,
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
            "planned_ebook_id": (
                ebook_values["id"]
            ),
            "planned_offer_ids": [
                offer_values["id"]
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
            REQUIRED_APPROVAL_LABEL
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

    return pack


def test_valid_final_gate_has_no_write(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    pack_path = tmp_path / "prep.json"

    create_database(database)
    create_import_prep_pack(
        pack_path,
        database,
    )

    before = database.read_bytes()

    result = run_final_gate(
        import_prep_pack_path=pack_path,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "out",
    )

    assert result["status"] == (
        "PASS_ONE_SHOT_IMPORT_FINAL_GATE_"
        "READY_AWAITING_EXPLICIT_APPROVAL"
    )
    assert result[
        "duplicate_match_count"
    ] == 0
    assert result[
        "approval_issued"
    ] is False
    assert result[
        "execution_allowed"
    ] is False
    assert result[
        "database_import_allowed"
    ] is False
    assert database.read_bytes() == before


def test_tampered_pack_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    pack_path = tmp_path / "prep.json"

    create_database(database)

    pack = create_import_prep_pack(
        pack_path,
        database,
    )

    pack[
        "planned_ebook_item_values"
    ]["title"] = "改ざん"

    pack_path.write_text(
        json.dumps(pack),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11OneShotImportFinalGateError,
        match="digest verification failed",
    ):
        run_final_gate(
            import_prep_pack_path=pack_path,
            production_database_path=(
                database
            ),
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "out",
        )


def test_database_sha_change_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    pack_path = tmp_path / "prep.json"

    create_database(database)
    create_import_prep_pack(
        pack_path,
        database,
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
                "2026-07-17 00:00:00",
                "2026-07-17 00:00:00",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        XR11OneShotImportFinalGateError,
        match="database SHA changed",
    ):
        run_final_gate(
            import_prep_pack_path=pack_path,
            production_database_path=(
                database
            ),
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "out",
        )


def test_existing_candidate_is_blocked(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    pack_path = tmp_path / "prep.json"

    create_database(database)

    pack = create_import_prep_pack(
        pack_path,
        database,
    )

    ebook = pack[
        "planned_ebook_item_values"
    ]

    connection = sqlite3.connect(database)

    try:
        connection.execute(
            """
            INSERT INTO ebook_items (
                id,
                source_name,
                source_item_id,
                title,
                volume_label,
                release_date,
                publisher_name,
                author_name,
                item_type,
                is_excluded,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                ebook["id"],
                ebook["source_name"],
                ebook["source_item_id"],
                ebook["title"],
                ebook["volume_label"],
                ebook["release_date"],
                ebook["publisher_name"],
                ebook["author_name"],
                ebook["item_type"],
                ebook["is_excluded"],
                ebook["created_at"],
                ebook["updated_at"],
            ),
        )
        connection.commit()
    finally:
        connection.close()

    pack[
        "production_database_sha256"
    ] = sha256_file(database)

    payload = {
        key: value
        for key, value in pack.items()
        if key
        != "import_prep_pack_digest_sha256"
    }

    pack[
        "import_prep_pack_digest_sha256"
    ] = canonical_digest(payload)

    pack_path.write_text(
        json.dumps(pack),
        encoding="utf-8",
    )

    result = run_final_gate(
        import_prep_pack_path=pack_path,
        production_database_path=database,
        expected_production_database_path=(
            database
        ),
        output_root=tmp_path / "out",
    )

    assert result["status"] == (
        "BLOCKED_ONE_SHOT_IMPORT_"
        "FINAL_GATE_DUPLICATE_FOUND"
    )
    assert result[
        "duplicate_match_count"
    ] >= 1


def test_non_null_affiliate_url_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    pack_path = tmp_path / "prep.json"

    create_database(database)

    pack = create_import_prep_pack(
        pack_path,
        database,
    )

    pack[
        "planned_store_offers"
    ][0]["values"]["affiliate_url"] = (
        "https://affiliate.invalid/"
    )

    payload = {
        key: value
        for key, value in pack.items()
        if key
        != "import_prep_pack_digest_sha256"
    }

    pack[
        "import_prep_pack_digest_sha256"
    ] = canonical_digest(payload)

    pack_path.write_text(
        json.dumps(pack),
        encoding="utf-8",
    )

    with pytest.raises(
        XR11OneShotImportFinalGateError,
        match="affiliate_url",
    ):
        run_final_gate(
            import_prep_pack_path=pack_path,
            production_database_path=(
                database
            ),
            expected_production_database_path=(
                database
            ),
            output_root=tmp_path / "out",
        )
