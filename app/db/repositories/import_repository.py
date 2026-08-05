from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EbookSeriesClassificationRule,
    StoreOffer,
    build_series_classification_identity,
)
from app.db.repositories.ebook_repository import EbookRepository


@dataclass(frozen=True)
class ImportResult:
    ebook_item_id: str
    created: bool
    updated: bool
    unchanged: bool
    offer_created: bool
    offer_updated: bool
    offer_unchanged: bool


class ImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.ebooks = EbookRepository(session)

    @staticmethod
    def parse_date(value: str | None) -> date | None:
        if not value:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        for format_string in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(
                    normalized,
                    format_string,
                ).date()
            except ValueError:
                continue

        raise ValueError(f"Unsupported release_date format: {value!r}")

    @staticmethod
    def parse_int(value: str | None) -> int | None:
        if value is None:
            return None

        normalized = value.strip().replace(",", "")
        if not normalized:
            return None

        parsed = int(normalized)
        if parsed < 0:
            raise ValueError("price must be non-negative")
        return parsed

    @staticmethod
    def parse_decimal(value: str | None) -> Decimal | None:
        if value is None:
            return None

        normalized = value.strip().replace("%", "")
        if not normalized:
            return None

        try:
            parsed = Decimal(normalized)
            if not parsed.is_finite():
                raise ValueError(f"Unsupported decimal value: {value!r}")
            return parsed
        except InvalidOperation as exc:
            raise ValueError(
                f"Unsupported decimal value: {value!r}"
            ) from exc

    @staticmethod
    def parse_datetime(value: str | None) -> datetime | None:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        try:
            parsed = datetime.fromisoformat(
                normalized.replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported verified_at format: {value!r}"
            ) from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("verified_at must include a timezone")
        return parsed

    @staticmethod
    def parse_nullable_bool(value: str | None) -> bool | None:
        normalized = str(value or "").strip().casefold()
        if not normalized:
            return None
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"Unsupported classification boolean: {value!r}")

    def find_offer(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        store_item_id: str,
    ) -> StoreOffer | None:
        statement = select(StoreOffer).where(
            StoreOffer.ebook_item_id == ebook_item_id,
            StoreOffer.store_name == store_name,
            StoreOffer.store_item_id == store_item_id,
        )
        return self.session.scalar(statement)

    def import_row(self, row: dict[str, str]) -> ImportResult:
        def first_nonempty(*names: str) -> str:
            for name in names:
                value = str(row.get(name) or "").strip()
                if value:
                    return value
            return ""

        def any_column(*names: str) -> bool:
            return any(name in row for name in names)

        def normalize_metadata_space(value: str | None) -> str:
            return re.sub(
                r"\s+", " ", html.unescape(str(value or "")).strip()
            )

        def normalize_authors(value: str | None) -> str | None:
            parts: list[str] = []
            seen: set[str] = set()
            for raw_part in str(value or "").split("|"):
                part = normalize_metadata_space(raw_part)
                if part and part not in seen:
                    parts.append(part)
                    seen.add(part)
            return "|".join(parts) or None

        source_name = (
            row.get("source_name")
            or row.get("source")
            or "csv_import"
        ).strip()

        source_item_id = (
            row.get("source_item_id")
            or row.get("item_id")
            or row.get("store_item_id")
            or row.get("item_url")
            or row.get("product_url")
            or ""
        ).strip()

        title = (row.get("title") or "").strip()

        if not source_item_id:
            raise ValueError("source_item_id or equivalent field is required")

        if not title:
            raise ValueError("title is required")

        isbn = first_nonempty("isbn", "isbn13") or None
        release_date = self.parse_date(row.get("release_date"))

        item = self.ebooks.find_by_source_identity(
            source_name=source_name,
            source_item_id=source_item_id,
        )

        created = item is None
        updated = False
        unchanged = False

        wordpress_status_text = (
            row.get("wordpress_status") or ""
        ).strip().lower()
        wordpress_status_by_input = {
            "": None,
            "draft": "DRAFT",
            "not_created": "NOT_CREATED",
        }
        if wordpress_status_text not in wordpress_status_by_input:
            raise ValueError(
                "wordpress_status must be draft or not_created"
            )
        requested_wordpress_status = wordpress_status_by_input[
            wordpress_status_text
        ]

        normalized_title = (
            row.get("normalized_title") or title
        ).strip()
        volume_label = first_nonempty(
            "volume_label", "volume_number", "sub_title"
        ) or None
        author_name = normalize_authors(first_nonempty(
            "authors", "author", "author_name"
        ))
        publisher_name = first_nonempty(
            "publisher", "publisher_name"
        )
        publisher_name = normalize_metadata_space(publisher_name) or None
        series_name = first_nonempty("series_name", "series") or None
        requested_item_type = (
            row.get("item_type") or "unknown"
        ).strip()
        explicit_classification = any(
            str(row.get(field_name) or "").strip()
            for field_name in ("is_single_episode", "is_split_edition")
        )
        explicit_single_episode = self.parse_nullable_bool(
            row.get("is_single_episode")
        )
        explicit_split_edition = self.parse_nullable_bool(
            row.get("is_split_edition")
        )
        explicit_classification_source = str(
            row.get("classification_source") or ""
        ).strip()
        if explicit_classification_source not in {
            "",
            "manual",
            "series_rule",
        }:
            raise ValueError(
                "classification_source must be manual or series_rule"
            )

        if item is None:
            item = self.ebooks.create(
                source_name=source_name,
                source_item_id=source_item_id,
                isbn=isbn,
                title=title,
                normalized_title=normalized_title,
                volume_label=volume_label,
                author_name=author_name,
                publisher_name=publisher_name,
                series_name=series_name,
                release_date=release_date,
                item_type=requested_item_type,
            )
            if requested_wordpress_status is not None:
                item.wordpress_status = requested_wordpress_status
            if explicit_classification:
                item.is_single_episode = explicit_single_episode
                item.is_split_edition = explicit_split_edition
                item.classification_source = (
                    explicit_classification_source or "manual"
                )
            else:
                identity = build_series_classification_identity(
                    title=title,
                    author_name=author_name,
                    publisher_name=publisher_name,
                )
                rule = None
                if identity is not None:
                    rule = self.session.scalar(
                        select(EbookSeriesClassificationRule).where(
                            EbookSeriesClassificationRule.series_key
                            == identity[0],
                            EbookSeriesClassificationRule.active.is_(True),
                        )
                    )
                if rule is not None:
                    item.is_single_episode = rule.is_single_episode
                    item.is_split_edition = rule.is_split_edition
                    item.classification_source = "series_rule"
        else:
            desired_values = {
                "title": title,
                "isbn": isbn or item.isbn,
                "normalized_title": normalized_title or item.normalized_title,
                "volume_label": volume_label or item.volume_label,
                "author_name": author_name or item.author_name,
                "publisher_name": publisher_name or item.publisher_name,
                "series_name": series_name or item.series_name,
                "release_date": release_date or item.release_date,
                "item_type": (
                    row.get("item_type")
                    or item.item_type
                    or "unknown"
                ).strip(),
                "wordpress_status": (
                    requested_wordpress_status
                    or item.wordpress_status
                ),
            }
            updated = any(
                getattr(item, field) != value
                for field, value in desired_values.items()
            )
            unchanged = not updated
            if updated:
                item = self.ebooks.update(
                    item,
                    title=desired_values["title"],
                    isbn=desired_values["isbn"],
                    normalized_title=desired_values["normalized_title"],
                    volume_label=desired_values["volume_label"],
                    author_name=desired_values["author_name"],
                    publisher_name=desired_values["publisher_name"],
                    series_name=desired_values["series_name"],
                    release_date=desired_values["release_date"],
                    item_type=desired_values["item_type"],
                )
                item.wordpress_status = desired_values[
                    "wordpress_status"
                ]

        rakuten_columns_present = any_column(
            "rakuten_kobo_url",
            "rakuten_kobo_price",
            "rakuten_kobo_currency",
            "rakuten_kobo_affiliate_url",
        )
        if not str(row.get("store_name") or "").strip():
            rakuten_columns_present = rakuten_columns_present or any_column(
                "item_price",
                "price",
                "price_amount",
                "currency",
                "currency_code",
                "affiliate_url",
            )
        store_name = (
            "rakuten_kobo"
            if rakuten_columns_present
            else (row.get("store_name") or source_name).strip()
        )

        store_item_id = (
            row.get("store_item_id")
            or source_item_id
        ).strip()

        offer = self.find_offer(
            ebook_item_id=item.id,
            store_name=store_name,
            store_item_id=store_item_id,
        )

        offer_created = offer is None
        offer_updated = False
        offer_unchanged = False

        product_url = first_nonempty(
            "rakuten_kobo_url" if rakuten_columns_present else "product_url",
            "item_url",
            "product_url",
        )
        affiliate_url = first_nonempty(
            "rakuten_kobo_affiliate_url"
            if rakuten_columns_present
            else "affiliate_url",
            "affiliate_url",
        )
        raw_price = first_nonempty(
            "rakuten_kobo_price" if rakuten_columns_present else "price_yen",
            "item_price",
            "price",
            "price_amount",
            "price_yen",
        )
        price_amount = self.parse_decimal(raw_price) if raw_price else None
        if price_amount is not None and price_amount < 0:
            raise ValueError("price must be non-negative")
        currency = first_nonempty(
            "rakuten_kobo_currency" if rakuten_columns_present else "currency",
            "currency",
            "currency_code",
        ).upper() or ("JPY" if price_amount is not None else "")
        source_row_sha256 = first_nonempty("source_row_sha256")
        verified_at = self.parse_datetime(row.get("verified_at"))
        verification_method = first_nonempty("verification_method")
        price_yen = (
            int(price_amount)
            if price_amount is not None
            and currency == "JPY"
            and price_amount == price_amount.to_integral_value()
            else None
        )
        discount_rate = (
            self.parse_decimal(row.get("discount_rate"))
            if row.get("discount_rate")
            else None
        )
        point_rate = (
            self.parse_decimal(row.get("point_rate"))
            if row.get("point_rate")
            else None
        )

        if offer is None:
            offer = StoreOffer(
                ebook_item_id=item.id,
                store_name=store_name,
                store_item_id=store_item_id,
            )
            self.session.add(offer)
            offer.product_url = product_url or None
            offer.affiliate_url = affiliate_url or None
            offer.price_yen = price_yen
            offer.price_amount = price_amount
            offer.currency = currency or None
            offer.source_row_sha256 = source_row_sha256 or None
            offer.verified_at = verified_at
            offer.verification_method = verification_method or None
            offer.discount_rate = discount_rate
            offer.point_rate = point_rate
            offer.last_checked_at = datetime.now(timezone.utc)
        else:
            desired_offer_values = {
                "product_url": product_url or offer.product_url,
                "affiliate_url": affiliate_url or offer.affiliate_url,
                "price_yen": (
                    price_yen if price_yen is not None else offer.price_yen
                ),
                "price_amount": (
                    price_amount
                    if price_amount is not None
                    else offer.price_amount
                ),
                "currency": currency or offer.currency,
                "source_row_sha256": (
                    source_row_sha256 or offer.source_row_sha256
                ),
                "verified_at": verified_at or offer.verified_at,
                "verification_method": (
                    verification_method or offer.verification_method
                ),
                "discount_rate": (
                    discount_rate
                    if discount_rate is not None
                    else offer.discount_rate
                ),
                "point_rate": (
                    point_rate
                    if point_rate is not None
                    else offer.point_rate
                ),
            }
            offer_updated = any(
                getattr(offer, field) != value
                for field, value in desired_offer_values.items()
            )
            offer_unchanged = not offer_updated
            if offer_updated:
                for field, value in desired_offer_values.items():
                    setattr(offer, field, value)
                offer.last_checked_at = datetime.now(timezone.utc)

        self.session.flush()

        if not created:
            updated = updated or offer_created or offer_updated
            unchanged = not updated and offer_unchanged

        return ImportResult(
            ebook_item_id=item.id,
            created=created,
            updated=updated,
            unchanged=unchanged,
            offer_created=offer_created,
            offer_updated=offer_updated,
            offer_unchanged=offer_unchanged,
        )
