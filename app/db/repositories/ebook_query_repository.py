from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import EbookItem, StoreOffer, StoreOfferAffiliateLink
from app.services.store_url_policy import STORE_AFFILIATE_HOSTS


AFFILIATE_STORES = ("amazon", "rakuten_kobo", "dmm")


class EbookQueryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_items(
        self,
        *,
        keyword: str | None = None,
        release_date_from: date | None = None,
        release_date_to: date | None = None,
        item_type: str | None = None,
        store_name: str | None = None,
        workflow_status: str | None = None,
        review_status: str | None = None,
        wordpress_status: str | None = None,
        excluded: bool | None = False,
        missing_price: bool = False,
        missing_affiliate: bool = False,
        affiliate_status: str = "all",
        amazon_affiliate_status: str = "all",
        rakuten_kobo_affiliate_status: str = "all",
        dmm_affiliate_status: str = "all",
        item_ids: Sequence[str] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[EbookItem]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")

        if offset < 0:
            raise ValueError("offset must be zero or greater")

        statement: Select[tuple[EbookItem]] = select(EbookItem).options(
            selectinload(EbookItem.offers)
        )
        statement = self._apply_search_filters(
            statement,
            keyword=keyword,
            release_date_from=release_date_from,
            release_date_to=release_date_to,
            item_type=item_type,
            store_name=store_name,
            workflow_status=workflow_status,
            review_status=review_status,
            wordpress_status=wordpress_status,
            excluded=excluded,
            missing_price=missing_price,
            missing_affiliate=missing_affiliate,
            affiliate_status=affiliate_status,
            amazon_affiliate_status=amazon_affiliate_status,
            rakuten_kobo_affiliate_status=rakuten_kobo_affiliate_status,
            dmm_affiliate_status=dmm_affiliate_status,
            item_ids=item_ids,
        )
        if store_name:
            statement = statement.distinct()
        statement = (
            statement.order_by(
                EbookItem.release_date.asc(),
                EbookItem.title.asc(),
            )
            .limit(limit)
            .offset(offset)
        )

        return self.session.scalars(statement).all()

    def count_items(
        self,
        *,
        keyword: str | None = None,
        release_date_from: date | None = None,
        release_date_to: date | None = None,
        item_type: str | None = None,
        store_name: str | None = None,
        workflow_status: str | None = None,
        review_status: str | None = None,
        wordpress_status: str | None = None,
        excluded: bool | None = False,
        missing_price: bool = False,
        missing_affiliate: bool = False,
        affiliate_status: str = "all",
        amazon_affiliate_status: str = "all",
        rakuten_kobo_affiliate_status: str = "all",
        dmm_affiliate_status: str = "all",
        item_ids: Sequence[str] | None = None,
    ) -> int:
        statement = select(func.count(func.distinct(EbookItem.id)))
        statement = self._apply_search_filters(
            statement,
            keyword=keyword,
            release_date_from=release_date_from,
            release_date_to=release_date_to,
            item_type=item_type,
            store_name=store_name,
            workflow_status=workflow_status,
            review_status=review_status,
            wordpress_status=wordpress_status,
            excluded=excluded,
            missing_price=missing_price,
            missing_affiliate=missing_affiliate,
            affiliate_status=affiliate_status,
            amazon_affiliate_status=amazon_affiliate_status,
            rakuten_kobo_affiliate_status=rakuten_kobo_affiliate_status,
            dmm_affiliate_status=dmm_affiliate_status,
            item_ids=item_ids,
        )
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _apply_search_filters(
        statement: Select[Any],
        *,
        keyword: str | None,
        release_date_from: date | None,
        release_date_to: date | None,
        item_type: str | None,
        store_name: str | None,
        workflow_status: str | None,
        review_status: str | None,
        wordpress_status: str | None,
        excluded: bool | None,
        missing_price: bool,
        missing_affiliate: bool,
        affiliate_status: str,
        amazon_affiliate_status: str,
        rakuten_kobo_affiliate_status: str,
        dmm_affiliate_status: str,
        item_ids: Sequence[str] | None,
    ) -> Select[Any]:
        if keyword:
            normalized_keyword = keyword.strip()

            if normalized_keyword:
                pattern = f"%{normalized_keyword}%"
                statement = statement.where(
                    or_(
                        EbookItem.title.ilike(pattern),
                        EbookItem.normalized_title.ilike(pattern),
                        EbookItem.author_name.ilike(pattern),
                        EbookItem.publisher_name.ilike(pattern),
                        EbookItem.isbn.ilike(pattern),
                    )
                )

        if item_ids is not None:
            statement = statement.where(EbookItem.id.in_(tuple(item_ids)))

        if release_date_from is not None:
            statement = statement.where(
                EbookItem.release_date >= release_date_from
            )

        if release_date_to is not None:
            statement = statement.where(
                EbookItem.release_date <= release_date_to
            )

        if item_type:
            item_type_value = item_type.strip()
            if item_type_value == "normal":
                statement = statement.where(
                    EbookItem.is_single_episode.is_(False),
                    EbookItem.is_split_edition.is_(False),
                )
            elif item_type_value == "single_episode":
                statement = statement.where(
                    EbookItem.is_single_episode.is_(True)
                )
            elif item_type_value == "split_edition":
                statement = statement.where(
                    EbookItem.is_split_edition.is_(True)
                )
            elif item_type_value == "single_or_split":
                statement = statement.where(
                    or_(
                        EbookItem.is_single_episode.is_(True),
                        EbookItem.is_split_edition.is_(True),
                    )
                )
            elif item_type_value == "unclassified":
                statement = statement.where(
                    EbookItem.is_single_episode.is_(None),
                    EbookItem.is_split_edition.is_(None),
                )
            else:
                statement = statement.where(
                    EbookItem.item_type == item_type_value
                )

        if excluded is not None:
            statement = statement.where(
                EbookItem.is_excluded == excluded
            )

        if workflow_status:
            statement = statement.where(
                EbookItem.workflow_status == workflow_status
            )
        if review_status:
            statement = statement.where(
                EbookItem.review_status == review_status
            )
        if wordpress_status:
            statement = statement.where(
                EbookItem.wordpress_status == wordpress_status
            )

        if store_name:
            statement = (
                statement
                .join(EbookItem.offers)
                .where(StoreOffer.store_name == store_name.strip())
            )

        if missing_price:
            statement = statement.where(
                ~EbookItem.offers.any(
                    or_(
                        StoreOffer.price_amount.is_not(None),
                        StoreOffer.price_yen.is_not(None),
                    )
                )
            )

        if missing_affiliate:
            statement = statement.where(
                ~EbookItem.offers.any(
                    and_(
                        StoreOffer.affiliate_url.is_not(None),
                        func.trim(StoreOffer.affiliate_url) != "",
                    )
                )
            )

        registered = {
            store_name: EbookQueryRepository._registered_affiliate_exists(
                store_name
            )
            for store_name in AFFILIATE_STORES
        }
        if affiliate_status == "all_unregistered":
            statement = statement.where(~or_(*registered.values()))
        elif affiliate_status == "partially_registered":
            statement = statement.where(
                or_(*registered.values()),
                ~and_(*registered.values()),
            )
        elif affiliate_status == "all_registered":
            statement = statement.where(and_(*registered.values()))

        store_filters = {
            "amazon": amazon_affiliate_status,
            "rakuten_kobo": rakuten_kobo_affiliate_status,
            "dmm": dmm_affiliate_status,
        }
        for store_name, status in store_filters.items():
            if status == "registered":
                statement = statement.where(registered[store_name])
            elif status == "unregistered":
                statement = statement.where(~registered[store_name])

        return statement

    def list_items_by_ids(
        self, ebook_item_ids: Sequence[str]
    ) -> Sequence[EbookItem]:
        if not ebook_item_ids:
            return ()
        statement = (
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.id.in_(tuple(ebook_item_ids)))
        )
        return self.session.scalars(statement).all()

    @staticmethod
    def _registered_affiliate_exists(store_name: str):
        normalized_url = func.lower(func.trim(StoreOffer.affiliate_url))
        allowed_urls = []
        for host in STORE_AFFILIATE_HOSTS[store_name]:
            prefix = f"https://{host}"
            allowed_urls.extend(
                (
                    normalized_url == prefix,
                    normalized_url.like(f"{prefix}/%"),
                    normalized_url.like(f"{prefix}?%"),
                    normalized_url.like(f"{prefix}#%"),
                )
            )
        return EbookItem.offers.any(
            and_(
                StoreOffer.store_name == store_name,
                StoreOffer.affiliate_url.is_not(None),
                func.trim(StoreOffer.affiliate_url) != "",
                or_(*allowed_urls),
            )
        )

    def get_by_id(self, ebook_item_id: str) -> EbookItem | None:
        statement = (
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.id == ebook_item_id)
        )
        return self.session.scalar(statement)

    def get_by_source_identity(
        self,
        *,
        source_name: str,
        source_item_id: str,
    ) -> EbookItem | None:
        statement = (
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(
                EbookItem.source_name == source_name,
                EbookItem.source_item_id == source_item_id,
            )
        )
        return self.session.scalar(statement)

    def list_affiliate_links_for_offer_ids(
        self, store_offer_ids: Sequence[str]
    ) -> Sequence[StoreOfferAffiliateLink]:
        normalized_ids = tuple(
            str(offer_id).strip()
            for offer_id in store_offer_ids
            if str(offer_id).strip()
        )
        if not normalized_ids:
            return ()
        statement = (
            select(StoreOfferAffiliateLink)
            .where(
                StoreOfferAffiliateLink.store_offer_id.in_(normalized_ids)
            )
            .order_by(
                StoreOfferAffiliateLink.store_offer_id,
                StoreOfferAffiliateLink.id,
            )
        )
        return self.session.scalars(statement).all()
