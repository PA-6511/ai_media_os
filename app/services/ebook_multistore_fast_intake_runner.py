from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re
from types import SimpleNamespace

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.db.models import EbookItem, StoreOffer
from app.db.repositories.import_repository import ImportRepository
from app.db.session import SessionLocal

from app.services.affiliate_account_settings_service import (
    AffiliateAccountSettingsService,
)
from app.services.ebook_fast_intake_canonical_identity import (
    CanonicalIdentityAmbiguousError,
    find_existing_fast_intake_item,
)
from app.services.dmm_affiliate_html_parser import (
    parse_dmm_input,
)
from app.services.dmm_manual_offer_service import (
    DmmManualOfferService,
)
from app.services.ebook_fast_intake_single_runner import (
    run_fast_intake_single,
)
from app.services.ebook_multistore_fast_intake_service import (
    EbookMultistoreFastIntakeService,
    MultistoreFastIntakeError,
    MultistoreFastIntakeInput,
)
from app.services.manual_store_offer_service import (
    ManualStoreOfferService,
)
from app.services.official_cover_automation_service import (
    RakutenKoboCoverReconciliationService,
)
from app.services.rakuten_kobo_affiliate_link_service import (
    RakutenKoboAffiliateLinkService,
)
from app.services.rakuten_kobo_manual_offer_resolver import (
    fetch_official_kobo_items_by_title,
)


KOBO_ITEM_ID_RE = re.compile(
    r"^(?:[0-9]{13}|[0-9a-fA-F]{32})$"
)


def _find_existing_item(
    session,
    *,
    store_name: str,
    store_item_id: str = "",
    product_url: str = "",
    title: str,
):
    return find_existing_fast_intake_item(
        session,
        store_name=store_name,
        store_item_id=store_item_id,
        product_url=product_url,
        title=title,
    )




def _create_item(
    session,
    *,
    store_name: str,
    source_item_id: str,
    title: str,
):
    result = ImportRepository(
        session
    ).import_row({
        "source_name":
            f"{store_name}_fast_intake",
        "source_item_id":
            source_item_id,
        "title":
            title,
        "item_type":
            "tankobon",
    })

    item = session.get(
        EbookItem,
        result.ebook_item_id,
    )

    if item is None:
        raise RuntimeError(
            "IMPORTED_ITEM_NOT_FOUND"
        )

    return item


def _resolve_kobo_product_input(
    product_input: str,
    title: str,
) -> tuple[str, str]:
    value = str(
        product_input or ""
    ).strip()

    if value.lower().startswith(
        "https://"
    ):
        return value, ""

    if not KOBO_ITEM_ID_RE.fullmatch(
        value
    ):
        raise ValueError(
            "KOBO_PRODUCT_INPUT_INVALID"
        )

    candidates = (
        fetch_official_kobo_items_by_title(
            title,
            hits=5,
        )
    )

    matched = [
        candidate
        for candidate in candidates
        if str(
            candidate.get(
                "itemNumber"
            )
            or ""
        ).strip().casefold()
        == value.casefold()
    ]

    if not matched:
        raise ValueError(
            "KOBO_ITEM_ID_NOT_FOUND"
        )

    if len(matched) != 1:
        raise ValueError(
            "KOBO_ITEM_ID_AMBIGUOUS"
        )

    product_url = str(
        matched[0].get(
            "itemUrl"
        )
        or ""
    ).strip()

    if not product_url:
        raise ValueError(
            "KOBO_PRODUCT_URL_MISSING"
        )

    return (
        product_url,
        value,
    )


def _generate_kobo_affiliate_url(
    session,
    product_url: str,
) -> str:
    affiliate_id = (
        AffiliateAccountSettingsService(
            session
        ).get_affiliate_id(
            service_name="rakuten_kobo",
        )
    )

    if not affiliate_id:
        raise ValueError(
            "RAKUTEN_AFFILIATE_ID_NOT_CONFIGURED"
        )

    return (
        RakutenKoboAffiliateLinkService()
        .generate(
            product_url=product_url,
            affiliate_id=affiliate_id,
        )
        .affiliate_url
    )


def _reconcile_kobo_cover(
    ebook_item_id: str,
) -> str:
    with SessionLocal() as session:
        result = (
            RakutenKoboCoverReconciliationService(
                session
            ).reconcile_item(
                ebook_item_id
            )
        )

        return str(
            result.status
        )


