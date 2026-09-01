from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.db.models import EbookItem
from app.db.repositories.store_offer_affiliate_link_repository import (
    StoreOfferAffiliateLinkRepository,
)
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.services.dmm_affiliate_html_parser import (
    DmmAffiliateHtmlParseError,
    parse_dmm_product_url,
)
from app.services.dmm_destination_affiliate_link_service import (
    DmmDestinationAffiliateLinkService,
)
from app.services.dmm_search_discovery_service import DmmSearchDiscoveryService


class DmmInitialDiscoveryError(ValueError):
    """Fail-closed DMM initial discovery error."""


@dataclass(frozen=True)
class DmmInitialDiscoveryResult:
    status: str
    reason_code: str | None
    changed: bool
    ebook_item_id: str
    store_offer_id: str | None = None
    store_item_id: str | None = None
    product_url: str | None = None
    affiliate_url: str | None = None
    affiliate_link_count: int = 0
    matched_title: str | None = None
    match_score: float | None = None


def _text(value: Any) -> str:
    return str(
        getattr(value, "value", value)
        or ""
    ).strip()


def build_dmm_search_url(title: str) -> str:
    normalized = _text(title)

    if not normalized:
        raise DmmInitialDiscoveryError(
            "TITLE_REQUIRED"
        )

    if len(normalized) > 1000:
        raise DmmInitialDiscoveryError(
            "TITLE_TOO_LONG"
        )

    return (
        "https://book.dmm.com/search/?"
        + urlencode(
            {
                "searchstr": normalized,
            }
        )
    )


class DmmInitialDiscoveryService:
    VERIFICATION_METHOD = "DMM_SEARCH_DISCOVERY"
    AFFILIATE_GENERATION_METHOD = "DMM_DESTINATION_PROFILE"
    LEGACY_DESTINATION_KEY = "blog_main"

    def __init__(
        self,
        session: Session,
        *,
        search_service: DmmSearchDiscoveryService | None = None,
        affiliate_service: DmmDestinationAffiliateLinkService | None = None,
    ) -> None:
        self.session = session

        self.search_service = (
            search_service
            or DmmSearchDiscoveryService()
        )

        self.affiliate_service = (
            affiliate_service
            or DmmDestinationAffiliateLinkService(
                session
            )
        )

    def run(
        self,
        ebook_item_id: str,
    ) -> DmmInitialDiscoveryResult:
        item = self.session.get(
            EbookItem,
            ebook_item_id,
        )

        if item is None:
            return DmmInitialDiscoveryResult(
                status="INCOMPLETE",
                reason_code="ITEM_NOT_FOUND",
                changed=False,
                ebook_item_id=ebook_item_id,
            )

        item_id = str(item.id)

        if _text(item.source_name) not in {
            "new_release_multistore",
            "amazon_asin_fast",
        }:
            return DmmInitialDiscoveryResult(
                status="INCOMPLETE",
                reason_code="SOURCE_NOT_ELIGIBLE",
                changed=False,
                ebook_item_id=item_id,
            )

        if bool(item.is_excluded):
            return DmmInitialDiscoveryResult(
                status="INCOMPLETE",
                reason_code="ITEM_EXCLUDED",
                changed=False,
                ebook_item_id=item_id,
            )

        offer_repository = StoreOfferRepository(
            self.session
        )

        current_offer = (
            offer_repository.find_for_store(
                ebook_item_id=item.id,
                store_name="dmm",
            )
        )

        if current_offer is not None:
            return DmmInitialDiscoveryResult(
                status="NOOP",
                reason_code="DMM_OFFER_ALREADY_EXISTS",
                changed=False,
                ebook_item_id=item_id,
                store_offer_id=str(
                    current_offer.id
                ),
                store_item_id=_text(
                    current_offer.store_item_id
                ),
                product_url=_text(
                    current_offer.product_url
                ),
                affiliate_url=_text(
                    current_offer.affiliate_url
                ),
            )

        search_url = build_dmm_search_url(
            _text(item.title)
        )

        match = self.search_service.fetch_and_match(
            search_url=search_url,
            item_title=_text(item.title),
            volume_label=(
                _text(item.volume_label)
                or None
            ),
        )

        if match is None:
            return DmmInitialDiscoveryResult(
                status="INCOMPLETE",
                reason_code="DMM_PRODUCT_NOT_FOUND",
                changed=False,
                ebook_item_id=item_id,
            )

        try:
            parsed = parse_dmm_product_url(
                match.product_url
            )
        except DmmAffiliateHtmlParseError as exc:
            raise DmmInitialDiscoveryError(
                "DISCOVERED_PRODUCT_URL_INVALID"
            ) from exc

        generated = (
            self.affiliate_service
            .generate_for_active_profiles(
                product_url=parsed.product_url
            )
        )

        blog_links = [
            link
            for link in generated
            if (
                _text(link.destination_key)
                == self.LEGACY_DESTINATION_KEY
                and bool(
                    _text(
                        link.affiliate_url
                    )
                )
            )
        ]

        if len(blog_links) != 1:
            raise DmmInitialDiscoveryError(
                "BLOG_MAIN_AFFILIATE_REQUIRED"
            )

        blog_link = blog_links[0]

        # Re-check after network work.
        # Never replace an offer created concurrently.
        current_offer = (
            offer_repository.find_for_store(
                ebook_item_id=item.id,
                store_name="dmm",
            )
        )

        if current_offer is not None:
            return DmmInitialDiscoveryResult(
                status="NOOP",
                reason_code="DMM_OFFER_FILLED_CONCURRENTLY",
                changed=False,
                ebook_item_id=item_id,
                store_offer_id=str(
                    current_offer.id
                ),
            )

        offer, _ = (
            offer_repository.upsert_manual_offer(
                ebook_item_id=item.id,
                store_name="dmm",
                store_item_id=parsed.product_id,
                product_url=parsed.product_url,
                affiliate_url=blog_link.affiliate_url,
                price_amount=None,
                currency=None,
                verification_method=self.VERIFICATION_METHOD,
            )
        )

        link_repository = (
            StoreOfferAffiliateLinkRepository(
                self.session
            )
        )

        persisted_links = 0

        for link in generated:
            if not (
                _text(link.profile_id)
                and _text(link.affiliate_url)
                and _text(link.affiliate_id)
            ):
                continue

            link_repository.upsert(
                store_offer_id=offer.id,
                profile_id=link.profile_id,
                affiliate_url=link.affiliate_url,
                generation_method=self.AFFILIATE_GENERATION_METHOD,
                source_affiliate_id=link.affiliate_id,
            )

            persisted_links += 1

        if persisted_links < 1:
            raise DmmInitialDiscoveryError(
                "AFFILIATE_LINK_PERSISTENCE_EMPTY"
            )

        return DmmInitialDiscoveryResult(
            status="READY",
            reason_code=None,
            changed=True,
            ebook_item_id=item_id,
            store_offer_id=str(offer.id),
            store_item_id=parsed.product_id,
            product_url=parsed.product_url,
            affiliate_url=blog_link.affiliate_url,
            affiliate_link_count=persisted_links,
            matched_title=_text(
                match.product_title
            ),
            match_score=float(
                match.score
            ),
        )
