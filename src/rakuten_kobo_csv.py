from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_ID = "NEW_RELEASE_BATCH_MULTISTORE_INPUT_SCHEMA_V2"
VERIFICATION_METHOD = "RAKUTEN_KOBO_API_RESPONSE"
CSV_FIELDNAMES = (
    "batch_id",
    "item_id",
    "title",
    "release_date",
    "category",
    "rakuten_kobo_url",
    "image_url",
    "wordpress_status",
    "schema_id",
    "record_status",
    "publish_ready",
    "pr_required",
    "price_notice_required",
    "dmm_match_status",
    "amazon_match_status",
    "source_row_sha256",
    "author_name",
    "publisher_name",
    "isbn13",
    "item_number",
    "volume_label",
    "verified_at",
    "verification_method",
    "rakuten_kobo_price",
    "rakuten_kobo_currency",
    "edition_type",
    "available_store_count",
)

ISBN13_SEPARATOR_PATTERN = re.compile(r"[-‐‑‒–—―−﹘﹣－\s]")


def normalize_isbn13(value: object) -> str:
    if value is None:
        return ""
    normalized = ISBN13_SEPARATOR_PATTERN.sub("", str(value))
    if not normalized:
        return ""
    if re.fullmatch(r"[0-9]{13}", normalized) is None:
        raise ValueError("ISBN-13 must normalize to exactly 13 ASCII digits")
    total = sum(
        int(digit) * (1 if index % 2 == 0 else 3)
        for index, digit in enumerate(normalized[:12])
    )
    check_digit = (10 - total % 10) % 10
    if check_digit != int(normalized[12]):
        raise ValueError("ISBN-13 check digit is invalid")
    return normalized


def _metadata_text(value: object) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or "")).strip())


def normalize_author_name(value: object) -> str:
    if value is None:
        raw_parts: Iterable[object] = ()
    elif isinstance(value, str):
        raw_parts = re.split(r"[|｜／]", value)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_parts = value
    else:
        raise ValueError("Rakuten Kobo author must be a string or string sequence")

    parts: list[str] = []
    seen: set[str] = set()
    for raw_part in raw_parts:
        if not isinstance(raw_part, str):
            raise ValueError("Rakuten Kobo author entries must be strings")
        part = _metadata_text(raw_part)
        if part and part not in seen:
            parts.append(part)
            seen.add(part)
    return "|".join(parts)


def normalize_publisher_name(value: object) -> str:
    return _metadata_text(value)


def _canonical_item_sha256(item: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        item,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _release_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for format_string in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(text, format_string).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unsupported Rakuten Kobo salesDate: {text!r}")


def _response_items(response: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    wrappers = response.get("Items")
    if not isinstance(wrappers, list):
        raise ValueError("Rakuten Kobo response Items must be a list")
    items: list[Mapping[str, Any]] = []
    for index, wrapper in enumerate(wrappers):
        if not isinstance(wrapper, Mapping) or not isinstance(
            wrapper.get("Item"), Mapping
        ):
            raise ValueError(f"Rakuten Kobo Items[{index}].Item must be an object")
        items.append(wrapper["Item"])
    return tuple(items)


def response_to_csv_rows(
    response: Mapping[str, Any],
    *,
    batch_id: str,
    verified_at: str,
) -> tuple[dict[str, str], ...]:
    batch = str(batch_id or "").strip()
    verified = str(verified_at or "").strip()
    if not batch:
        raise ValueError("batch_id is required")
    try:
        parsed_verified = datetime.fromisoformat(verified.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("verified_at must be ISO-8601") from exc
    if parsed_verified.tzinfo is None or parsed_verified.utcoffset() is None:
        raise ValueError("verified_at must include a timezone")

    rows: list[dict[str, str]] = []
    for item in _response_items(response):
        title = _metadata_text(item.get("title"))
        product_url = str(item.get("itemUrl") or "").strip()
        source_identifier = str(
            item.get("itemNumber") or item.get("isbn") or product_url
        ).strip()
        if not title or not product_url or not source_identifier:
            raise ValueError(
                "Rakuten Kobo item requires title, itemUrl, and a stable identifier"
            )
        item_digest = hashlib.sha256(source_identifier.encode("utf-8")).hexdigest()
        row = {field: "" for field in CSV_FIELDNAMES}
        row.update(
            {
                "batch_id": batch,
                "item_id": f"RAKUTEN_KOBO_{item_digest[:16]}",
                "title": title,
                "release_date": _release_date(item.get("salesDate")),
                "category": "コミック",
                "rakuten_kobo_url": product_url,
                "image_url": str(
                    item.get("mediumImageUrl")
                    or item.get("largeImageUrl")
                    or item.get("smallImageUrl")
                    or ""
                ).strip(),
                "wordpress_status": "draft",
                "schema_id": SCHEMA_ID,
                "record_status": "READY_FOR_DRAFT",
                "publish_ready": "true",
                "pr_required": "true",
                "price_notice_required": "true",
                "dmm_match_status": "NOT_FOUND",
                "amazon_match_status": "NOT_FOUND",
                "source_row_sha256": _canonical_item_sha256(item),
                "author_name": normalize_author_name(item.get("author")),
                # publisherName is the publisher.  A label field is intentionally
                # never used as a fallback because label and publisher differ.
                "publisher_name": normalize_publisher_name(
                    item.get("publisherName")
                ),
                "isbn13": normalize_isbn13(item.get("isbn")),
                "item_number": str(item.get("itemNumber") or "").strip(),
                "verified_at": parsed_verified.isoformat(),
                "verification_method": VERIFICATION_METHOD,
                "rakuten_kobo_price": str(item.get("itemPrice") or "").strip(),
                "rakuten_kobo_currency": "JPY",
                "edition_type": "volume",
                "available_store_count": "1",
            }
        )
        rows.append(row)
    return tuple(rows)


def write_response_csv(
    response: Mapping[str, Any],
    *,
    output_path: Path,
    batch_id: str,
    verified_at: str,
) -> tuple[dict[str, str], ...]:
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"refusing to overwrite CSV: {output_path}")
    rows = response_to_csv_rows(
        response,
        batch_id=batch_id,
        verified_at=verified_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return rows
