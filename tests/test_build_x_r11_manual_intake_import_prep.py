from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.build_x_r11_manual_intake_import_prep import (
    EXPECTED_APPROVAL_LABEL,
    EXPECTED_APPROVAL_SCOPE,
    EXPECTED_REVIEW_PHASE,
    EXPECTED_REVIEW_STATE,
    EXPECTED_REVIEW_STATUS,
    XR11ImportPrepError,
    run_import_prep,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


REVIEW_REQUEST_ID = (
    "xr11-manual-review-"
    "d233e7afa9a33dab0c9ee797"
)


def candidate() -> dict[str, str]:
    return {
        "intake_id": (
            "x-r11-real-20260717-noa-senpai-11"
        ),
        "title": "のあ先輩はともだち。",
        "volume_label": "第11巻",
        "release_date": "2026-07-17",
        "publisher": "集英社",
        "authors": "あきやまえんま",
        "category": "comic",
        "source_discovery_url": (
            "https://books.rakuten.co.jp/"
            "rk/real-item/"
        ),
        "publisher_confirmation_url": (
            "https://www.shueisha.co.jp/"
            "books/items/real-item"
        ),
        "amazon_url": "",
        "rakuten_kobo_url": (
            "https://books.rakuten.co.jp/"
            "rk/real-item/"
        ),
        "dmm_url": "",
        "description_mode": "MINIMAL",
        "human_review_state": "NOT_REVIEWED",
    }


def create_database(
    path: Path,
    *,
    include_offer_url: bool = True,
) -> None:
    connection = sqlite3.connect(path)

    try:
        connection.execute(
            """
            CREATE TABLE ebook_items (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_item_id TEXT NOT NULL,
                title TEXT NOT NULL,
                volume_label TEXT,
                release_date TEXT NOT NULL,
                publisher_name TEXT,
                author_name TEXT,
                item_type TEXT NOT NULL,
                wordpress_post_id INTEGER,
                wordpress_status TEXT,
                is_excluded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (
                    source_name,
                    source_item_id
                )
            )
            """
        )

        if include_offer_url:
            connection.execute(
                """
                CREATE TABLE store_offers (
                    id TEXT PRIMARY KEY,
                    ebook_item_id TEXT NOT NULL,
                    store TEXT NOT NULL,
                    store_item_id TEXT NOT NULL,
                    product_url TEXT,
                    affiliate_url TEXT,
                    last_checked_at TEXT NOT NULL,
                    FOREIGN KEY (
                        ebook_item_id
                    )
                    REFERENCES ebook_items(id)
                )
                """
            )
        else:
            connection.execute(
                """
                CREATE TABLE store_offers (
                    id TEXT PRIMARY KEY,
                    ebook_item_id TEXT NOT NULL,
                    store TEXT NOT NULL,
                    store_item_id TEXT NOT NULL,
                    affiliate_url TEXT,
                    last_checked_at TEXT NOT NULL
                )
                """
            )

        connection.commit()
    finally:
        connection.close()


def write_review_pack(
    path: Path,
) -> tuple[dict, str]:
    item = candidate()
    candidate_digest = canonical_digest(
        item
    )

    payload = {
        "phase": EXPECTED_REVIEW_PHASE,
        "status": EXPECTED_REVIEW_STATUS,
        "review_state": EXPECTED_REVIEW_STATE,
        "review_request_id": (
            REVIEW_REQUEST_ID
        ),
        "required_approval_label": (
            EXPECTED_APPROVAL_LABEL
        ),
        "candidate": item,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "duplicate_match_count": 0,
        "explicit_approval_required": True,
        "approval_issued": False,
        "database_import_allowed": False,
        "wordpress_draft_creation_allowed": (
            False
        ),
        "normal_x_fb_write_allowed": False,
        "production_status": "NO_GO",
    }

    pack = {
        **payload,
        "human_review_pack_digest_sha256": (
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

    return pack, candidate_digest


def run_prep(
    tmp_path: Path,
    *,
    database: Path,
    review_pack: Path,
    candidate_digest: str,
    output_name: str,
    approval_label: str = (
        EXPECTED_APPROVAL_LABEL
    ),
) -> dict:
    return run_import_prep(
        human_review_pack_path=(
            review_pack
        ),
        approval_review_request_id=(
            REVIEW_REQUEST_ID
        ),
        approval_candidate_digest=(
            candidate_digest
        ),
        approval_label=approval_label,
        approval_scope=(
            EXPECTED_APPROVAL_SCOPE
        ),
        production_database_path=(
            database
        ),
        expected_production_database_path=(
            database
        ),
        output_root=(
            tmp_path / output_name
        ),
    )


def test_valid_import_prep_has_no_write(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    review_pack = tmp_path / "review.json"

    create_database(database)

    _, digest = write_review_pack(
        review_pack
    )

    database_before = database.read_bytes()

    result = run_prep(
        tmp_path,
        database=database,
        review_pack=review_pack,
        candidate_digest=digest,
        output_name="valid",
    )

    assert result["status"] == (
        "PASS_IMPORT_PREP_READY_"
        "AWAITING_ONE_SHOT_IMPORT_APPROVAL"
    )
    assert result[
        "planned_store_offer_count"
    ] == 1
    assert result[
        "database_import_allowed"
    ] is False
    assert result[
        "execution_allowed"
    ] is False

    pack = json.loads(
        Path(
            result[
                "import_prep_pack_path"
            ]
        ).read_text(
            encoding="utf-8"
        )
    )

    ebook_values = pack[
        "planned_ebook_item_values"
    ]
    offer_values = pack[
        "planned_store_offers"
    ][0]["values"]

    assert ebook_values[
        "source_name"
    ] == "x_r11_manual_intake"
    assert ebook_values[
        "source_item_id"
    ] == (
        "x-r11-real-20260717-"
        "noa-senpai-11"
    )
    assert ebook_values[
        "item_type"
    ] == "tankobon"
    assert ebook_values[
        "publisher_name"
    ] == "集英社"
    assert ebook_values[
        "author_name"
    ] == "あきやまえんま"

    assert offer_values[
        "store_item_id"
    ] == "real-item"
    assert offer_values[
        "product_url"
    ].endswith(
        "/rk/real-item/"
    )
    assert offer_values[
        "affiliate_url"
    ] is None
    assert offer_values[
        "last_checked_at"
    ]

    assert database.read_bytes() == (
        database_before
    )


def test_wrong_approval_label_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    review_pack = tmp_path / "review.json"

    create_database(database)

    _, digest = write_review_pack(
        review_pack
    )

    with pytest.raises(
        XR11ImportPrepError,
        match="approval label is invalid",
    ):
        run_prep(
            tmp_path,
            database=database,
            review_pack=review_pack,
            candidate_digest=digest,
            output_name="wrong_label",
            approval_label="WRONG",
        )


def test_candidate_digest_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    review_pack = tmp_path / "review.json"

    create_database(database)
    write_review_pack(review_pack)

    with pytest.raises(
        XR11ImportPrepError,
        match=(
            "approval candidate digest "
            "does not match"
        ),
    ):
        run_prep(
            tmp_path,
            database=database,
            review_pack=review_pack,
            candidate_digest="0" * 64,
            output_name="wrong_digest",
        )


def test_existing_book_blocks_import_prep(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    review_pack = tmp_path / "review.json"

    create_database(database)

    _, digest = write_review_pack(
        review_pack
    )

    connection = sqlite3.connect(
        database
    )

    try:
        connection.execute(
            """
            INSERT INTO ebook_items (
                id,
                source_name,
                source_item_id,
                title,
                release_date,
                item_type,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "existing",
                "existing_fixture",
                "existing-noa-senpai-11",
                "のあ先輩はともだち。",
                "2026-07-17",
                "tankobon",
                "2026-07-17 00:00:00.000000",
                "2026-07-17 00:00:00.000000",
            ),
        )
        connection.commit()
    finally:
        connection.close()

    result = run_prep(
        tmp_path,
        database=database,
        review_pack=review_pack,
        candidate_digest=digest,
        output_name="duplicate",
    )

    assert result["status"] == (
        "BLOCKED_IMPORT_PREP_"
        "DUPLICATE_FOUND"
    )
    assert result[
        "duplicate_match_count"
    ] >= 1


def test_missing_store_url_column_blocks_prep(
    tmp_path: Path,
) -> None:
    database = tmp_path / "production.db"
    review_pack = tmp_path / "review.json"

    create_database(
        database,
        include_offer_url=False,
    )

    _, digest = write_review_pack(
        review_pack
    )

    result = run_prep(
        tmp_path,
        database=database,
        review_pack=review_pack,
        candidate_digest=digest,
        output_name="missing_url",
    )

    assert result["status"] == (
        "BLOCKED_IMPORT_PREP_"
        "SCHEMA_MAPPING_INCOMPLETE"
    )
    assert (
        "STORE_PRODUCT_URL_COLUMN_NOT_FOUND"
        in result["schema_blockers"]
    )
