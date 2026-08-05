from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CatalogEditHistory, EbookItem, StoreOffer
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.services.catalog_edit_service import CURRENCY_PATTERN, parse_price
from app.services.store_url_policy import (
    StoreUrlPolicyError,
    normalize_store_url,
)


class ManualStoreOfferError(ValueError):
    pass


@dataclass(frozen=True)
class ManualStoreOfferPreview:
    ebook_item_id: str
    store_name: str
    product_url: str | None
    affiliate_url: str
    price_amount: Decimal | None
    currency: str | None
    availability_status: str
    observed_at: datetime


@dataclass(frozen=True)
class ManualStoreOfferResult:
    code: str
    ebook_item_id: str
    store_name: str
    offer_id: str
    idempotent: bool = False


class ManualStoreOfferService:
    SUPPORTED_STORES = frozenset({"rakuten_kobo"})
    ALLOWED_WORDPRESS_STATUSES = frozenset({"NOT_CREATED", "DRAFT"})
    ALLOWED_AVAILABILITY = frozenset({"FOUND", "FOUND_CONFIRMED"})

    def __init__(self, session: Session) -> None:
        self.session = session
        self.offers = StoreOfferRepository(session)

    @staticmethod
    def _observed_at(value: datetime | None) -> datetime:
        observed = value or datetime.now(timezone.utc)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return observed

    def preview_create(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        product_url: str,
        affiliate_url: str,
        price: str,
        currency: str,
        availability_status: str,
        observed_at: datetime | None,
    ) -> ManualStoreOfferPreview:
        normalized_store = store_name.strip().casefold()
        if normalized_store not in self.SUPPORTED_STORES:
            raise ManualStoreOfferError("STORE_NOT_SUPPORTED")
        item = self.session.scalar(
            select(EbookItem)
            .where(EbookItem.id == ebook_item_id)
            .with_for_update()
        )
        if item is None:
            raise ManualStoreOfferError("ITEM_NOT_FOUND")
        if item.wordpress_status not in self.ALLOWED_WORDPRESS_STATUSES:
            raise ManualStoreOfferError("WORDPRESS_STATUS_BLOCKED")
        if item.is_excluded:
            raise ManualStoreOfferError("ITEM_FROZEN")
        try:
            normalized_product = normalize_store_url(
                product_url,
                store_name=normalized_store,
                purpose="product",
                required=False,
            )
            normalized_affiliate = normalize_store_url(
                affiliate_url,
                store_name=normalized_store,
                purpose="affiliate",
                required=True,
            )
        except StoreUrlPolicyError as exc:
            raise ManualStoreOfferError(str(exc)) from exc
        assert normalized_affiliate is not None
        amount = parse_price(price)
        normalized_currency = currency.strip().upper() or (
            "JPY" if amount is not None else "JPY"
        )
        if not CURRENCY_PATTERN.fullmatch(normalized_currency):
            raise ManualStoreOfferError("CURRENCY_INVALID")
        normalized_availability = availability_status.strip().upper() or "FOUND"
        if normalized_availability not in self.ALLOWED_AVAILABILITY:
            raise ManualStoreOfferError("AVAILABILITY_INVALID")
        return ManualStoreOfferPreview(
            ebook_item_id=item.id,
            store_name=normalized_store,
            product_url=normalized_product,
            affiliate_url=normalized_affiliate,
            price_amount=amount,
            currency=normalized_currency,
            availability_status="FOUND_CONFIRMED",
            observed_at=self._observed_at(observed_at),
        )

    @staticmethod
    def _store_item_id(preview: ManualStoreOfferPreview) -> str:
        identity = preview.product_url or preview.affiliate_url
        return "manual:" + sha256(identity.encode("utf-8")).hexdigest()

    def _same_offer(
        self, offer: StoreOffer, preview: ManualStoreOfferPreview
    ) -> bool:
        return all((
            offer.product_url == preview.product_url,
            offer.affiliate_url == preview.affiliate_url,
            offer.price_amount == preview.price_amount,
            offer.currency == preview.currency,
            offer.availability_status == preview.availability_status,
        ))

    def _add_history(
        self,
        *,
        preview: ManualStoreOfferPreview,
        operator: str,
    ) -> None:
        evidence = {
            "action": "MANUAL_STORE_OFFER_CREATED",
            "store_name": preview.store_name,
            "product_url_present": preview.product_url is not None,
            "affiliate_url_present": True,
            "affiliate_host": urlsplit(preview.affiliate_url).hostname,
            "affiliate_url_sha256": sha256(
                preview.affiliate_url.encode("utf-8")
            ).hexdigest(),
            "price": (
                str(preview.price_amount)
                if preview.price_amount is not None
                else None
            ),
            "source": "MANUAL",
            "validation_result": "VALID",
        }
        self.session.add(CatalogEditHistory(
            ebook_item_id=preview.ebook_item_id,
            field_name=f"{preview.store_name}.offer_created",
            before_value=None,
            after_value=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            change_reason="MANUAL_STORE_OFFER_CREATED",
            changed_by=operator,
        ))
        self.session.flush()

    def create_offer(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        product_url: str,
        affiliate_url: str,
        price: str,
        currency: str,
        availability_status: str,
        observed_at: datetime | None,
        operator: str,
    ) -> ManualStoreOfferResult:
        normalized_operator = operator.strip()
        if not normalized_operator:
            raise ManualStoreOfferError("OPERATOR_REQUIRED")
        preview = self.preview_create(
            ebook_item_id=ebook_item_id,
            store_name=store_name,
            product_url=product_url,
            affiliate_url=affiliate_url,
            price=price,
            currency=currency,
            availability_status=availability_status,
            observed_at=observed_at,
        )
        existing = self.offers.find_for_store(
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
        )
        if existing is not None:
            if self._same_offer(existing, preview):
                return ManualStoreOfferResult(
                    code="MANUAL_STORE_OFFER_CREATED",
                    ebook_item_id=ebook_item_id,
                    store_name=preview.store_name,
                    offer_id=existing.id,
                    idempotent=True,
                )
            raise ManualStoreOfferError("STORE_OFFER_ALREADY_EXISTS")
        price_yen = (
            int(preview.price_amount)
            if preview.price_amount is not None
            and preview.currency == "JPY"
            and preview.price_amount == preview.price_amount.to_integral_value()
            else None
        )
        offer = StoreOffer(
            ebook_item_id=preview.ebook_item_id,
            store_name=preview.store_name,
            store_item_id=self._store_item_id(preview),
            product_url=preview.product_url,
            affiliate_url=preview.affiliate_url,
            price_amount=preview.price_amount,
            price_yen=price_yen,
            currency=preview.currency,
            availability_status=preview.availability_status,
            verified_at=preview.observed_at,
            verification_method="MANUAL_WEB_EDIT",
            last_checked_at=preview.observed_at,
        )
        self.session.add(offer)
        self.session.flush()
        self._add_history(preview=preview, operator=normalized_operator)
        return ManualStoreOfferResult(
            code="MANUAL_STORE_OFFER_CREATED",
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
            offer_id=offer.id,
        )