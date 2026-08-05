#!/usr/bin/env python3
"""Safely backfill existing ebook store offers from a local CSV.

Default mode is DRY_RUN.  This module performs no network, WordPress, or X
operations and never creates ``ebook_items``.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys

from sqlalchemy import select


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from app.db.models import EbookItem, StoreOffer  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class BackfillSummary:
    mode: str
    processed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    review: int = 0
    missing_item: int = 0
    failed: int = 0
    database_write_performed: bool = False
    external_network_performed: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Commit the transaction. Default is DRY_RUN rollback.",
    )
    return parser.parse_args(argv)


def _price(value: str) -> Decimal | None:
    normalized = value.strip().replace(",", "")
    if not normalized:
        return None
    try:
        result = Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError("price must be a non-negative number") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("price must be a non-negative number")
    return result


def _observed_at(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError as exc:
        raise ValueError("observed_at must be ISO-8601") from exc


def _titles_match(existing: str, supplied: str) -> bool:
    normalized_supplied = " ".join(supplied.split()).casefold()
    if not normalized_supplied:
        return True
    normalized_existing = " ".join(existing.split()).casefold()
    return SequenceMatcher(None, normalized_existing, normalized_supplied).ratio() >= 0.6


def run_backfill(session: object, csv_path: Path, *, execute: bool = False) -> BackfillSummary:
    summary = BackfillSummary(mode="EXECUTE" if execute else "DRY_RUN")
    required = {"item_id", "title", "store_code", "store_item_id"}
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ValueError(
                    "CSV requires columns: " + ", ".join(sorted(required))
                )
            for row_number, row in enumerate(reader, start=2):
                item_id = str(row.get("item_id") or "").strip()
                item = session.scalar(
                    select(EbookItem).where(
                        EbookItem.source_item_id == item_id
                    )
                )
                if item is None:
                    summary.missing_item += 1
                    continue
                if not _titles_match(item.title, str(row.get("title") or "")):
                    summary.review += 1
                    continue
                store_name = str(row.get("store_code") or "").strip()
                store_item_id = str(row.get("store_item_id") or "").strip()
                if not store_name or not store_item_id:
                    raise ValueError(f"row {row_number}: store_code/store_item_id is required")
                sha256 = str(row.get("source_row_sha256") or "").strip()
                if sha256 and not SHA256_PATTERN.fullmatch(sha256):
                    raise ValueError(f"row {row_number}: invalid source_row_sha256")
                amount = _price(str(row.get("price") or ""))
                currency_input = str(row.get("currency") or "").strip().upper()
                currency = currency_input or ("JPY" if amount is not None else None)
                observed_at = _observed_at(str(row.get("observed_at") or ""))
                matching_offers = list(
                    session.scalars(
                        select(StoreOffer).where(
                            StoreOffer.ebook_item_id == item.id,
                            StoreOffer.store_name == store_name,
                        )
                    ).all()
                )
                if len(matching_offers) > 1:
                    raise ValueError(
                        f"row {row_number}: multiple existing offers "
                        f"for ebook_item_id={item.id}, store_name={store_name}"
                    )
                offer = matching_offers[0] if matching_offers else None
                created = offer is None
                if offer is None:
                    offer = StoreOffer(
                        ebook_item_id=item.id,
                        store_name=store_name,
                        store_item_id=store_item_id,
                    )
                    session.add(offer)
                desired = {
                    "store_item_id": store_item_id,
                    "price_amount": amount if amount is not None else offer.price_amount,
                    "price_yen": (
                        int(amount)
                        if amount is not None
                        and currency == "JPY"
                        and amount == amount.to_integral_value()
                        else offer.price_yen
                    ),
                    "currency": currency or offer.currency,
                    "product_url": str(row.get("item_url") or "").strip() or offer.product_url,
                    "affiliate_url": str(row.get("affiliate_url") or "").strip() or offer.affiliate_url,
                    "verified_at": observed_at or offer.verified_at,
                    "last_checked_at": observed_at or offer.last_checked_at,
                    "verification_method": "BACKFILL_CSV",
                    "source_row_sha256": sha256 or offer.source_row_sha256,
                }
                changed = created or any(
                    getattr(offer, field_name) != value
                    for field_name, value in desired.items()
                )
                if changed:
                    for field_name, value in desired.items():
                        setattr(offer, field_name, value)
                    summary.created += int(created)
                    summary.updated += int(not created)
                else:
                    summary.unchanged += 1
                summary.processed += 1
        if execute:
            session.commit()
            summary.database_write_performed = bool(summary.created or summary.updated)
        else:
            session.rollback()
    except Exception:
        summary.failed += 1
        session.rollback()
        raise
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.csv.is_file():
        raise FileNotFoundError(args.csv)
    with SessionLocal() as session:
        summary = run_backfill(session, args.csv, execute=args.execute)
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
