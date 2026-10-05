"""Build the existing Sale Slack approval snapshot shape from a DMM campaign."""

from __future__ import annotations

from datetime import (
    datetime,
    timezone,
)
import math

from sqlalchemy.orm import Session

from app.db.models.sale_roundup import (
    SaleCampaign,
)
from app.services.sale_roundup_service import (
    current_snapshot,
    digest,
)


class DmmSaleApprovalSnapshotError(
    ValueError
):
    pass


def _discount(
    value,
) -> float:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (
                int,
                float,
            ),
        )
        or not math.isfinite(
            float(
                value
            )
        )
    ):
        return 0.0

    return float(
        value
    )


def build_dmm_sale_approval_snapshot(
    session: Session,
    *,
    campaign_id: str,
    now: datetime | None = None,
) -> dict:
    effective_now = (
        now
        or datetime.now(
            timezone.utc
        )
    )

    snapshot = current_snapshot(
        session,
        campaign_id,
        now=effective_now,
    )

    if (
        snapshot.get(
            "campaign_store"
        )
        != "dmm"
    ):
        raise DmmSaleApprovalSnapshotError(
            "NOT_DMM_CAMPAIGN"
        )

    campaign = session.get(
        SaleCampaign,
        campaign_id,
    )

    if campaign is None:
        raise DmmSaleApprovalSnapshotError(
            "CAMPAIGN_NOT_FOUND"
        )

    items = snapshot.get(
        "items"
    )

    if (
        not isinstance(
            items,
            list,
        )
        or not items
    ):
        raise DmmSaleApprovalSnapshotError(
            "NO_VALID_DMM_OFFERS"
        )

    grouped = {}

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        name = str(
            item.get(
                "series_name"
            )
            or item.get(
                "title"
            )
            or "不明"
        ).strip()

        grouped.setdefault(
            name,
            [],
        ).append(
            item
        )

    rows = []

    for series_name in sorted(
        grouped,
        key=str.casefold,
    ):
        group = grouped[
            series_name
        ]

        discounts = [
            _discount(
                item.get(
                    "discount_percent"
                )
            )
            for item in group
        ]

        rows.append({
            "series_name":
                series_name,

            # Existing Slack shape compatibility.
            # DMM does not use Amazon's simple-sale scorer.
            "simple_sale_score":
                0,

            "sale_coverage":
                "DMM_OFFICIAL",

            "sale_volume_count":
                len(
                    group
                ),

            "known_volume_count":
                len(
                    group
                ),

            "max_savings_percentage":
                max(
                    discounts,
                    default=0.0,
                ),
        })

    detected_at = str(
        campaign.source_generated_at
        or campaign.imported_at
        or campaign.starts_at
        or ""
    )

    payload = {
        "campaign_id":
            campaign.id,

        "campaign_store":
            "dmm",

        "title":
            campaign.title,

        "detected_at":
            detected_at,

        "checked_item_count":
            len(
                items
            ),

        "verified_signal_count":
            len(
                items
            ),

        "series_count":
            len(
                rows
            ),

        "series":
            rows,
    }

    return {
        **payload,
        "snapshot_hash":
            digest(
                payload
            ),
    }
