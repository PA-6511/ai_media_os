from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AffiliateDestinationProfile,
    StoreOfferAffiliateLink,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoreOfferAffiliateLinkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, *, store_offer_id: str, profile_id: str
    ) -> StoreOfferAffiliateLink | None:
        return self.session.scalar(
            select(StoreOfferAffiliateLink).where(
                StoreOfferAffiliateLink.store_offer_id == store_offer_id,
                StoreOfferAffiliateLink.profile_id == profile_id,
            )
        )

    def list_for_offer(
        self, *, store_offer_id: str
    ) -> list[StoreOfferAffiliateLink]:
        return list(
            self.session.scalars(
                select(StoreOfferAffiliateLink)
                .where(
                    StoreOfferAffiliateLink.store_offer_id == store_offer_id
                )
                .order_by(StoreOfferAffiliateLink.profile_id)
            )
        )

    def upsert(
        self,
        *,
        store_offer_id: str,
        profile_id: str,
        affiliate_url: str,
        generation_method: str,
        source_affiliate_id: str,
    ) -> tuple[StoreOfferAffiliateLink, dict[str, tuple[object, object]]]:
        current = self.get(
            store_offer_id=store_offer_id,
            profile_id=profile_id,
        )
        normalized_url = str(affiliate_url or "").strip()
        normalized_method = str(generation_method or "").strip()
        normalized_source_id = str(source_affiliate_id or "").strip()
        if current is None and not (
            normalized_url and normalized_method and normalized_source_id
        ):
            raise ValueError("affiliate link fields are required")
        created = current is None
        link = current or StoreOfferAffiliateLink(
            store_offer_id=store_offer_id,
            profile_id=profile_id,
        )
        if created:
            self.session.add(link)
        desired = {
            "affiliate_url": normalized_url or link.affiliate_url,
            "generation_method": normalized_method or link.generation_method,
            "source_affiliate_id": (
                normalized_source_id or link.source_affiliate_id
            ),
        }
        changes: dict[str, tuple[object, object]] = {}
        for field_name, after_value in desired.items():
            before_value = getattr(link, field_name)
            if before_value != after_value:
                changes[field_name] = (before_value, after_value)
                setattr(link, field_name, after_value)
        if changes or created:
            now = utc_now()
            link.generated_at = now
            link.updated_at = now
        self.session.flush()
        return link, changes

    def get_for_destination(
        self,
        *,
        store_offer_id: str,
        provider: str,
        destination_type: str,
        destination_key: str,
    ) -> StoreOfferAffiliateLink | None:
        return self.session.scalar(
            select(StoreOfferAffiliateLink)
            .join(
                AffiliateDestinationProfile,
                AffiliateDestinationProfile.id
                == StoreOfferAffiliateLink.profile_id,
            )
            .where(
                StoreOfferAffiliateLink.store_offer_id == store_offer_id,
                AffiliateDestinationProfile.provider
                == str(provider or "").strip().lower(),
                AffiliateDestinationProfile.destination_type
                == str(destination_type or "").strip().lower(),
                AffiliateDestinationProfile.destination_key
                == str(destination_key or "").strip().lower(),
                AffiliateDestinationProfile.is_active.is_(True),
            )
        )

    def get_dmm_wordpress_link(
        self, *, store_offer_id: str
    ) -> StoreOfferAffiliateLink | None:
        return self.get_for_destination(
            store_offer_id=store_offer_id,
            provider="dmm",
            destination_type="wordpress",
            destination_key="blog_main",
        )

    def get_dmm_x_link(
        self, *, store_offer_id: str
    ) -> StoreOfferAffiliateLink | None:
        return self.get_for_destination(
            store_offer_id=store_offer_id,
            provider="dmm",
            destination_type="x",
            destination_key="x_main",
        )
