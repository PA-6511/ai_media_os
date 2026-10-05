"""Bounded DMM sale automation up to Slack approval handoff."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.ebook import StoreOffer
from app.db.models.sale_roundup import (
    SaleCampaign,
    SaleOffer,
)
from app.services.dmm_sale_affiliate_persistence_service import (
    persist_dmm_sale_affiliate,
)
from app.services.dmm_sale_offer_bridge_service import (
    stage_dmm_sale_candidate,
)
from app.services.sale_roundup_service import digest


JST = ZoneInfo("Asia/Tokyo")


class DmmSaleAutonomyError(RuntimeError):
    pass


@dataclass(frozen=True)
class DmmSaleAutonomyResult:
    campaign_id: str
    campaign_created: bool

    candidate_count: int
    sale_created_count: int
    sale_reused_count: int

    affiliate_updated_count: int
    affiliate_reused_count: int

    campaign_title: str
    campaign_url: str


def _as_datetime(
    value: object,
) -> datetime | None:
    if value is None:
        return None

    if isinstance(
        value,
        datetime,
    ):
        result = value

    elif isinstance(
        value,
        str,
    ):
        text = value.strip()

        if not text:
            return None

        result = datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00",
            )
        )

    else:
        raise DmmSaleAutonomyError(
            "DATETIME_INVALID"
        )

    if result.tzinfo is None:
        result = result.replace(
            tzinfo=timezone.utc
        )

    return result.astimezone(
        timezone.utc
    )


def campaign_id_for(
    *,
    campaign_url: str,
    sale_end_at: object,
) -> str:
    end = _as_datetime(
        sale_end_at
    )

    if end is None:
        raise DmmSaleAutonomyError(
            "CAMPAIGN_END_UNKNOWN"
        )

    suffix = (
        end.astimezone(
            JST
        )
        .strftime(
            "%Y%m%d"
        )
    )

    identity = hashlib.sha256(
        campaign_url.encode(
            "utf-8"
        )
    ).hexdigest()[:16]

    return (
        "dmm-official-"
        + identity
        + "-"
        + suffix
    )


def _candidate_payload(
    candidate: object,
) -> dict[str, Any]:
    names = (
        "campaign_url",
        "campaign_title",
        "title",
        "series_name",
        "cover_image_url",
        "source_filter_threshold",
        "series_id",
        "product_id",
        "product_url",
        "normal_price_yen",
        "sale_price_yen",
        "discount_percent",
        "sale_start_at",
        "sale_end_at",
        "source_method",
    )

    result = {}

    for name in names:
        value = getattr(
            candidate,
            name,
            None,
        )

        if isinstance(
            value,
            datetime,
        ):
            value = value.isoformat()

        result[name] = value

    return result


def _ensure_campaign(
    session: Session,
    *,
    collection: object,
    now: datetime,
) -> tuple[
    SaleCampaign,
    bool,
]:
    candidates = tuple(
        getattr(
            collection,
            "candidates",
            (),
        )
        or ()
    )

    if not candidates:
        raise DmmSaleAutonomyError(
            "NO_DMM_SALE_CANDIDATES"
        )

    ends = [
        value
        for candidate in candidates
        if (
            value := _as_datetime(
                getattr(
                    candidate,
                    "sale_end_at",
                    None,
                )
            )
        )
        is not None
    ]

    if not ends:
        raise DmmSaleAutonomyError(
            "CAMPAIGN_END_UNKNOWN"
        )

    starts = [
        value
        for candidate in candidates
        if (
            value := _as_datetime(
                getattr(
                    candidate,
                    "sale_start_at",
                    None,
                )
            )
        )
        is not None
    ]

    end = max(
        ends
    )

    start = (
        min(
            starts
        )
        if starts
        else now
    )

    campaign_url = str(
        getattr(
            collection,
            "campaign_url",
            "",
        )
        or ""
    ).strip()

    title = str(
        getattr(
            collection,
            "campaign_title",
            "",
        )
        or ""
    ).strip()

    if (
        not campaign_url
        or not title
    ):
        raise DmmSaleAutonomyError(
            "CAMPAIGN_IDENTITY_INVALID"
        )

    campaign_id = campaign_id_for(
        campaign_url=campaign_url,
        sale_end_at=end,
    )

    payload = {
        "campaign_url":
            campaign_url,
        "campaign_title":
            title,
        "starts_at":
            start.isoformat(),
        "ends_at":
            end.isoformat(),
        "candidates": [
            _candidate_payload(
                candidate
            )
            for candidate
            in candidates
        ],
    }

    snapshot_hash = digest(
        payload
    )

    campaign = session.get(
        SaleCampaign,
        campaign_id,
    )

    created = (
        campaign is None
    )

    if campaign is None:
        campaign = SaleCampaign(
            id=campaign_id,
        )

        session.add(
            campaign
        )

        campaign.title = title
        campaign.starts_at = (
            start.isoformat()
        )

    else:
        if (
            str(
                campaign.title
                or ""
            ).strip()
            != title
        ):
            raise DmmSaleAutonomyError(
                "CAMPAIGN_TITLE_CONFLICT"
            )

    # Re-scan refreshes the authoritative source timestamp.
    campaign.ends_at = (
        end.isoformat()
    )

    campaign.snapshot_hash = (
        snapshot_hash
    )

    campaign.imported_at = (
        now.isoformat()
    )

    campaign.source_generated_at = (
        now.isoformat()
    )

    session.flush()

    return (
        campaign,
        created,
    )


def stage_dmm_campaign(
    session: Session,
    *,
    candidate_service: object,
    campaign_url: str,
    threshold_percent: int,
    max_products: int,
    now: datetime | None = None,
) -> DmmSaleAutonomyResult:
    effective_now = (
        now
        or datetime.now(
            timezone.utc
        )
    )

    if (
        effective_now.tzinfo
        is None
    ):
        effective_now = (
            effective_now.replace(
                tzinfo=timezone.utc
            )
        )

    effective_now = (
        effective_now.astimezone(
            timezone.utc
        )
    )

    if (
        threshold_percent < 1
        or threshold_percent > 100
    ):
        raise DmmSaleAutonomyError(
            "THRESHOLD_INVALID"
        )

    if (
        max_products < 1
        or max_products > 100
    ):
        raise DmmSaleAutonomyError(
            "MAX_PRODUCTS_INVALID"
        )

    collect = getattr(
        candidate_service,
        "collect",
        None,
    )

    if not callable(
        collect
    ):
        raise DmmSaleAutonomyError(
            "CANDIDATE_SERVICE_INVALID"
        )

    collection = collect(
        campaign_url=campaign_url,
        threshold_percent=(
            threshold_percent
        ),
        max_products=max_products,
    )

    candidates = tuple(
        getattr(
            collection,
            "candidates",
            (),
        )
        or ()
    )

    if not candidates:
        return (
            DmmSaleAutonomyResult(
                campaign_id="",
                campaign_created=False,
                candidate_count=0,
                sale_created_count=0,
                sale_reused_count=0,
                affiliate_updated_count=0,
                affiliate_reused_count=0,
                campaign_title=str(
                    getattr(
                        collection,
                        "campaign_title",
                        "",
                    )
                    or ""
                ),
                campaign_url=str(
                    getattr(
                        collection,
                        "campaign_url",
                        campaign_url,
                    )
                    or campaign_url
                ),
            )
        )

    campaign, campaign_created = (
        _ensure_campaign(
            session,
            collection=collection,
            now=effective_now,
        )
    )

    created_count = 0
    reused_count = 0

    affiliate_updated = 0
    affiliate_reused = 0

    for candidate in candidates:
        result = (
            stage_dmm_sale_candidate(
                session,
                campaign_id=campaign.id,
                candidate=candidate,
            )
        )

        session.flush()

        if (
            result.sale_offer_status
            == "CREATED"
        ):
            created_count += 1

        elif (
            result.sale_offer_status
            == "EXISTING_REUSED"
        ):
            reused_count += 1

        else:
            raise DmmSaleAutonomyError(
                "SALE_STAGE_STATUS_INVALID:"
                + str(
                    result.sale_offer_status
                )
            )

        store_offer = session.get(
            StoreOffer,
            result.store_offer_id,
        )

        sale_offer = session.get(
            SaleOffer,
            result.sale_offer_id,
        )

        if (
            store_offer is None
            or sale_offer is None
        ):
            raise DmmSaleAutonomyError(
                "STAGED_OFFER_NOT_FOUND"
            )

        affiliate = (
            persist_dmm_sale_affiliate(
                store_offer=store_offer,
                sale_offer=sale_offer,
            )
        )

        if (
            affiliate.status
            == "UPDATED"
        ):
            affiliate_updated += 1

        elif (
            affiliate.status
            == "EXISTING_REUSED"
        ):
            affiliate_reused += 1

        else:
            raise DmmSaleAutonomyError(
                "AFFILIATE_STATUS_INVALID:"
                + affiliate.status
            )

    session.flush()

    return (
        DmmSaleAutonomyResult(
            campaign_id=campaign.id,
            campaign_created=(
                campaign_created
            ),
            candidate_count=len(
                candidates
            ),
            sale_created_count=(
                created_count
            ),
            sale_reused_count=(
                reused_count
            ),
            affiliate_updated_count=(
                affiliate_updated
            ),
            affiliate_reused_count=(
                affiliate_reused
            ),
            campaign_title=(
                campaign.title
            ),
            campaign_url=str(
                getattr(
                    collection,
                    "campaign_url",
                    campaign_url,
                )
            ),
        )
    )
