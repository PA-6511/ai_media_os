from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.ebook_query_repository import EbookQueryRepository
from app.services.ebook_query_service import (
    EbookQueryService,
    EbookSearchFilters,
)
from app.services.ebook_bulk_selection_service import (
    build_ebook_bulk_capabilities,
)


@dataclass(frozen=True)
class EbookDatabaseQuery:
    keyword: str = ""
    release_date_from: str = ""
    release_date_to: str = ""
    item_type: str = ""
    store_name: str = ""
    workflow_status: str = ""
    review_status: str = ""
    wordpress_status: str = ""
    include_excluded: bool = False
    excluded_only: bool = False
    missing_price: bool = False
    missing_affiliate: bool = False
    affiliate_status: str = "all"
    amazon_affiliate_status: str = "all"
    rakuten_kobo_affiliate_status: str = "all"
    dmm_affiliate_status: str = "all"
    limit: int = 200
    offset: int = 0


def parse_optional_date(value: str):
    normalized = value.strip()

    if not normalized:
        return None

    try:
        return datetime.strptime(
            normalized,
            "%Y-%m-%d",
        ).date()
    except ValueError as exc:
        raise ValueError(
            f"日付はYYYY-MM-DD形式で入力してください: {value}"
        ) from exc


class EbookDatabaseViewModel:
    def __init__(self, session: Session) -> None:
        self.service = EbookQueryService(session)
        self.repository = EbookQueryRepository(session)

    @staticmethod
    def filters_for_query(query: EbookDatabaseQuery) -> EbookSearchFilters:
        return EbookSearchFilters(
            keyword=query.keyword.strip() or None,
            release_date_from=parse_optional_date(
                query.release_date_from
            ),
            release_date_to=parse_optional_date(
                query.release_date_to
            ),
            item_type=query.item_type.strip() or None,
            store_name=query.store_name.strip() or None,
            workflow_status=query.workflow_status.strip() or None,
            review_status=query.review_status.strip() or None,
            wordpress_status=query.wordpress_status.strip() or None,
            excluded=(
                True
                if query.excluded_only
                else None
                if query.include_excluded
                else False
            ),
            missing_price=query.missing_price,
            missing_affiliate=query.missing_affiliate,
            affiliate_status=query.affiliate_status,
            amazon_affiliate_status=query.amazon_affiliate_status,
            rakuten_kobo_affiliate_status=(
                query.rakuten_kobo_affiliate_status
            ),
            dmm_affiliate_status=query.dmm_affiliate_status,
            limit=query.limit,
            offset=query.offset,
        )

    _filters = filters_for_query

    def search(
        self,
        query: EbookDatabaseQuery,
    ) -> list[dict[str, Any]]:
        result = self.service.search(self.filters_for_query(query))

        return [
            self._flatten_item(item)
            for item in result["items"]
        ]

    def count(self, query: EbookDatabaseQuery) -> int:
        filters = self.filters_for_query(query)
        return self.repository.count_items(
            keyword=filters.keyword,
            release_date_from=filters.release_date_from,
            release_date_to=filters.release_date_to,
            item_type=filters.item_type,
            store_name=filters.store_name,
            workflow_status=filters.workflow_status,
            review_status=filters.review_status,
            wordpress_status=filters.wordpress_status,
            excluded=filters.excluded,
            missing_price=filters.missing_price,
            missing_affiliate=filters.missing_affiliate,
            affiliate_status=filters.affiliate_status,
            amazon_affiliate_status=filters.amazon_affiliate_status,
            rakuten_kobo_affiliate_status=(
                filters.rakuten_kobo_affiliate_status
            ),
            dmm_affiliate_status=filters.dmm_affiliate_status,
        )

    @staticmethod
    def _flatten_item(
        item: dict[str, Any],
    ) -> dict[str, Any]:
        offers = item.get("offers", [])
        bulk_capabilities = build_ebook_bulk_capabilities(item)

        store_names = ", ".join(
            offer["store_name"]
            for offer in offers
        )

        prices = ", ".join(
            (
                f'{offer["store_name"]}:{offer.get("price_amount")}'
                f' {offer.get("currency") or "JPY"}'
                if offer.get("price_amount") is not None
                else f'{offer["store_name"]}:{offer.get("price_yen")}'
            )
            for offer in offers
            if (
                offer.get("price_amount") is not None
                or offer.get("price_yen") is not None
            )
        )

        rakuten_offer = next(
            (
                offer
                for offer in offers
                if offer.get("store_name") == "rakuten_kobo"
            ),
            None,
        )

        amazon_affiliate_ready = bool(
            item.get("amazon_affiliate_ready", False)
        )
        rakuten_kobo_affiliate_ready = bool(
            item.get("rakuten_kobo_affiliate_ready", False)
        )
        dmm_affiliate_ready = bool(
            item.get("dmm_affiliate_ready", False)
        )
        affiliate_ready_count = sum(
            (
                amazon_affiliate_ready,
                rakuten_kobo_affiliate_ready,
                dmm_affiliate_ready,
            )
        )
        affiliate_count = sum(
            1
            for offer in offers
            if str(offer.get("affiliate_url") or "").strip()
        )

        return {
            "id": item["id"],
            "source_item_id": item["source_item_id"],
            "title": item["title"],
            "volume_label": item.get("volume_label") or "",
            "author_name": item.get("author_name") or "",
            "publisher_name": item.get("publisher_name") or "",
            "series_name": item.get("series_name") or "",
            "rakuten_kobo_offer": rakuten_offer,
            "release_date": item.get("release_date") or "",
            "item_type": item.get("item_type") or "",
            "is_single_episode": item.get("is_single_episode"),
            "is_split_edition": item.get("is_split_edition"),
            "classification_source": (
                item.get("classification_source") or ""
            ),
            "store_names": store_names,
            "prices": prices,
            "amazon_affiliate_ready": amazon_affiliate_ready,
            "rakuten_kobo_affiliate_ready": rakuten_kobo_affiliate_ready,
            "dmm_affiliate_ready": dmm_affiliate_ready,
            "amazon_affiliate_registration_state": item.get(
                "amazon_affiliate_registration_state", "unregistered"
            ),
            "rakuten_kobo_affiliate_registration_state": item.get(
                "rakuten_kobo_affiliate_registration_state", "unregistered"
            ),
            "dmm_affiliate_registration_state": item.get(
                "dmm_affiliate_registration_state", "unregistered"
            ),
            "affiliate_ready_count": affiliate_ready_count,
            "affiliate_count": affiliate_count,
            "affiliate_registration_capability": (
                bulk_capabilities.affiliate_registration_capability
            ),
            "wordpress_draft_capability": (
                bulk_capabilities.wordpress_draft_capability
            ),
            "wordpress_schedule_capability": (
                bulk_capabilities.wordpress_schedule_capability
            ),
            "workflow_status": (
                item.get("workflow_status") or "NEW"
            ),
            "wordpress_status": (
                item.get("wordpress_status") or "NOT_CREATED"
            ),
            "wordpress_post_id": (
                item.get("wordpress_post_id") or ""
            ),
            "x_status": (
                item.get("x_status") or "NOT_CREATED"
            ),
            "affiliate_status": (
                item.get("affiliate_status") or "UNCHECKED"
            ),
            "image_status": (
                item.get("image_status") or "UNCHECKED"
            ),
            "review_status": (
                item.get("review_status") or "NOT_REVIEWED"
            ),
            "publish_ready": bool(
                item.get("publish_ready", False)
            ),
            "last_error": item.get("last_error") or "",
            "is_excluded": item.get("is_excluded", False),
        }
