"""Persist a verified DMM StoreOffer affiliate URL into one SaleOffer."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy.orm import (
    object_session,
)

from app.db.models.ebook import (
    StoreOffer,
)
from app.db.models.sale_roundup import (
    SaleOffer,
)
from app.services.sale_store_policy import (
    SaleStorePolicyError,
    validate_sale_affiliate_url,
    validate_sale_product_url,
)


class DmmSaleAffiliatePersistenceError(
    ValueError
):
    pass


@dataclass(frozen=True)
class DmmSaleAffiliatePersistenceResult:
    status: str
    affiliate_url: str


def persist_dmm_sale_affiliate(
    *,
    store_offer: StoreOffer,
    sale_offer: SaleOffer,
) -> DmmSaleAffiliatePersistenceResult:
    if (
        not isinstance(
            store_offer,
            StoreOffer,
        )
        or not isinstance(
            sale_offer,
            SaleOffer,
        )
    ):
        raise DmmSaleAffiliatePersistenceError(
            "OFFER_TYPE_INVALID"
        )

    store_session = object_session(
        store_offer
    )

    sale_session = object_session(
        sale_offer
    )

    if (
        store_session is None
        or store_session
        is not sale_session
    ):
        raise DmmSaleAffiliatePersistenceError(
            "UNIT_OF_WORK_MISMATCH"
        )

    if (
        store_offer.store_name
        != "dmm"
    ):
        raise DmmSaleAffiliatePersistenceError(
            "NON_CANONICAL_STORE"
        )

    if not isinstance(
        sale_offer.data,
        Mapping,
    ):
        raise DmmSaleAffiliatePersistenceError(
            "SALE_DATA_INVALID"
        )

    data = dict(
        sale_offer.data
    )

    expected = {
        "campaign_store":
            "dmm",
        "store_name":
            "dmm",
        "ebook_item_id":
            store_offer.ebook_item_id,
        "offer_id":
            store_offer.id,
        "store_item_id":
            store_offer.store_item_id,
        "product_url":
            store_offer.product_url,
    }

    for key, value in expected.items():
        if data.get(
            key
        ) != value:
            raise DmmSaleAffiliatePersistenceError(
                "SALE_STORE_IDENTITY_MISMATCH"
            )

    if (
        sale_offer.ebook_item_id
        != store_offer.ebook_item_id
    ):
        raise DmmSaleAffiliatePersistenceError(
            "EBOOK_IDENTITY_MISMATCH"
        )

    affiliate_url = str(
        store_offer.affiliate_url
        or ""
    ).strip()

    if not affiliate_url:
        raise DmmSaleAffiliatePersistenceError(
            "AFFILIATE_URL_MISSING"
        )

    try:
        validate_sale_product_url(
            "dmm",
            store_offer.product_url,
        )

        validate_sale_affiliate_url(
            "dmm",
            affiliate_url,
        )

    except SaleStorePolicyError as exc:
        raise DmmSaleAffiliatePersistenceError(
            "AFFILIATE_URL_INVALID"
        ) from exc

    current = str(
        data.get(
            "affiliate_url"
        )
        or ""
    ).strip()

    if current:
        if current != affiliate_url:
            raise DmmSaleAffiliatePersistenceError(
                "AFFILIATE_URL_CONFLICT"
            )

        return (
            DmmSaleAffiliatePersistenceResult(
                status="EXISTING_REUSED",
                affiliate_url=affiliate_url,
            )
        )

    data[
        "affiliate_url"
    ] = affiliate_url

    sale_offer.data = data

    return (
        DmmSaleAffiliatePersistenceResult(
            status="UPDATED",
            affiliate_url=affiliate_url,
        )
    )
