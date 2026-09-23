from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    ImageRightsEvidence,
    StoreOffer,
)
from app.integrations.amazon_creators_api_client import (
    AmazonCreatorsApiClient,
)
from app.services.official_cover_automation_service import (
    StoreCoverPolicyService,
)


@dataclass(frozen=True)
class AmazonCoverPersistenceResult:
    ebook_item_id: str
    status: str
    reason_code: str | None = None
    changed: bool = False


def _amazon_cover_url(value: str | None) -> str | None:
    raw = str(value or "").strip()

    if not raw:
        return None

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None

    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname != "m.media-amazon.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        return None

    return raw


def _amazon_destination_url(
    value: str | None,
) -> str | None:
    raw = str(value or "").strip()

    if not raw:
        return None

    try:
        parsed = urlsplit(raw)
    except ValueError:
        return None

    hostname = str(
        parsed.hostname or ""
    ).lower()

    if (
        parsed.scheme.lower() != "https"
        or hostname not in {
            "amazon.co.jp",
            "www.amazon.co.jp",
        }
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        return None

    return raw


class AmazonCreatorsCoverPersistenceService:
    """Persist a verified Amazon Creators cover for an existing Amazon offer."""

    def __init__(
        self,
        session: Session,
        client: AmazonCreatorsApiClient,
        *,
        now=None,
    ) -> None:
        self.session = session
        self.client = client
        self._now = now or (
            lambda: datetime.now(
                timezone.utc
            )
        )

    def persist_item(
        self,
        ebook_item_id: str,
        *,
        execute: bool,
    ) -> AmazonCoverPersistenceResult:
        item_id = str(
            ebook_item_id or ""
        ).strip()

        item = self.session.get(
            EbookItem,
            item_id,
        )

        if item is None:
            return AmazonCoverPersistenceResult(
                item_id,
                "ITEM_NOT_FOUND",
            )

        if (
            str(
                item.cover_status
                or ""
            ).upper()
            == "AUTO_ALLOWED"
            and str(
                item.cover_image_url
                or ""
            ).strip()
        ):
            return AmazonCoverPersistenceResult(
                item.id,
                "NOOP_ALREADY_ALLOWED",
            )

        policy = (
            StoreCoverPolicyService(
                self.session
            ).amazon_state()
        )

        if not policy.current_and_agreed:
            return AmazonCoverPersistenceResult(
                item.id,
                "BLOCKED",
                "AMAZON_COVER_POLICY_NOT_AGREED",
            )

        rights = self.session.scalar(
            select(
                ImageRightsEvidence
            )
            .where(
                ImageRightsEvidence
                .candidate_id
                == item.id
            )
            .order_by(
                ImageRightsEvidence
                .verified_at.desc(),
                ImageRightsEvidence
                .created_at.desc(),
                ImageRightsEvidence
                .id.desc(),
            )
            .limit(1)
        )

        if (
            rights is not None
            and str(
                rights.rights_status
                or ""
            ).upper()
            in {
                "VERIFIED_NOT_ALLOWED",
                "UNRESOLVED",
            }
        ):
            return AmazonCoverPersistenceResult(
                item.id,
                "BLOCKED",
                "RIGHTS_NOT_ALLOWED",
            )

        offers = list(
            self.session.scalars(
                select(
                    StoreOffer
                )
                .where(
                    StoreOffer
                    .ebook_item_id
                    == item.id,
                    func.lower(
                        StoreOffer.store_name
                    )
                    == "amazon",
                )
                .order_by(
                    StoreOffer.id
                )
            )
        )

        if len(offers) != 1:
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_OFFER_NOT_UNIQUE",
            )

        offer = offers[0]

        asin = str(
            offer.store_item_id
            or ""
        ).strip().upper()

        if (
            len(asin) != 10
            or not asin.isalnum()
        ):
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_ASIN_INVALID",
            )

        api_items = self.client.get_items(
            [asin]
        )

        if len(api_items) != 1:
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_ITEM_NOT_UNIQUE",
            )

        api_item = api_items[0]

        if (
            str(
                api_item.asin
                or ""
            ).strip().upper()
            != asin
        ):
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_ASIN_MISMATCH",
            )

        cover_url = _amazon_cover_url(
            api_item.cover_url
        )

        if cover_url is None:
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_COVER_MISSING_OR_INVALID",
            )

        destination_url = (
            _amazon_destination_url(
                offer.affiliate_url
            )
            or _amazon_destination_url(
                offer.product_url
            )
        )

        if destination_url is None:
            return AmazonCoverPersistenceResult(
                item.id,
                "UNAVAILABLE",
                "AMAZON_DESTINATION_INVALID",
            )

        if not execute:
            return AmazonCoverPersistenceResult(
                item.id,
                "VERIFIED_DRY_RUN",
            )

        item.cover_source = (
            "AMAZON_PA_API"
        )
        item.cover_source_item_id = (
            asin
        )
        item.cover_image_url = (
            cover_url
        )
        item.cover_destination_url = (
            destination_url
        )
        item.cover_retrieved_at = (
            self._now()
        )
        item.cover_policy_version = (
            policy.current_version
        )
        item.cover_status = (
            "AUTO_ALLOWED"
        )
        item.image_status = (
            "READY"
        )

        self.session.commit()

        return AmazonCoverPersistenceResult(
            item.id,
            "AUTO_ALLOWED",
            changed=True,
        )
