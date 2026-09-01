from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    CoverAutomationAuditQueue,
    EbookItem,
    StoreCoverPolicyAgreement,
)
from app.integrations.rakuten_kobo_api_client import (
    RakutenKoboApiClient,
    RakutenKoboApiError,
    RequestsGetTransport,
)
from app.integrations.rakuten_kobo_live_configuration import (
    load_repository_live_configuration,
)


RAKUTEN_KOBO_COVER_POLICY_VERSION = "2026-08-14.v1"
RAKUTEN_KOBO_POLICY_TEXT = (
    "楽天Kobo公式APIが返す書影のみを、対応する楽天Koboリンクとともに"
    "掲載することを了承する"
)
COVER_SOURCES = {
    "RAKUTEN_KOBO_API",
    "AMAZON_PA_API",
    "DMM_AFFILIATE_API",
    "MANUAL",
    "UNKNOWN",
}
COVER_STATUSES = {
    "AUTO_ALLOWED",
    "HIDDEN_UNVERIFIED",
    "MANUAL_REVIEW",
    "UNAVAILABLE",
}


def _kobo_api_price_yen(
    value: Any,
) -> int | None:
    """
    Return a verified positive integral JPY amount from
    Rakuten Kobo EbookSearch itemPrice.

    Price synchronization is intentionally non-blocking
    for cover reconciliation. Missing or malformed
    itemPrice must not make an otherwise valid official
    cover unavailable.
    """
    if value is None:
        return None

    raw = str(value).strip()

    if not raw:
        return None

    try:
        price = Decimal(raw)
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None

    if (
        not price.is_finite()
        or price <= 0
        or price != price.to_integral_value()
    ):
        return None

    return int(price)


class OfficialCoverAutomationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class CoverPolicyState:
    store_name: str
    current_version: str
    agreed: bool
    responsible_name: str
    agreed_at: datetime | None
    recorded_version: str

    @property
    def current_and_agreed(self) -> bool:
        return self.agreed and self.recorded_version == self.current_version