def _amazon_intake(
    product_input: str,
    title: str,
    mode: str,
) -> Mapping[str, Any]:
    payload = dict(
        run_fast_intake_single(
            product_input,
            title,
            mode,
        )
    )

    if mode != "execute":
        return payload

    ebook_item_id = str(
        payload.get(
            "ebook_item_id"
        )
        or ""
    ).strip()

    kobo = (
        payload.get(
            "rakuten_kobo"
        )
        if isinstance(
            payload.get(
                "rakuten_kobo"
            ),
            Mapping,
        )
        else {}
    )

    kobo_status = str(
        kobo.get(
            "status"
        )
        or ""
    ).strip()

    if (
        ebook_item_id
        and kobo_status in {
            "SAVED",
            "ALREADY_SAVED",
        }
    ):
        try:
            payload[
                "cover_status"
            ] = (
                _reconcile_kobo_cover(
                    ebook_item_id
                )
            )
        except Exception as exc:
            payload[
                "cover_status"
            ] = "PENDING"

            payload[
                "cover_reason"
            ] = str(exc)[:300]

    return payload


def _kobo_intake(
    product_input: str,
    title: str,
    mode: str,
) -> Mapping[str, Any]:
    (
        product_url,
        canonical_input_id,
    ) = (
        _resolve_kobo_product_input(
            product_input,
            title,
        )
    )

    ebook_item_id = ""
    created = False
    offer_id = ""
    idempotent = False

    with SessionLocal() as session:
        try:
            try:
                item = _find_existing_item(
                    session,
                    store_name="rakuten_kobo",
                    store_item_id=(
                        canonical_input_id
                    ),
                    product_url=product_url,
                    title=title,
                )
            except CanonicalIdentityAmbiguousError:
                session.rollback()

                return {
                    "status": "REVIEW_REQUIRED",
                    "created": False,
                    "ebook_item_id": "",
                    "offer_id": "",
                    "product_url": product_url,
                    "canonical_store_item_id": (
                        canonical_input_id
                        or None
                    ),
                    "warnings": [
                        "CANONICAL_IDENTITY_AMBIGUOUS"
                    ],
                }

            if item is None:
                item = _create_item(
                    session,
                    store_name="rakuten_kobo",
                    source_item_id=(
                        canonical_input_id
                        or product_url
                    ),
                    title=title,
                )

                created = True

            ebook_item_id = str(
                item.id
            )

            # KOBO_FAST_INTAKE_EXISTING_IDENTITY_V2
            #
            # Existing identical Kobo identity is terminal.
            # Use the EbookItem relationship instead of introducing a
            # new direct Session query contract into this runner.
            existing_kobo_offer = next(
                (
                    offer
                    for offer in getattr(
                        item,
                        "offers",
                        (),
                    )
                    if str(
                        getattr(
                            offer,
                            "store_name",
                            "",
                        )
                        or ""
                    ).strip()
                    == "rakuten_kobo"
                ),
                None,
            )

            if existing_kobo_offer is not None:
                existing_store_item_id = str(
                    getattr(
                        existing_kobo_offer,
                        "store_item_id",
                        "",
                    )
                    or ""
                ).strip()

                existing_product_url = str(
                    getattr(
                        existing_kobo_offer,
                        "product_url",
                        "",
                    )
                    or ""
                ).strip()

                identity_matches = (
                    bool(canonical_input_id)
                    and (
                        existing_store_item_id.casefold()
                        == canonical_input_id.casefold()
                    )
                ) or (
                    bool(product_url)
                    and existing_product_url
                    == product_url
                )

                if identity_matches:
                    session.rollback()

                    return {
                        "status": "EXISTING",
                        "created": False,
                        "ebook_item_id":
                            ebook_item_id,
                        "offer_id": str(
                            getattr(
                                existing_kobo_offer,
                                "id",
                                "",
                            )
                            or ""
                        ),
                        "product_url": (
                            existing_product_url
                            or product_url
                        ),
                        "canonical_store_item_id": (
                            existing_store_item_id
                            or canonical_input_id
                            or None
                        ),
                        "cover_status": str(
                            getattr(
                                item,
                                "cover_status",
                                "",
                            )
                            or "EXISTING"
                        ),
                    }

            affiliate_url = (
                _generate_kobo_affiliate_url(
                    session,
                    product_url,
                )
            )

            saved = (
                ManualStoreOfferService(
                    session
                ).upsert_offer(
                    ebook_item_id=(
                        ebook_item_id
                    ),
                    store_name=(
                        "rakuten_kobo"
                    ),
                    product_url=(
                        product_url
                    ),
                    affiliate_url=(
                        affiliate_url
                    ),
                    price="",
                    currency="JPY",
                    availability_status=(
                        "FOUND"
                    ),
                    observed_at=None,
                    operator=(
                        "multistore_fast_intake"
                    ),
                    resolve_kobo_official=True,
                )
            )

            offer_id = str(
                saved.offer_id
            )

            idempotent = bool(
                saved.idempotent
            )

            if mode == "execute":
                session.commit()
            else:
                session.rollback()

        except Exception:
            session.rollback()
            raise

    payload: dict[str, Any] = {
        "status": (
            "DRY_RUN"
            if mode == "dry_run"
            else (
                "EXISTING"
                if idempotent
                and not created
                else "REGISTERED"
            )
        ),
        "created": created,
        "ebook_item_id":
            ebook_item_id,
        "offer_id":
            offer_id,
        "product_url":
            product_url,
        "canonical_store_item_id":
            canonical_input_id
            or None,
    }

    if mode == "execute":
        try:
            payload[
                "cover_status"
            ] = (
                _reconcile_kobo_cover(
                    ebook_item_id
                )
            )
        except Exception as exc:
            payload[
                "cover_status"
            ] = "PENDING"

            payload[
                "cover_reason"
            ] = str(exc)[:300]

    return payload


