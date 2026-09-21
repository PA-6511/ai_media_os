from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CatalogEditHistory, EbookItem, StoreOffer
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.services.catalog_edit_service import CURRENCY_PATTERN, parse_price
from app.services.store_url_policy import (
    StoreUrlPolicyError,
    normalize_store_url,
)


class ManualStoreOfferError(ValueError):
    pass


@dataclass(frozen=True)
class ManualStoreOfferPreview:
    ebook_item_id: str
    store_name: str
    product_url: str | None
    affiliate_url: str
    price_amount: Decimal | None
    currency: str | None
    availability_status: str
    observed_at: datetime
    canonical_store_item_id: str | None = None


@dataclass(frozen=True)
class ManualStoreOfferResult:
    code: str
    ebook_item_id: str
    store_name: str
    offer_id: str
    idempotent: bool = False


class ManualStoreOfferService:
    SUPPORTED_STORES = frozenset({"rakuten_kobo"})
    ALLOWED_WORDPRESS_STATUSES = frozenset({"NOT_CREATED", "DRAFT"})
    ALLOWED_AVAILABILITY = frozenset({"FOUND", "FOUND_CONFIRMED"})

    def __init__(self, session: Session) -> None:
        self.session = session
        self.offers = StoreOfferRepository(session)

    @staticmethod
    def _observed_at(value: datetime | None) -> datetime:
        observed = value or datetime.now(timezone.utc)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return observed

    def preview_create(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        product_url: str,
        affiliate_url: str,
        price: str,
        currency: str,
        availability_status: str,
        observed_at: datetime | None,
    ) -> ManualStoreOfferPreview:
        normalized_store = store_name.strip().casefold()
        if normalized_store not in self.SUPPORTED_STORES:
            raise ManualStoreOfferError("STORE_NOT_SUPPORTED")
        item = self.session.scalar(
            select(EbookItem)
            .where(EbookItem.id == ebook_item_id)
            .with_for_update()
        )
        if item is None:
            raise ManualStoreOfferError("ITEM_NOT_FOUND")
        if item.wordpress_status not in self.ALLOWED_WORDPRESS_STATUSES:
            raise ManualStoreOfferError("WORDPRESS_STATUS_BLOCKED")
        if item.is_excluded:
            raise ManualStoreOfferError("ITEM_FROZEN")
        try:
            normalized_product = normalize_store_url(
                product_url,
                store_name=normalized_store,
                purpose="product",
                required=False,
            )
            normalized_affiliate = normalize_store_url(
                affiliate_url,
                store_name=normalized_store,
                purpose="affiliate",
                required=True,
            )
        except StoreUrlPolicyError as exc:
            raise ManualStoreOfferError(str(exc)) from exc
        assert normalized_affiliate is not None
        amount = parse_price(price)
        normalized_currency = currency.strip().upper() or (
            "JPY" if amount is not None else "JPY"
        )
        if not CURRENCY_PATTERN.fullmatch(normalized_currency):
            raise ManualStoreOfferError("CURRENCY_INVALID")
        normalized_availability = availability_status.strip().upper() or "FOUND"
        if normalized_availability not in self.ALLOWED_AVAILABILITY:
            raise ManualStoreOfferError("AVAILABILITY_INVALID")
        return ManualStoreOfferPreview(
            ebook_item_id=item.id,
            store_name=normalized_store,
            product_url=normalized_product,
            affiliate_url=normalized_affiliate,
            price_amount=amount,
            currency=normalized_currency,
            availability_status="FOUND_CONFIRMED",
            observed_at=self._observed_at(observed_at),
        )

    @staticmethod
    def _store_item_id(preview: ManualStoreOfferPreview) -> str:
        if preview.canonical_store_item_id:
            return preview.canonical_store_item_id

        # A valid Rakuten Kobo /rk/{key}/ URL carries the legacy
        # 32-hex canonical identity accepted by the metadata gate.
        # Prefer that stable identity over manual:<sha256>.
        if (
            preview.store_name == "rakuten_kobo"
            and preview.product_url
        ):
            from app.services.store_url_policy import (
                store_item_id_from_url,
            )

            url_identity = store_item_id_from_url(
                preview.product_url,
                store_name="rakuten_kobo",
            )

            if (
                ManualStoreOfferService
                ._is_kobo_canonical_store_item_id(
                    url_identity
                )
            ):
                return str(url_identity)

        identity = preview.product_url or preview.affiliate_url
        return "manual:" + sha256(identity.encode("utf-8")).hexdigest()

    def _same_offer(
        self, offer: StoreOffer, preview: ManualStoreOfferPreview
    ) -> bool:
        return all((
            offer.product_url == preview.product_url,
            offer.affiliate_url == preview.affiliate_url,
            offer.price_amount == preview.price_amount,
            offer.currency == preview.currency,
            offer.availability_status == preview.availability_status,
        ))

    def _add_history(
        self,
        *,
        preview: ManualStoreOfferPreview,
        operator: str,
    ) -> None:
        evidence = {
            "action": "MANUAL_STORE_OFFER_CREATED",
            "store_name": preview.store_name,
            "product_url_present": preview.product_url is not None,
            "affiliate_url_present": True,
            "affiliate_host": urlsplit(preview.affiliate_url).hostname,
            "affiliate_url_sha256": sha256(
                preview.affiliate_url.encode("utf-8")
            ).hexdigest(),
            "price": (
                str(preview.price_amount)
                if preview.price_amount is not None
                else None
            ),
            "source": "MANUAL",
            "validation_result": "VALID",
        }
        self.session.add(CatalogEditHistory(
            ebook_item_id=preview.ebook_item_id,
            field_name=f"{preview.store_name}.offer_created",
            before_value=None,
            after_value=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            change_reason="MANUAL_STORE_OFFER_CREATED",
            changed_by=operator,
        ))
        self.session.flush()

    def create_offer(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        product_url: str,
        affiliate_url: str,
        price: str,
        currency: str,
        availability_status: str,
        observed_at: datetime | None,
        operator: str,
    ) -> ManualStoreOfferResult:
        normalized_operator = operator.strip()
        if not normalized_operator:
            raise ManualStoreOfferError("OPERATOR_REQUIRED")
        preview = self.preview_create(
            ebook_item_id=ebook_item_id,
            store_name=store_name,
            product_url=product_url,
            affiliate_url=affiliate_url,
            price=price,
            currency=currency,
            availability_status=availability_status,
            observed_at=observed_at,
        )
        existing = self.offers.find_for_store(
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
        )
        if existing is not None:
            if self._same_offer(existing, preview):
                return ManualStoreOfferResult(
                    code="MANUAL_STORE_OFFER_CREATED",
                    ebook_item_id=ebook_item_id,
                    store_name=preview.store_name,
                    offer_id=existing.id,
                    idempotent=True,
                )
            raise ManualStoreOfferError("STORE_OFFER_ALREADY_EXISTS")
        price_yen = (
            int(preview.price_amount)
            if preview.price_amount is not None
            and preview.currency == "JPY"
            and preview.price_amount == preview.price_amount.to_integral_value()
            else None
        )
        offer = StoreOffer(
            ebook_item_id=preview.ebook_item_id,
            store_name=preview.store_name,
            store_item_id=self._store_item_id(preview),
            product_url=preview.product_url,
            affiliate_url=preview.affiliate_url,
            price_amount=preview.price_amount,
            price_yen=price_yen,
            currency=preview.currency,
            availability_status=preview.availability_status,
            verified_at=preview.observed_at,
            verification_method="MANUAL_WEB_EDIT",
            last_checked_at=preview.observed_at,
        )
        self.session.add(offer)
        self.session.flush()
        self._add_history(preview=preview, operator=normalized_operator)
        return ManualStoreOfferResult(
            code="MANUAL_STORE_OFFER_CREATED",
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
            offer_id=offer.id,
        )
    @staticmethod
    def _is_kobo_canonical_store_item_id(
        value: str | None,
    ) -> bool:
        item_id = str(value or "").strip()

        if len(item_id) == 13 and item_id.isdigit():
            return True

        return (
            len(item_id) == 32
            and all(
                character in "0123456789abcdef"
                for character in item_id
            )
        )

    def upsert_offer(
        self,
        *,
        ebook_item_id: str,
        store_name: str,
        product_url: str,
        affiliate_url: str,
        price: str,
        currency: str,
        availability_status: str,
        observed_at: datetime | None,
        operator: str,
        resolve_kobo_official: bool = False,
    ) -> ManualStoreOfferResult:
        """
        Explicit GUI create-or-update operation.

        create_offer() keeps its existing duplicate rejection
        contract. Only GUI callers that explicitly require update
        behavior use this method.
        """
        normalized_operator = operator.strip()

        if not normalized_operator:
            raise ManualStoreOfferError(
                "OPERATOR_REQUIRED"
            )

        preview = self.preview_create(
            ebook_item_id=ebook_item_id,
            store_name=store_name,
            product_url=product_url,
            affiliate_url=affiliate_url,
            price=price,
            currency=currency,
            availability_status=availability_status,
            observed_at=observed_at,
        )

        # KOBO_EXISTING_OFFER_IDEMPOTENT_PRECHECK_V1
        #
        # An unchanged existing Kobo offer is already a valid local state.
        # Do not make an external official-resolution call merely to
        # re-save the same manually supplied store payload.
        existing_before_resolution = self.offers.find_for_store(
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
        )

        if (
            resolve_kobo_official
            and preview.store_name == "rakuten_kobo"
            and existing_before_resolution is not None
            and self._is_kobo_canonical_store_item_id(
                existing_before_resolution.store_item_id
            )
            and existing_before_resolution.product_url
            == preview.product_url
            and existing_before_resolution.affiliate_url
            == preview.affiliate_url
            and existing_before_resolution.price_amount
            == preview.price_amount
            and existing_before_resolution.currency
            == preview.currency
        ):
            return ManualStoreOfferResult(
                code="MANUAL_STORE_OFFER_CREATED",
                ebook_item_id=ebook_item_id,
                store_name=preview.store_name,
                offer_id=existing_before_resolution.id,
                idempotent=True,
            )

        # KOBO_OFFICIAL_MANUAL_RESOLUTION_V3
        #
        # Official Kobo lookup is preferred, but a valid human-supplied
        # Kobo product URL must remain usable when the official title
        # search returns zero items. Other integrity failures remain fatal.
        kobo_official_fallback = False

        if resolve_kobo_official:
            if preview.store_name != "rakuten_kobo":
                raise ManualStoreOfferError(
                    "OFFICIAL_RESOLUTION_STORE_UNSUPPORTED"
                )

            if not preview.product_url:
                raise ManualStoreOfferError(
                    "KOBO_PRODUCT_URL_REQUIRED_FOR_OFFICIAL_LOOKUP"
                )

            item = self.session.get(
                EbookItem,
                ebook_item_id,
            )

            if item is None:
                raise ManualStoreOfferError(
                    "ITEM_NOT_FOUND"
                )

            from app.services.rakuten_kobo_manual_offer_resolver import (
                RakutenKoboManualOfferResolutionError,
                RakutenKoboManualOfferResolver,
            )

            try:
                resolution = (
                    RakutenKoboManualOfferResolver()
                    .resolve(
                        title=str(
                            item.title or ""
                        ).strip(),
                        product_url=preview.product_url,
                        entered_price=price,
                    )
                )
            except RakutenKoboManualOfferResolutionError as exc:
                if (
                    exc.code
                    != "KOBO_OFFICIAL_ITEM_NOT_FOUND"
                ):
                    raise ManualStoreOfferError(
                        exc.code
                    ) from exc

                # The official API call itself succeeded but returned
                # zero title-search candidates. Keep the already validated
                # human Kobo URL and generated affiliate URL instead of
                # rejecting a valid manual recovery operation.
                kobo_official_fallback = True

            else:
                preview = replace(
                    preview,
                    product_url=resolution.product_url,
                    price_amount=Decimal(
                        str(
                            resolution.item_price_yen
                        )
                    ),
                    currency="JPY",
                    canonical_store_item_id=(
                        resolution.item_number
                    ),
                )

        existing = self.offers.find_for_store(
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
        )

        if (
            existing is not None
            and preview.store_name == "rakuten_kobo"
            and not preview.canonical_store_item_id
            and self._is_kobo_canonical_store_item_id(
                existing.store_item_id
            )
        ):
            preview = replace(
                preview,
                canonical_store_item_id=(
                    existing.store_item_id
                ),
            )

        before_evidence = {
            "product_url_present": (
                existing.product_url is not None
            ),
            "affiliate_url_present": (
                existing.affiliate_url is not None
            ),
            "affiliate_url_sha256": (
                sha256(
                    existing.affiliate_url.encode(
                        "utf-8"
                    )
                ).hexdigest()
                if existing.affiliate_url
                else None
            ),
            "price": (
                str(existing.price_amount)
                if existing.price_amount
                is not None
                else None
            ),
        } if existing is not None else None

        offer, changes = self.offers.upsert_manual_offer(
            ebook_item_id=preview.ebook_item_id,
            store_name=preview.store_name,
            store_item_id=self._store_item_id(preview),
            product_url=preview.product_url or "",
            affiliate_url=preview.affiliate_url,
            price_amount=preview.price_amount,
            currency=preview.currency,
            verification_method="MANUAL_WEB_EDIT",
        )

        if not changes:
            return ManualStoreOfferResult(
                code="MANUAL_STORE_OFFER_CREATED",
                ebook_item_id=ebook_item_id,
                store_name=preview.store_name,
                offer_id=offer.id,
                idempotent=True,
            )

        after_evidence = {
            "action": (
                "MANUAL_STORE_OFFER_UPDATED"
                if existing is not None
                else "MANUAL_STORE_OFFER_CREATED"
            ),
            "store_name": (
                preview.store_name
            ),
            "product_url_present": (
                preview.product_url is not None
            ),
            "affiliate_url_present": True,
            "affiliate_host": (
                urlsplit(
                    preview.affiliate_url
                ).hostname
            ),
            "affiliate_url_sha256": (
                sha256(
                    preview.affiliate_url.encode(
                        "utf-8"
                    )
                ).hexdigest()
            ),
            "price": (
                str(
                    preview.price_amount
                )
                if preview.price_amount
                is not None
                else None
            ),
            "source": "MANUAL",
            "validation_result": "VALID",
        }

        self.session.add(
            CatalogEditHistory(
                ebook_item_id=(
                    preview.ebook_item_id
                ),
                field_name=(
                    f"{preview.store_name}."
                    + (
                        "offer_updated"
                        if existing is not None
                        else "offer_created"
                    )
                ),
                before_value=(
                    json.dumps(
                        before_evidence,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    if before_evidence is not None
                    else None
                ),
                after_value=json.dumps(
                    after_evidence,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                change_reason=(
                    "MANUAL_STORE_OFFER_UPDATED"
                    if existing is not None
                    else "MANUAL_STORE_OFFER_CREATED"
                ),
                changed_by=(
                    normalized_operator
                ),
            )
        )

        self.session.flush()

        return ManualStoreOfferResult(
            # Reuse existing GUI success notice contract.
            code="MANUAL_STORE_OFFER_CREATED",
            ebook_item_id=ebook_item_id,
            store_name=preview.store_name,
            offer_id=offer.id,
        )
