from __future__ import annotations

import csv
from pathlib import Path

from app.adapters.new_release_multistore_adapter import (
    adapt_multistore_csv,
    adapt_multistore_row,
    map_item_type,
)


def test_map_item_type() -> None:
    assert map_item_type("comic") == "tankobon"
    assert map_item_type("light_novel") == "light_novel"
    assert map_item_type("general_book") == "general_book"
    assert map_item_type("unknown-category") == "unknown"


def test_adapt_row_creates_multiple_store_offers() -> None:
    row = {
        "item_id": "ITEM-001",
        "title": "Test Comic",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
        "publisher": "Test Publisher",
        "authors": "Author A|Author B",
        "isbn13": "9781234567890",
        "category": "comic",
        "amazon_url": "https://example.com/amazon/1",
        "rakuten_kobo_url": "https://example.com/kobo/1",
        "dmm_url": "",
        "amazon_price_jpy": "770",
        "rakuten_kobo_price_jpy": "750",
        "dmm_price_jpy": "",
        "verified_at": "2026-08-01T09:00:00+09:00",
        "verification_method": "RAKUTEN_KOBO_API_RESPONSE",
    }

    adapted = adapt_multistore_row(row)

    assert len(adapted) == 2
    assert adapted[0]["source_name"] == "new_release_multistore"
    assert adapted[0]["source_item_id"] == "ITEM-001"
    assert adapted[0]["item_type"] == "tankobon"
    assert adapted[0]["author_name"] == "Author A|Author B"
    assert adapted[0]["publisher_name"] == "Test Publisher"
    assert adapted[0]["isbn"] == "9781234567890"

    store_names = {item["store_name"] for item in adapted}
    assert store_names == {"amazon", "rakuten_kobo"}
    by_store = {item["store_name"]: item for item in adapted}
    assert by_store["amazon"]["verified_at"] == ""
    assert by_store["amazon"]["verification_method"] == ""
    assert by_store["rakuten_kobo"]["verified_at"] == (
        "2026-08-01T09:00:00+09:00"
    )
    assert by_store["rakuten_kobo"]["verification_method"] == (
        "RAKUTEN_KOBO_API_RESPONSE"
    )


def test_adapt_row_uses_catalog_fallback() -> None:
    row = {
        "item_id": "ITEM-002",
        "title": "Catalog Only Book",
        "release_date": "2026-07-17",
        "category": "comic",
        "publisher_confirmation_url": (
            "https://publisher.example.com/item-002"
        ),
    }

    adapted = adapt_multistore_row(row)

    assert len(adapted) == 1
    assert adapted[0]["store_name"] == "new_release_catalog"
    assert adapted[0]["product_url"] == (
        "https://publisher.example.com/item-002"
    )


def test_adapt_multistore_csv(tmp_path: Path) -> None:
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    input_path.write_text(
        (
            "item_id,title,volume_label,release_date,"
            "publisher,authors,category,"
            "amazon_url,rakuten_kobo_url,dmm_url,"
            "amazon_price_jpy,rakuten_kobo_price_jpy,"
            "dmm_price_jpy,publisher_confirmation_url\n"
            "ITEM-003,Test Book,第1巻,2026-07-17,"
            "Publisher,Author,comic,"
            "https://example.com/amazon/3,,,"
            "770,,,\n"
        ),
        encoding="utf-8",
    )

    summary = adapt_multistore_csv(
        input_path=input_path,
        output_path=output_path,
    )

    assert summary.input_rows == 1
    assert summary.output_rows == 1
    assert summary.catalog_fallback_rows == 0

    with output_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))

    assert len(rows) == 1
    assert rows[0]["store_name"] == "amazon"
    assert rows[0]["price"] == "770"
