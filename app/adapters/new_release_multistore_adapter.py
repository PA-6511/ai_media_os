from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


STORE_MAPPINGS = (
    {
        "store_name": "amazon",
        "url_field": "amazon_url",
        "price_field": "amazon_price_jpy",
    },
    {
        "store_name": "rakuten_kobo",
        "url_field": "rakuten_kobo_url",
        "price_field": "rakuten_kobo_price_jpy",
    },
    {
        "store_name": "dmm",
        "url_field": "dmm_url",
        "price_field": "dmm_price_jpy",
    },
)


CATEGORY_TO_ITEM_TYPE = {
    "comic": "tankobon",
    "manga": "tankobon",
    "light_novel": "light_novel",
    "novel": "general_book",
    "general_book": "general_book",
}


@dataclass(frozen=True)
class AdapterSummary:
    input_rows: int
    output_rows: int
    catalog_fallback_rows: int


def clean(value: str | None) -> str:
    return (value or "").strip()


def map_item_type(category: str | None) -> str:
    normalized = clean(category).lower()
    return CATEGORY_TO_ITEM_TYPE.get(normalized, "unknown")


def build_store_item_id(
    *,
    item_id: str,
    store_name: str,
) -> str:
    return f"{store_name}:{item_id}"


def adapt_multistore_row(
    row: dict[str, str],
) -> list[dict[str, str]]:
    item_id = clean(row.get("item_id"))
    title = clean(row.get("title"))

    if not item_id:
        raise ValueError("item_id is required")

    if not title:
        raise ValueError("title is required")

    author_name = clean(
        row.get("authors") or row.get("author") or row.get("author_name")
    )
    publisher_name = clean(
        row.get("publisher") or row.get("publisher_name")
    )
    common = {
        "source_name": "new_release_multistore",
        "source_item_id": item_id,
        "title": title,
        "isbn": clean(row.get("isbn") or row.get("isbn13")),
        "normalized_title": title,
        "volume_label": clean(row.get("volume_label") or row.get("volume_number")),
        "author_name": author_name,
        "author": author_name,
        "publisher_name": publisher_name,
        "publisher": publisher_name,
        "series_name": clean(row.get("series_name") or row.get("series")),
        "release_date": clean(row.get("release_date")),
        "item_type": map_item_type(row.get("category")),
        "source_row_sha256": clean(row.get("source_row_sha256")),
    }

    adapted_rows: list[dict[str, str]] = []

    for mapping in STORE_MAPPINGS:
        store_name = mapping["store_name"]
        product_url = clean(row.get(mapping["url_field"]))
        price = clean(row.get(mapping["price_field"]))
        if store_name == "rakuten_kobo":
            price = price or clean(
                row.get("rakuten_kobo_price")
                or row.get("item_price")
                or row.get("price")
                or row.get("price_amount")
            )

        # URLも価格もないストアは未確認扱いとして登録しない。
        if not product_url and not price:
            continue

        adapted_rows.append(
            {
                **common,
                "store_name": store_name,
                "store_item_id": build_store_item_id(
                    item_id=item_id,
                    store_name=store_name,
                ),
                "product_url": product_url,
                "affiliate_url": (
                    clean(
                        row.get("rakuten_kobo_affiliate_url")
                        or row.get("affiliate_url")
                    )
                    if store_name == "rakuten_kobo"
                    else ""
                ),
                "price": price,
                "currency": (
                    clean(
                        row.get("rakuten_kobo_currency")
                        or row.get("currency")
                        or row.get("currency_code")
                    )
                    or ("JPY" if price and store_name == "rakuten_kobo" else "")
                ),
                "discount_rate": "",
                "point_rate": "",
                "verified_at": (
                    clean(row.get("verified_at"))
                    if store_name == "rakuten_kobo"
                    else ""
                ),
                "verification_method": (
                    clean(row.get("verification_method"))
                    if store_name == "rakuten_kobo"
                    else ""
                ),
            }
        )

    # ストア情報がまだない新刊も、書籍マスタへ登録できるようにする。
    if not adapted_rows:
        adapted_rows.append(
            {
                **common,
                "store_name": "new_release_catalog",
                "store_item_id": build_store_item_id(
                    item_id=item_id,
                    store_name="new_release_catalog",
                ),
                "product_url": clean(
                    row.get("publisher_confirmation_url")
                ),
                "affiliate_url": "",
                "price": "",
                "discount_rate": "",
                "point_rate": "",
                "verified_at": "",
                "verification_method": "",
            }
        )

    return adapted_rows


def iter_adapted_rows(
    input_path: Path,
) -> Iterator[dict[str, str]]:
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV header is missing")

        required_columns = {
            "item_id",
            "title",
            "release_date",
        }

        missing_columns = required_columns - set(reader.fieldnames)

        if missing_columns:
            raise ValueError(
                "Missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                yield from adapt_multistore_row(row)
            except Exception as exc:
                raise ValueError(
                    f"Multistore adapter failed at row "
                    f"{row_number}: {exc}"
                ) from exc


def adapt_multistore_csv(
    *,
    input_path: Path,
    output_path: Path,
) -> AdapterSummary:
    rows = list(iter_adapted_rows(input_path))

    input_row_count = 0
    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        input_row_count = sum(1 for _ in csv.DictReader(file))

    fieldnames = [
        "source_name",
        "source_item_id",
        "title",
        "isbn",
        "normalized_title",
        "volume_label",
        "author_name",
        "author",
        "publisher_name",
        "publisher",
        "series_name",
        "release_date",
        "item_type",
        "store_name",
        "store_item_id",
        "product_url",
        "affiliate_url",
        "price",
        "currency",
        "discount_rate",
        "point_rate",
        "source_row_sha256",
        "verified_at",
        "verification_method",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fallback_count = sum(
        1
        for row in rows
        if row["store_name"] == "new_release_catalog"
    )

    return AdapterSummary(
        input_rows=input_row_count,
        output_rows=len(rows),
        catalog_fallback_rows=fallback_count,
    )