def _dmm_intake(
    product_input: str,
    title: str,
    mode: str,
) -> Mapping[str, Any]:
    parsed = parse_dmm_input(
        product_input
    )

    store_item_id = str(
        parsed.product_id
        or ""
    ).strip()

    product_url = str(
        parsed.product_url
        or ""
    ).strip()

    source_item_id = (
        store_item_id
        or product_url
    )

    if not source_item_id:
        raise ValueError(
            "DMM_PRODUCT_IDENTITY_MISSING"
        )

    created = False
    ebook_item_id = ""
    offer_id = ""
    unchanged = False

    with SessionLocal() as session:
        try:
            try:
                item = _find_existing_item(
                    session,
                    store_name="dmm",
                    store_item_id=(
                        store_item_id
                    ),
                    product_url=(
                        product_url
                    ),
                    title=title,
                )
            except CanonicalIdentityAmbiguousError:
                session.rollback()

                return {
                    "status": "REVIEW_REQUIRED",
                    "created": False,
                    "ebook_item_id": "",
                    "offer_id": "",
                    "product_url": product_url,
                    "store_item_id": (
                        store_item_id
                        or None
                    ),
                    "warnings": [
                        "CANONICAL_IDENTITY_AMBIGUOUS"
                    ],
                }

            if item is None:
                item = _create_item(
                    session,
                    store_name="dmm",
                    source_item_id=(
                        source_item_id
                    ),
                    title=title,
                )

                created = True

            ebook_item_id = str(
                item.id
            )

            service = (
                DmmManualOfferService(
                    session
                )
            )

            preview = (
                service.preview_input(
                    ebook_item_id=(
                        ebook_item_id
                    ),
                    dmm_input=(
                        product_input
                    ),
                    price="",
                    currency="JPY",
                )
            )

            if not (
                preview.registration_allowed
            ):
                warnings = list(
                    preview.blocking_warnings
                )

                session.rollback()

                return {
                    "status":
                        "REVIEW_REQUIRED",
                    "created":
                        created,
                    "ebook_item_id":
                        ebook_item_id,
                    "store_item_id":
                        str(
                            preview.store_item_id
                            or ""
                        ),
                    "product_url":
                        str(
                            preview.product_url
                            or ""
                        ),
                    "warnings":
                        warnings,
                }

            saved = service.save(
                preview=preview,
                confirmed=True,
                reason=(
                    "DMM multistore "
                    "fast intake"
                ),
                changed_by=(
                    "human:local_gui"
                ),
            )

            offer_id = str(
                saved.offer_id
            )

            unchanged = bool(
                saved.unchanged
            )

            if mode == "execute":
                session.commit()
            else:
                session.rollback()

        except Exception:
            session.rollback()
            raise

    return {
        "status": (
            "DRY_RUN"
            if mode == "dry_run"
            else (
                "EXISTING"
                if unchanged
                and not created
                else "REGISTERED"
            )
        ),
        "created":
            created,
        "ebook_item_id":
            ebook_item_id,
        "offer_id":
            offer_id,
        "store_item_id":
            store_item_id,
        "product_url":
            product_url,
        "cover_status": (
            "QUEUED_BY_STORE_OFFER_TRIGGER"
            if mode == "execute"
            else "NOT_QUEUED_DRY_RUN"
        ),
    }


def run_multistore_fast_intake(
    store_name: str,
    product_input: str,
    title: str,
    mode: str,
) -> Mapping[str, Any]:
    service = (
        EbookMultistoreFastIntakeService(
            amazon_intake=(
                _amazon_intake
            ),
            kobo_intake=(
                _kobo_intake
            ),
            dmm_intake=(
                _dmm_intake
            ),
        )
    )

    result = service.run_one(
        MultistoreFastIntakeInput(
            store_name=store_name,
            product_input=product_input,
            title=title,
        ),
        mode=mode,
    )

    return {
        "store_name":
            result.store_name,
        "product_input":
            result.product_input,
        "title":
            result.title,
        "mode":
            result.mode,
        "payload":
            dict(
                result.payload
            ),
    }