@dataclass(frozen=True)
class CoverReconciliationResult:
    ebook_item_id: str
    status: str
    reason_code: str | None
    api_called: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _https(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urlsplit(text)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return ""
    if parsed.username or parsed.password or parsed.fragment:
        return ""
    return text


class StoreCoverPolicyService:
    def __init__(self, session: Session, *, now: Callable[[], datetime] = _utc_now):
        self.session = session
        self._now = now

    def rakuten_kobo_state(self) -> CoverPolicyState:
        row = self.session.get(StoreCoverPolicyAgreement, "rakuten_kobo")
        return CoverPolicyState(
            store_name="rakuten_kobo",
            current_version=RAKUTEN_KOBO_COVER_POLICY_VERSION,
            agreed=bool(row and row.agreed),
            responsible_name=str(row.responsible_name if row else ""),
            agreed_at=row.agreed_at if row else None,
            recorded_version=str(row.policy_version if row else ""),
        )

    def agree_rakuten_kobo(
        self,
        *,
        responsible_name: str,
        confirmed: bool,
    ) -> CoverPolicyState:
        name = str(responsible_name or "").strip()
        if not name:
            raise OfficialCoverAutomationError("RESPONSIBLE_NAME_REQUIRED")
        if not confirmed:
            raise OfficialCoverAutomationError("AGREEMENT_REQUIRED")
        now = self._now()
        row = self.session.get(StoreCoverPolicyAgreement, "rakuten_kobo")
        if row is None:
            row = StoreCoverPolicyAgreement(store_name="rakuten_kobo")
            self.session.add(row)
        row.responsible_name = name
        row.agreed = True
        row.agreed_at = now
        row.policy_version = RAKUTEN_KOBO_COVER_POLICY_VERSION
        row.updated_at = now
        self.session.commit()
        return self.rakuten_kobo_state()

    def enforce_current_version(self, *, commit: bool = True) -> int:
        """Fail closed after a policy-version change without exposing covers."""

        state = self.rakuten_kobo_state()
        if state.current_and_agreed:
            return 0
        result = self.session.execute(
            update(EbookItem)
            .where(
                EbookItem.cover_source == "RAKUTEN_KOBO_API",
                EbookItem.cover_status == "AUTO_ALLOWED",
            )
            .values(
                cover_status="HIDDEN_UNVERIFIED",
                image_status="MISSING",
            )
        )
        count = int(result.rowcount or 0)
        if count:
            item_ids = self.session.scalars(
                select(EbookItem.id).where(
                    EbookItem.cover_source == "RAKUTEN_KOBO_API",
                    EbookItem.cover_status == "HIDDEN_UNVERIFIED",
                )
            ).all()
            for item_id in item_ids:
                _enqueue_once(
                    self.session,
                    ebook_item_id=item_id,
                    reason_code="POLICY_VERSION_CHANGED",
                )
        if commit:
            self.session.commit()
        return count


class RakutenKoboCoverReconciliationService:
    def __init__(
        self,
        session: Session,
        *,
        api_client: RakutenKoboApiClient | None = None,
        configuration_loader: Callable[..., Any] = (
            load_repository_live_configuration
        ),
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.session = session
        self.api_client = api_client or RakutenKoboApiClient(
            RequestsGetTransport()
        )
        self.configuration_loader = configuration_loader
        self._now = now

    def reconcile_item(self, ebook_item_id: str) -> CoverReconciliationResult:
        item = self.session.scalar(
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.id == str(ebook_item_id or "").strip())
        )
        if item is None:
            raise OfficialCoverAutomationError("ITEM_NOT_FOUND")
        offers = [
            offer for offer in item.offers
            if str(offer.store_name or "").strip().casefold()
            == "rakuten_kobo"
        ]
        if len(offers) != 1:
            return self._hide(item, "KOBO_OFFER_UNAVAILABLE", unavailable=True)
        offer = offers[0]
        expected_item_number = str(offer.store_item_id or "").strip()
        if not expected_item_number:
            return self._hide(item, "KOBO_ITEM_ID_MISSING")

        policy = StoreCoverPolicyService(self.session).rakuten_kobo_state()
        if not policy.current_and_agreed:
            return self._hide(item, "POLICY_NOT_AGREED")

        configuration = self.configuration_loader(
            title=None,
            item_number=expected_item_number,
        )
        if configuration is None:
            return self._hide(item, "STORE_NOT_CONNECTED")

        try:
            response = self.api_client.fetch(configuration)
            payload = json.loads(response.body.decode("utf-8"))
            api_item = self._single_item(payload)
        except (RakutenKoboApiError, UnicodeError, json.JSONDecodeError) as exc:
            code = getattr(exc, "code", "API_RESPONSE_INVALID")
            return self._hide(item, "API_FAILURE", safe_detail=str(code))
        except OfficialCoverAutomationError as exc:
            return self._hide(item, exc.code)

        actual_item_number = str(api_item.get("itemNumber") or "").strip()
        if actual_item_number != expected_item_number:
            return self._hide(item, "ITEM_MISMATCH")
        image_url = _https(api_item.get("largeImageUrl"))
        if not image_url:
            return self._hide(item, "IMAGE_MISSING")

        api_price_yen = _kobo_api_price_yen(
            api_item.get("itemPrice")
        )

        affiliate_url = _https(api_item.get("affiliateUrl"))
        if not affiliate_url:
            return self._hide(item, "AFFILIATE_URL_MISSING")

        now = self._now()
        item.cover_source = "RAKUTEN_KOBO_API"
        item.cover_source_item_id = actual_item_number
        item.cover_image_url = image_url
        item.cover_destination_url = affiliate_url
        item.cover_retrieved_at = now
        item.cover_policy_version = policy.current_version
        item.cover_status = "AUTO_ALLOWED"
        item.image_status = "READY"
        offer.affiliate_url = affiliate_url
        item_url = _https(api_item.get("itemUrl"))
        if item_url:
            offer.product_url = item_url

        # R5_KOBO_OFFICIAL_PRICE_SYNC_V1:
        # itemPrice is supplied by the same verified Kobo API
        # response used for item identity and cover evidence.
        # Do not manufacture or infer a price when the provider
        # does not return a valid positive integral amount.
        if api_price_yen is not None:
            offer.price_yen = api_price_yen
            offer.price_amount = Decimal(api_price_yen)
            offer.currency = "JPY"

        offer.verified_at = now
        offer.verification_method = "RAKUTEN_KOBO_API_RESPONSE"
        self._resolve_pending(item.id)
        self.session.commit()
        return CoverReconciliationResult(item.id, "AUTO_ALLOWED", None, True)

    @staticmethod
    def _single_item(payload: Mapping[str, Any]) -> Mapping[str, Any]:
        wrappers = payload.get("Items")
        if not isinstance(wrappers, list) or len(wrappers) != 1:
            raise OfficialCoverAutomationError("API_ITEM_NOT_UNIQUE")
        wrapper = wrappers[0]
        if not isinstance(wrapper, Mapping):
            raise OfficialCoverAutomationError("API_RESPONSE_INVALID")
        value = wrapper.get("Item", wrapper)
        if not isinstance(value, Mapping):
            raise OfficialCoverAutomationError("API_RESPONSE_INVALID")
        return value

    def _hide(
        self,
        item: EbookItem,
        reason_code: str,
        *,
        safe_detail: str | None = None,
        unavailable: bool = False,
    ) -> CoverReconciliationResult:
        # Retain prior API references for internal audit, but never render them.
        item.cover_status = (
            "UNAVAILABLE" if unavailable else "HIDDEN_UNVERIFIED"
        )
        item.image_status = "MISSING"
        _enqueue_once(
            self.session,
            ebook_item_id=item.id,
            reason_code=reason_code,
            safe_detail=safe_detail,
        )
        self.session.commit()
        return CoverReconciliationResult(
            item.id, item.cover_status, reason_code, reason_code not in {
                "POLICY_NOT_AGREED", "STORE_NOT_CONNECTED",
                "KOBO_OFFER_UNAVAILABLE", "KOBO_ITEM_ID_MISSING",
            }
        )

    def _resolve_pending(self, ebook_item_id: str) -> None:
        now = self._now()
        for row in self.session.scalars(
            select(CoverAutomationAuditQueue).where(
                CoverAutomationAuditQueue.ebook_item_id == ebook_item_id,
                CoverAutomationAuditQueue.store_name == "rakuten_kobo",
                CoverAutomationAuditQueue.status == "PENDING",
            )
        ):
            row.status = "RESOLVED"
            row.resolved_at = now


def _enqueue_once(
    session: Session,
    *,
    ebook_item_id: str,
    reason_code: str,
    safe_detail: str | None = None,
) -> None:
    exists = session.scalar(
        select(CoverAutomationAuditQueue.id).where(
            CoverAutomationAuditQueue.ebook_item_id == ebook_item_id,
            CoverAutomationAuditQueue.store_name == "rakuten_kobo",
            CoverAutomationAuditQueue.reason_code == reason_code,
            CoverAutomationAuditQueue.status == "PENDING",
        ).limit(1)
    )
    if exists is not None:
        return
    session.add(
        CoverAutomationAuditQueue(
            ebook_item_id=ebook_item_id,
            store_name="rakuten_kobo",
            reason_code=reason_code,
            safe_detail=str(safe_detail or "")[:240] or None,
        )
    )
