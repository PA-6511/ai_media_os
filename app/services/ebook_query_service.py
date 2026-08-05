from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import EbookItem, StoreOffer
from app.db.repositories.ebook_query_repository import (
    EbookQueryRepository,
)
from app.services.ebook_affiliate_readiness_service import (
    affiliate_store_registration_state,
    build_ebook_affiliate_readiness,
)


@dataclass(frozen=True)
class EbookSearchFilters:
    keyword: str | None = None
    release_date_from: date | None = None
    release_date_to: date | None = None
    item_type: str | None = None
    store_name: str | None = None
    workflow_status: str | None = None
    review_status: str | None = None
    wordpress_status: str | None = None
    excluded: bool | None = False
    missing_price: bool = False
    missing_affiliate: bool = False
    affiliate_status: str = "all"
    amazon_affiliate_status: str = "all"
    rakuten_kobo_affiliate_status: str = "all"
    dmm_affiliate_status: str = "all"
    limit: int = 100
    offset: int = 0


def serialize_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    return value


def serialize_offer(offer: StoreOffer) -> dict[str, Any]:
    return {
        "id": offer.id,
        "store_name": offer.store_name,
        "store_item_id": offer.store_item_id,
        "product_url": offer.product_url,
        "affiliate_url": offer.affiliate_url,
        "price_yen": offer.price_yen,
        "price_amount": serialize_value(offer.price_amount),
        "currency": offer.currency,
        "availability_status": offer.availability_status,
        "verified_at": serialize_value(offer.verified_at),
        "verification_method": offer.verification_method,
        "source_row_sha256": offer.source_row_sha256,
        "discount_rate": serialize_value(offer.discount_rate),
        "point_rate": serialize_value(offer.point_rate),
        "sale_start_at": serialize_value(offer.sale_start_at),
        "sale_end_at": serialize_value(offer.sale_end_at),
        "last_checked_at": serialize_value(offer.last_checked_at),
    }


def serialize_ebook_item(
    item: EbookItem,
    *,
    affiliate_urls_by_offer_id: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    readiness = build_ebook_affiliate_readiness(
        item.offers,
        affiliate_urls_by_offer_id=affiliate_urls_by_offer_id,
    )
    return {
        "id": item.id,
        "source_name": item.source_name,
        "source_item_id": item.source_item_id,
        "isbn": item.isbn,
        "title": item.title,
        "normalized_title": item.normalized_title,
        "volume_label": item.volume_label,
        "author_name": item.author_name,
        "publisher_name": item.publisher_name,
        "series_name": item.series_name,
        "release_date": serialize_value(item.release_date),
        "item_type": item.item_type,
        "is_single_episode": item.is_single_episode,
        "is_split_edition": item.is_split_edition,
        "classification_source": item.classification_source,
        "is_excluded": item.is_excluded,
        "exclusion_reason": item.exclusion_reason,
        "workflow_status": item.workflow_status,
        "wordpress_status": item.wordpress_status,
        "wordpress_post_id": item.wordpress_post_id,
        "wordpress_updated_at": serialize_value(
            item.wordpress_updated_at
        ),
        "x_status": item.x_status,
        "x_post_id": item.x_post_id,
        "affiliate_status": item.affiliate_status,
        "image_status": item.image_status,
        "review_status": item.review_status,
        "publish_ready": item.publish_ready,
        "last_error": item.last_error,
        "amazon_affiliate_ready": readiness.amazon_affiliate_ready,
        "rakuten_kobo_affiliate_ready": (
            readiness.rakuten_kobo_affiliate_ready
        ),
        "dmm_affiliate_ready": readiness.dmm_affiliate_ready,
        "affiliate_ready_count": readiness.affiliate_ready_count,
        "amazon_affiliate_registration_state": (
            affiliate_store_registration_state(
                item.offers, store_name="amazon"
            )
        ),
        "rakuten_kobo_affiliate_registration_state": (
            affiliate_store_registration_state(
                item.offers, store_name="rakuten_kobo"
            )
        ),
        "dmm_affiliate_registration_state": (
            affiliate_store_registration_state(
                item.offers, store_name="dmm"
            )
        ),
        "last_checked_at": serialize_value(item.last_checked_at),
        "created_at": serialize_value(item.created_at),
        "updated_at": serialize_value(item.updated_at),
        "offers": [
            serialize_offer(offer)
            for offer in sorted(
                item.offers,
                key=lambda offer: offer.store_name,
            )
        ],
    }


class EbookQueryService:
    def __init__(self, session: Session) -> None:
        self.repository = EbookQueryRepository(session)

    def search(
        self,
        filters: EbookSearchFilters,
    ) -> dict[str, Any]:
        items = self.repository.search_items(
            **asdict(filters),
        )

        serialized_items = [
            serialize_ebook_item(item)
            for item in items
        ]

        return {
            "status": "PASS",
            "count": len(serialized_items),
            "filters": {
                key: serialize_value(value)
                for key, value in asdict(filters).items()
            },
            "items": serialized_items,
        }

    def get_by_source_identity(
        self,
        *,
        source_name: str,
        source_item_id: str,
    ) -> dict[str, Any] | None:
        item = self.repository.get_by_source_identity(
            source_name=source_name,
            source_item_id=source_item_id,
        )

        if item is None:
            return None

        return serialize_ebook_item(
            item,
            affiliate_urls_by_offer_id=self._affiliate_urls_by_offer_id(
                [item]
            ),
        )

    def _affiliate_urls_by_offer_id(
        self, items: Any
    ) -> dict[str, list[str]]:
        offer_ids = [offer.id for item in items for offer in item.offers]
        links = self.repository.list_affiliate_links_for_offer_ids(offer_ids)
        urls: dict[str, list[str]] = {}
        for link in links:
            urls.setdefault(link.store_offer_id, []).append(link.affiliate_url)
        return urls
