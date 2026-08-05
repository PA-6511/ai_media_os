from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    CatalogEditHistory,
    EbookItem,
    EbookSeriesClassificationRule,
    build_series_classification_identity,
)
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.db.repositories.workflow_state_repository import WorkflowStateRepository


CURRENCY_PATTERN = re.compile(r"^[A-Z0-9]{3,12}$")
ITEM_TYPES = {
    "tankobon",
    "light_novel",
    "general_book",
    "single_chapter",
    "magazine_episode",
    "unknown",
}


class CatalogEditError(ValueError):
    pass


@dataclass(frozen=True)
class CatalogEditResult:
    ebook_item_id: str
    changed_fields: tuple[str, ...]
    unchanged: bool
    series_rule_saved: bool = False
    series_rule_skipped: bool = False


def normalize_authors(value: str) -> str | None:
    normalized = (
        author.replace(" ", "").replace("\u3000", "")
        for author in str(value or "").split("|")
    )
    return "|".join(author for author in normalized if author) or None


def parse_price(value: str) -> Decimal | None:
    normalized = value.strip().replace(",", "")
    if not normalized:
        return None
    try:
        price = Decimal(normalized)
    except InvalidOperation as exc:
        raise CatalogEditError("price must be a non-negative number") from exc
    if not price.is_finite() or price < 0:
        raise CatalogEditError("price must be a non-negative number")
    if price.as_tuple().exponent < -2:
        raise CatalogEditError("price supports at most two decimal places")
    return price


class CatalogEditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save(
        self,
        *,
        ebook_item_id: str,
        title: str | None = None,
        volume_label: str,
        authors: str,
        publisher: str,
        imprint: str | None = None,
        item_type: str | None = None,
        release_date: str | None = None,
        price: str,
        currency: str,
        reason: str,
        changed_by: str = "human:local_gui",
        is_single_episode: bool | None = None,
        is_split_edition: bool | None = None,
        apply_to_future_series: bool = False,
    ) -> CatalogEditResult:
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise CatalogEditError("item_not_found")
        if str(item.wordpress_status or "NOT_CREATED").upper() not in {
            "",
            "NOT_CREATED",
        }:
            raise CatalogEditError("wordpress_already_created")
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise CatalogEditError("change reason is required")
        normalized_currency = currency.strip().upper()
        amount = parse_price(price)
        if amount is not None and not CURRENCY_PATTERN.fullmatch(normalized_currency):
            raise CatalogEditError("currency is required for a price")

        offer = StoreOfferRepository(self.session).find_for_store(
            ebook_item_id=ebook_item_id,
            store_name="rakuten_kobo",
        )
        if offer is None and (amount is not None or normalized_currency):
            raise CatalogEditError("rakuten_kobo_offer_not_found")

        desired = {
            "volume_label": volume_label.strip() or None,
            "author_name": normalize_authors(authors),
            "publisher_name": publisher.strip() or None,
        }
        if title is not None:
            normalized_title = title.strip()
            if not normalized_title:
                raise CatalogEditError("title is required")
            desired["title"] = normalized_title
        if imprint is not None:
            desired["series_name"] = imprint.strip() or None
        if item_type is not None:
            normalized_item_type = item_type.strip()
            if normalized_item_type not in ITEM_TYPES:
                raise CatalogEditError("invalid item_type")
            desired["item_type"] = normalized_item_type
        if release_date is not None:
            try:
                desired["release_date"] = (
                    date.fromisoformat(release_date.strip())
                    if release_date.strip()
                    else None
                )
            except ValueError as exc:
                raise CatalogEditError("invalid release_date") from exc
        classification_supplied = (
            is_single_episode is not None or is_split_edition is not None
        )
        if classification_supplied and (
            is_single_episode is None or is_split_edition is None
        ):
            raise CatalogEditError(
                "both classification flags must be supplied"
            )
        if classification_supplied:
            desired.update(
                {
                    "is_single_episode": bool(is_single_episode),
                    "is_split_edition": bool(is_split_edition),
                    "classification_source": "manual",
                }
            )
        changes: dict[str, tuple[object, object]] = {}
        for field_name, after_value in desired.items():
            before_value = getattr(item, field_name)
            if before_value != after_value:
                changes[field_name] = (before_value, after_value)
                setattr(item, field_name, after_value)

        if offer is not None:
            price_yen = (
                int(amount)
                if amount is not None
                and normalized_currency == "JPY"
                and amount == amount.to_integral_value()
                else None
            )
            for field_name, after_value in (
                ("price_amount", amount),
                ("price_yen", price_yen),
                ("currency", normalized_currency or None),
            ):
                before_value = getattr(offer, field_name)
                if before_value != after_value:
                    history_name = f"rakuten_kobo.{field_name}"
                    changes[history_name] = (before_value, after_value)
                    setattr(offer, field_name, after_value)

        series_rule_saved = False
        series_rule_skipped = False
        if apply_to_future_series and classification_supplied:
            identity = build_series_classification_identity(
                title=item.title,
                author_name=item.author_name,
                publisher_name=item.publisher_name,
            )
            if identity is None:
                series_rule_skipped = True
            else:
                (
                    series_key,
                    normalized_base_title,
                    normalized_author_name,
                    normalized_publisher_name,
                ) = identity
                rule = self.session.scalar(
                    select(EbookSeriesClassificationRule).where(
                        EbookSeriesClassificationRule.series_key == series_key
                    )
                )
                if rule is None:
                    rule = EbookSeriesClassificationRule(
                        series_key=series_key,
                        normalized_base_title=normalized_base_title,
                        normalized_author_name=normalized_author_name,
                        normalized_publisher_name=normalized_publisher_name,
                        is_single_episode=bool(is_single_episode),
                        is_split_edition=bool(is_split_edition),
                        source_ebook_item_id=item.id,
                        active=True,
                    )
                    self.session.add(rule)
                    series_rule_saved = True
                else:
                    rule_values = {
                        "normalized_base_title": normalized_base_title,
                        "normalized_author_name": normalized_author_name,
                        "normalized_publisher_name": normalized_publisher_name,
                        "is_single_episode": bool(is_single_episode),
                        "is_split_edition": bool(is_split_edition),
                        "source_ebook_item_id": item.id,
                        "active": True,
                    }
                    series_rule_saved = any(
                        getattr(rule, field_name) != after_value
                        for field_name, after_value in rule_values.items()
                    )
                    for field_name, after_value in rule_values.items():
                        setattr(rule, field_name, after_value)

        if changes:
            classification_fields = {
                "is_single_episode",
                "is_split_edition",
                "classification_source",
            }
            has_non_classification_change = any(
                field_name not in classification_fields
                for field_name in changes
            )
            if has_non_classification_change:
                before_review_status = item.review_status
                before_workflow_status = item.workflow_status
                WorkflowStateRepository(self.session).reset_for_metadata_review(
                    item,
                    changed_by=changed_by,
                    note="Basic metadata changed; item returned to review entry.",
                )
                if before_review_status != item.review_status:
                    changes["review_status"] = (
                        before_review_status,
                        item.review_status,
                    )
                if before_workflow_status != item.workflow_status:
                    changes["workflow_status"] = (
                        before_workflow_status,
                        item.workflow_status,
                    )
            if has_non_classification_change and item.publish_ready:
                changes["publish_ready"] = (True, False)
                item.publish_ready = False
            for field_name, (before_value, after_value) in changes.items():
                self.session.add(
                    CatalogEditHistory(
                        ebook_item_id=item.id,
                        field_name=field_name,
                        before_value=None if before_value is None else str(before_value),
                        after_value=None if after_value is None else str(after_value),
                        change_reason=normalized_reason,
                        changed_by=changed_by,
                    )
                )
        if changes or series_rule_saved:
            self.session.flush()

        return CatalogEditResult(
            ebook_item_id=item.id,
            changed_fields=tuple(changes),
            unchanged=not changes and not series_rule_saved,
            series_rule_saved=series_rule_saved,
            series_rule_skipped=series_rule_skipped,
        )
