from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ebook import StoreOffer


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoreOfferRepository:
    """Store-scoped offer lookup and manual upsert operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def find(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        store_item_id: str,
    ) -> StoreOffer | None:
        return self.session.scalar(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id == ebook_item_id,
                StoreOffer.store_name == store_name,
                StoreOffer.store_item_id == store_item_id,
            )
        )

    def find_for_store(
        self, *, ebook_item_id: str, store_name: str
    ) -> StoreOffer | None:
        return self.session.scalar(
            select(StoreOffer)
            .where(
                StoreOffer.ebook_item_id == ebook_item_id,
                StoreOffer.store_name == store_name,
            )
            .order_by(StoreOffer.last_checked_at.desc(), StoreOffer.id)
            .limit(1)
        )

    def find_amazon_offer(self, *, ebook_item_id: str, asin: str) -> StoreOffer | None:
        return self.find(
            ebook_item_id=ebook_item_id,
            store_name="amazon",
            store_item_id=asin.strip().upper(),
        )

    def upsert_manual_offer(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        store_item_id: str,
        product_url: str,
        affiliate_url: str,
        price_amount: Decimal | None = None,
        currency: str | None = None,
        verification_method: str = "MANUAL_WEB_EDIT",
    ) -> tuple[StoreOffer, dict[str, tuple[object, object]]]:
        offer = self.find(
            ebook_item_id=ebook_item_id,
            store_name=store_name,
            store_item_id=store_item_id,
        ) or self.find_for_store(
            ebook_item_id=ebook_item_id,
            store_name=store_name,
        )
        created = offer is None
        if offer is None:
            offer = StoreOffer(
                ebook_item_id=ebook_item_id,
                store_name=store_name,
                store_item_id=store_item_id,
            )
            self.session.add(offer)

        price_yen = (
            int(price_amount)
            if price_amount is not None
            and currency == "JPY"
            and price_amount == price_amount.to_integral_value()
            else None
        )
        desired = {
            "store_item_id": store_item_id or offer.store_item_id,
            "product_url": product_url or offer.product_url,
            "affiliate_url": affiliate_url or offer.affiliate_url,
            "price_amount": (
                price_amount if price_amount is not None else offer.price_amount
            ),
            "price_yen": (
                price_yen if price_amount is not None else offer.price_yen
            ),
            "currency": currency or offer.currency,
            "availability_status": "FOUND_CONFIRMED",
            "verification_method": (
                verification_method or offer.verification_method
            ),
        }
        changes: dict[str, tuple[object, object]] = {}
        for field_name, after_value in desired.items():
            before_value = getattr(offer, field_name)
            if before_value != after_value:
                changes[field_name] = (before_value, after_value)
                setattr(offer, field_name, after_value)

        if changes or created:
            checked_at = utc_now()
            offer.verified_at = checked_at
            offer.last_checked_at = checked_at
        self.session.flush()
        return offer, changes

    def save_amazon_offer(
        self,
        *,
        ebook_item_id: str,
        asin: str,
        product_url: str,
        affiliate_url: str,
    ) -> StoreOffer:
        offer, _ = self.upsert_manual_offer(
            ebook_item_id=ebook_item_id,
            store_name="amazon",
            store_item_id=asin.strip().upper(),
            product_url=product_url,
            affiliate_url=affiliate_url,
        )
        return offer

    def delete_amazon_offer(self, *, ebook_item_id: str, asin: str) -> bool:
        offer = self.find_amazon_offer(ebook_item_id=ebook_item_id, asin=asin)
        if offer is None:
            return False
        self.session.delete(offer)
        self.session.flush()
        return True
