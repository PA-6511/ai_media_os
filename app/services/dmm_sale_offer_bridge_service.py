# DMM_SALE_OFFER_BRIDGE_V1

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    StoreOffer,
)
from app.db.repositories.import_repository import (
    ImportRepository,
)
from app.services.bounded_sale_offer_persistence_service import (
    StagedSaleOfferResult,
    stage_bounded_sale_offer,
)
from app.services.dmm_manual_offer_service import (
    DmmManualOfferService,
)
from app.services.dmm_sale_candidate_service import (
    DmmSaleCandidate,
)
from app.services.ebook_fast_intake_canonical_identity import (
    CanonicalIdentityAmbiguousError,
    find_existing_fast_intake_item,
)


class DmmSaleOfferBridgeError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class DmmSaleOfferBridgeResult:
    ebook_item_id: str
    store_offer_id: str
    sale_offer_id: str
    catalog_created: bool
    sale_offer_status: str


def _create_dmm_item(
    session: Session,
    candidate: DmmSaleCandidate,
) -> EbookItem:
    imported = ImportRepository(
        session
    ).import_row({
        "source_name":
            "dmm_fast_intake",
        "source_item_id":
            candidate.product_id
            or candidate.product_url,
        "title":
            candidate.title,
        "item_type":
            "tankobon",
    })

    item = session.get(
        EbookItem,
        imported.ebook_item_id,
    )

    if item is None:
        raise DmmSaleOfferBridgeError(
            "IMPORTED_ITEM_NOT_FOUND"
        )

    return item


def _source_row_sha256(
    candidate: DmmSaleCandidate,
) -> str:
    payload = {
        "campaign_url":
            candidate.campaign_url,
        "product_id":
            candidate.product_id,
        "product_url":
            candidate.product_url,
        "normal_price_yen":
            candidate.normal_price_yen,
        "sale_price_yen":
            candidate.sale_price_yen,
        "discount_percent":
            candidate.discount_percent,
        "sale_start_at":
            candidate.sale_start_at,
        "sale_end_at":
            candidate.sale_end_at,
        "source_method":
            candidate.source_method,
    }

    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        allow_nan=False,
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        encoded
    ).hexdigest()


def stage_dmm_sale_candidate(
    session: Session,
    *,
    campaign_id: str,
    candidate: DmmSaleCandidate,
) -> DmmSaleOfferBridgeResult:
    try:
        item = (
            find_existing_fast_intake_item(
                session,
                store_name="dmm",
                store_item_id=(
                    candidate.product_id
                ),
                product_url=(
                    candidate.product_url
                ),
                title=(
                    candidate.title
                ),
            )
        )

    except CanonicalIdentityAmbiguousError as exc:
        raise DmmSaleOfferBridgeError(
            "CANONICAL_IDENTITY_AMBIGUOUS"
        ) from exc

    created = False

    if item is None:
        item = _create_dmm_item(
            session,
            candidate,
        )
        created = True

    if not str(
        item.series_name
        or ""
    ).strip():
        item.series_name = (
            candidate.series_name
        )

    if not str(
        item.cover_image_url
        or ""
    ).strip():
        item.cover_image_url = (
            candidate.cover_image_url
        )

    if not str(
        item.series_name
        or ""
    ).strip():
        raise DmmSaleOfferBridgeError(
            "SERIES_NAME_REQUIRED"
        )

    if not str(
        item.cover_image_url
        or ""
    ).strip():
        raise DmmSaleOfferBridgeError(
            "COVER_IMAGE_REQUIRED"
        )

    service = DmmManualOfferService(
        session
    )

    preview = service.preview_input(
        ebook_item_id=str(
            item.id
        ),
        dmm_input=(
            candidate.product_url
        ),
        price=str(
            candidate.sale_price_yen
        ),
        currency="JPY",
    )

    if not preview.registration_allowed:
        raise DmmSaleOfferBridgeError(
            "DMM_OFFER_REVIEW_REQUIRED:"
            + ",".join(
                preview.blocking_warnings
            )
        )

    saved = service.save(
        preview=preview,
        confirmed=True,
        reason=(
            "DMM sale candidate intake"
        ),
        changed_by=(
            "system:dmm_sale_bridge"
        ),
    )

    offer = session.get(
        StoreOffer,
        saved.offer_id,
    )

    if offer is None:
        raise DmmSaleOfferBridgeError(
            "STORE_OFFER_NOT_FOUND"
        )

    sale_data = {
        "campaign_store":
            "dmm",
        "store_name":
            "dmm",
        "ebook_item_id":
            item.id,
        "offer_id":
            offer.id,
        "store_item_id":
            offer.store_item_id,
        "product_url":
            offer.product_url,
        "title":
            item.title,
        "series_name":
            item.series_name,
        "cover_image_url":
            item.cover_image_url,
        "sale_price":
            candidate.sale_price_yen,
        "normal_price_evidence_only":
            candidate.normal_price_yen,
        "discount_percent":
            candidate.discount_percent,
        "sale_start_at_utc":
            candidate.sale_start_at,
        "sale_end_at_utc":
            candidate.sale_end_at,
        "source_name":
            "dmm",
        "source_row_sha256":
            _source_row_sha256(
                candidate
            ),
        "affiliate_url":
            None,
        "source_method":
            candidate.source_method,
        "source_filter_threshold":
            candidate.source_filter_threshold,
        "campaign_url":
            candidate.campaign_url,
    }

    staged: StagedSaleOfferResult = (
        stage_bounded_sale_offer(
            session,
            campaign_id=campaign_id,
            ebook_item=item,
            store_offer=offer,
            sale_data=sale_data,
            canonical_store="dmm",
        )
    )

    return DmmSaleOfferBridgeResult(
        ebook_item_id=str(
            item.id
        ),
        store_offer_id=str(
            offer.id
        ),
        sale_offer_id=str(
            staged.sale_offer.id
        ),
        catalog_created=created,
        sale_offer_status=(
            staged.status
        ),
    )
