"""Append a bounded SaleOffer within a caller-owned transaction."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    object_session,
)

from app.db.models.ebook import (
    EbookItem,
    StoreOffer,
)
from app.db.models.sale_roundup import (
    SaleCampaign,
    SaleOffer,
)
from app.services.sale_roundup_service import (
    digest,
)
from app.services.sale_store_policy import (
    SaleStorePolicyError,
    require_canonical_sale_store,
    validate_sale_cover_url,
    validate_sale_product_url,
)


KOBO_CAMPAIGN_ID = (
    "rakuten-kobo-official-discount-341921-20261001"
)

SUPPORTED_BOUNDED_STORES = frozenset({
    "rakuten_kobo",
    "dmm",
})

DMM_STORE_ITEM_ID_RE = re.compile(
    r"^[a-z0-9]{6,64}$"
)


class BoundedSaleOfferError(
    ValueError
):
    """Invalid identity or conflicting SaleOffer."""


@dataclass(frozen=True)
class StagedSaleOfferResult:
    status: str
    sale_offer: SaleOffer


def _instant(
    value: object,
) -> datetime:
    if not isinstance(
        value,
        str,
    ):
        raise BoundedSaleOfferError(
            "SALE_PERIOD_INVALID"
        )

    try:
        instant = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError as exc:
        raise BoundedSaleOfferError(
            "SALE_PERIOD_INVALID"
        ) from exc

    if (
        instant.tzinfo is None
        or instant.utcoffset()
        is None
    ):
        raise BoundedSaleOfferError(
            "SALE_PERIOD_INVALID"
        )

    return instant


def _canonical_bounded_store(
    value: object,
) -> str:
    try:
        store = (
            require_canonical_sale_store(
                value
            )
        )
    except SaleStorePolicyError as exc:
        raise BoundedSaleOfferError(
            "NON_CANONICAL_STORE"
        ) from exc

    if (
        store
        not in SUPPORTED_BOUNDED_STORES
    ):
        raise BoundedSaleOfferError(
            "BOUNDED_STORE_UNSUPPORTED"
        )

    return store


def _validated_data(
    campaign: SaleCampaign,
    item: EbookItem,
    offer: StoreOffer,
    sale_data: Mapping[str, object],
    *,
    canonical_store: str = "rakuten_kobo",
) -> dict:
    if not isinstance(
        sale_data,
        Mapping,
    ):
        raise BoundedSaleOfferError(
            "SALE_DATA_INVALID"
        )

    store = _canonical_bounded_store(
        canonical_store
    )

    if (
        offer.store_name != store
        or sale_data.get(
            "store_name"
        )
        != store
    ):
        raise BoundedSaleOfferError(
            "NON_CANONICAL_STORE"
        )

    if (
        sale_data.get(
            "campaign_store"
        )
        != store
    ):
        raise BoundedSaleOfferError(
            "NON_CANONICAL_CAMPAIGN_STORE"
        )

    store_item_id = getattr(
        offer,
        "store_item_id",
        None,
    )

    if store == "rakuten_kobo":
        if (
            not isinstance(
                store_item_id,
                str,
            )
            or not store_item_id.isdigit()
            or len(
                store_item_id
            )
            != 13
        ):
            raise BoundedSaleOfferError(
                "STORE_ITEM_ID_INVALID"
            )

    elif store == "dmm":
        if (
            not isinstance(
                store_item_id,
                str,
            )
            or DMM_STORE_ITEM_ID_RE.fullmatch(
                store_item_id
            )
            is None
        ):
            raise BoundedSaleOfferError(
                "STORE_ITEM_ID_INVALID"
            )

    if (
        offer.ebook_item_id
        != item.id
        or sale_data.get(
            "ebook_item_id"
        )
        != item.id
        or sale_data.get(
            "offer_id"
        )
        != offer.id
        or sale_data.get(
            "store_item_id"
        )
        != offer.store_item_id
        or sale_data.get(
            "product_url"
        )
        != offer.product_url
        or sale_data.get(
            "title"
        )
        != item.title
        or not item.series_name
        or sale_data.get(
            "series_name"
        )
        != item.series_name
        or sale_data.get(
            "cover_image_url"
        )
        != item.cover_image_url
    ):
        raise BoundedSaleOfferError(
            "OFFER_IDENTITY_CONFLICT"
        )

    if (
        sale_data.get(
            "affiliate_url"
        )
        not in (
            None,
            "",
        )
        or "affiliate_resolution"
        in sale_data
    ):
        raise BoundedSaleOfferError(
            "AFFILIATE_MUST_BE_STAGED_SEPARATELY"
        )

    try:
        validate_sale_product_url(
            store,
            offer.product_url,
        )

        validate_sale_cover_url(
            store,
            item.cover_image_url,
        )

    except SaleStorePolicyError as exc:
        raise BoundedSaleOfferError(
            "STORE_URL_INVALID"
        ) from exc

    price = sale_data.get(
        "sale_price"
    )

    normal = sale_data.get(
        "normal_price_evidence_only"
    )

    discount = sale_data.get(
        "discount_percent"
    )

    if (
        isinstance(
            price,
            bool,
        )
        or not isinstance(
            price,
            (
                int,
                float,
            ),
        )
        or isinstance(
            normal,
            bool,
        )
        or not isinstance(
            normal,
            (
                int,
                float,
            ),
        )
        or isinstance(
            discount,
            bool,
        )
        or not isinstance(
            discount,
            (
                int,
                float,
            ),
        )
        or not 0
        < price
        < normal
        or not 0
        < discount
        <= 100
    ):
        raise BoundedSaleOfferError(
            "SALE_PRICE_INVALID"
        )

    start_value = sale_data.get(
        "sale_start_at_utc"
    )

    if (
        store == "dmm"
        and start_value
        in (
            None,
            "",
        )
    ):
        # DMM sometimes exposes the sale end
        # without exposing its beginning.
        # Use campaign start only for validation;
        # preserve the original None in sale_data.
        start = _instant(
            campaign.starts_at
        )
    else:
        start = _instant(
            start_value
        )

    end = _instant(
        sale_data.get(
            "sale_end_at_utc"
        )
    )

    if not (
        _instant(
            campaign.starts_at
        )
        <= start
        < end
        <= _instant(
            campaign.ends_at
        )
    ):
        raise BoundedSaleOfferError(
            "SALE_PERIOD_OUTSIDE_CAMPAIGN"
        )

    try:
        return json.loads(
            json.dumps(
                dict(
                    sale_data
                ),
                ensure_ascii=False,
                allow_nan=False,
            )
        )

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise BoundedSaleOfferError(
            "SALE_DATA_NOT_JSON_SAFE"
        ) from exc


def stage_bounded_sale_offer(
    session: Session,
    *,
    campaign_id: str,
    ebook_item: EbookItem,
    store_offer: StoreOffer,
    sale_data: Mapping[str, object],
    canonical_store: str = "rakuten_kobo",
) -> StagedSaleOfferResult:
    """
    Stage at most one SaleOffer.

    Never flush, commit, rollback, or delete.
    Existing callers remain Kobo by default.
    """

    store = _canonical_bounded_store(
        canonical_store
    )

    if (
        not isinstance(
            ebook_item,
            EbookItem,
        )
        or not isinstance(
            store_offer,
            StoreOffer,
        )
    ):
        raise BoundedSaleOfferError(
            "OFFER_TYPE_INVALID"
        )

    if (
        object_session(
            ebook_item
        )
        is not session
        or object_session(
            store_offer
        )
        is not session
    ):
        raise BoundedSaleOfferError(
            "UNIT_OF_WORK_MISMATCH"
        )

    with session.no_autoflush:
        campaign = session.get(
            SaleCampaign,
            campaign_id,
        )

        if campaign is None:
            raise BoundedSaleOfferError(
                "CAMPAIGN_NOT_FOUND"
            )

        data = _validated_data(
            campaign,
            ebook_item,
            store_offer,
            sale_data,
            canonical_store=store,
        )

        key = digest([
            campaign_id,
            store,
            store_offer.store_item_id,
        ])

        existing = list(
            session.scalars(
                select(
                    SaleOffer
                ).where(
                    SaleOffer.campaign_id
                    == campaign_id
                )
            )
        )

        existing.extend(
            row
            for row in session.new
            if (
                isinstance(
                    row,
                    SaleOffer,
                )
                and row.campaign_id
                == campaign_id
            )
        )

        matches = []

        for row in existing:
            current = (
                row.data
                if isinstance(
                    row.data,
                    Mapping,
                )
                else {}
            )

            if (
                current.get(
                    "store_name"
                )
                != store
            ):
                raise BoundedSaleOfferError(
                    "CAMPAIGN_STORE_CONFLICT"
                )

            same_identity = (
                current.get(
                    "store_name"
                )
                == store
                and current.get(
                    "store_item_id"
                )
                == store_offer.store_item_id
            )

            if (
                row.id == key
                or same_identity
            ):
                matches.append(
                    row
                )

        if len(
            matches
        ) > 1:
            raise BoundedSaleOfferError(
                "SALE_OFFER_IDENTITY_CONFLICT"
            )

        if matches:
            row = matches[0]

            if (
                row.id != key
                or row.ebook_item_id
                != ebook_item.id
            ):
                raise BoundedSaleOfferError(
                    "SALE_OFFER_IDENTITY_CONFLICT"
                )

            if any(
                row.data.get(
                    name
                )
                != value
                for name, value
                in data.items()
                if name
                != "affiliate_url"
            ):
                raise BoundedSaleOfferError(
                    "SALE_OFFER_SEMANTIC_CONFLICT"
                )

            return StagedSaleOfferResult(
                "EXISTING_REUSED",
                row,
            )

        row = SaleOffer(
            id=key,
            campaign_id=campaign_id,
            ebook_item_id=ebook_item.id,
            data=data,
            block_reasons=[],
        )

        session.add(
            row
        )

        return StagedSaleOfferResult(
            "CREATED",
            row,
        )
