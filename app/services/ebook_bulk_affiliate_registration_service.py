from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import CatalogEditHistory, EbookItem, StoreOffer
from app.services.store_url_policy import (
    StoreUrlPolicyError,
    normalize_store_url,
    store_item_id_from_url,
)


SUPPORTED_STORES = ("amazon", "rakuten_kobo", "dmm")
ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
ITEM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,255}$")
MAX_PRICE_YEN = 10_000_000


ERROR_MESSAGES = {
    "BULK_AFFILIATE_ITEM_NOT_FOUND": "選択された作品が見つかりません",
    "BULK_AFFILIATE_ITEM_EXCLUDED": "除外済み作品は登録できません",
    "BULK_AFFILIATE_INVALID_STORE": "対象媒体が不正です",
    "BULK_AFFILIATE_INVALID_URL": "商品URLまたは画像URLが不正です",
    "BULK_AFFILIATE_INVALID_AFFILIATE_URL": "アフィリエイトURLが不正です",
    "BULK_AFFILIATE_STORE_MISMATCH": "URLと対象媒体が一致しません",
    "BULK_AFFILIATE_ITEM_MISMATCH": "商品識別子とURLが一致しません",
    "BULK_AFFILIATE_INVALID_PRICE": "価格は1円以上の整数で入力してください",
    "BULK_AFFILIATE_OVERWRITE_NOT_CONFIRMED": "既存登録情報の更新確認が必要です",
    "BULK_AFFILIATE_CONFLICT": "同一媒体の登録が複数存在します",
    "BULK_AFFILIATE_STALE_DATA": "確認後に登録情報が変更されました",
    "BULK_AFFILIATE_NO_CHANGES": "登録対象の変更がありません",
}


class BulkAffiliateError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class BulkAffiliateStoreInput:
    store_item_id: str = ""
    product_url: str = ""
    affiliate_url: str = ""
    price: str = ""
    image_url: str = ""
    overwrite: bool = False
    expected_hash: str = ""


@dataclass(frozen=True)
class BulkAffiliateStorePlan:
    store_name: str
    operation: str
    status: str
    changed_fields: tuple[str, ...]
    current_hash: str
    store_item_id: str = ""
    product_url: str = ""
    affiliate_url: str = ""
    price_yen: int | None = None
    image_url: str = ""
    error_code: str = ""

    def safe_dict(self) -> dict[str, Any]:
        return {
            "store_name": self.store_name,
            "operation": self.operation,
            "status": self.status,
            "changed_fields": list(self.changed_fields),
            "current_hash": self.current_hash,
            "store_item_id": self.store_item_id,
            "price_yen": self.price_yen,
            "product_host": urlsplit(self.product_url).hostname or "",
            "affiliate_host": urlsplit(self.affiliate_url).hostname or "",
            "image_host": urlsplit(self.image_url).hostname or "",
            "error_code": self.error_code,
        }


@dataclass(frozen=True)
class BulkAffiliateItemPlan:
    ebook_item_id: str
    title: str
    volume_label: str
    status: str
    stores: tuple[BulkAffiliateStorePlan, ...]


@dataclass(frozen=True)
class BulkAffiliatePlan:
    ok: bool
    selected_count: int
    create_count: int
    update_count: int
    unchanged_count: int
    blocked_count: int
    items: tuple[BulkAffiliateItemPlan, ...]
    input_hash: str
    errors: tuple[dict[str, str], ...]

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "selected_count": self.selected_count,
            "create_count": self.create_count,
            "update_count": self.update_count,
            "unchanged_count": self.unchanged_count,
            "blocked_count": self.blocked_count,
            "items": [
                {
                    "ebook_item_id": item.ebook_item_id,
                    "title": item.title,
                    "volume_label": item.volume_label,
                    "status": item.status,
                    "stores": {
                        store.store_name: store.safe_dict()
                        for store in item.stores
                    },
                }
                for item in self.items
            ],
            "input_hash": self.input_hash,
            "errors": list(self.errors),
        }


def offer_state_hash(offers: Iterable[StoreOffer]) -> str:
    payload = [
        {
            "id": offer.id,
            "store_item_id": offer.store_item_id,
            "product_url": offer.product_url or "",
            "affiliate_url": offer.affiliate_url or "",
            "price_yen": offer.price_yen,
            "price_amount": str(offer.price_amount or ""),
            "currency": offer.currency or "",
            "last_checked_at": offer.last_checked_at.isoformat(),
        }
        for offer in sorted(offers, key=lambda value: value.id)
    ]
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def canonical_input_hash(
    selected_ids: Iterable[str],
    inputs: Mapping[str, Mapping[str, BulkAffiliateStoreInput]],
) -> str:
    payload = {
        item_id: {
            store_name: asdict(inputs.get(item_id, {}).get(
                store_name, BulkAffiliateStoreInput()
            ))
            for store_name in SUPPORTED_STORES
        }
        for item_id in selected_ids
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _price_yen(value: str) -> int | None:
    normalized = value.strip().replace(",", "")
    if not normalized:
        return None
    try:
        amount = Decimal(normalized)
    except InvalidOperation as exc:
        raise BulkAffiliateError("BULK_AFFILIATE_INVALID_PRICE") from exc
    if (
        not amount.is_finite()
        or amount != amount.to_integral_value()
        or amount <= 0
        or amount > MAX_PRICE_YEN
    ):
        raise BulkAffiliateError("BULK_AFFILIATE_INVALID_PRICE")
    return int(amount)


def _image_url(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    if len(normalized) > 2048 or any(ord(char) < 33 for char in normalized):
        raise BulkAffiliateError("BULK_AFFILIATE_INVALID_URL")
    parsed = urlsplit(normalized)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise BulkAffiliateError("BULK_AFFILIATE_INVALID_URL")
    return normalized


def _normalized_identifier(store_name: str, value: str) -> str:
    normalized = value.strip()
    if store_name == "amazon":
        normalized = normalized.upper()
        if not ASIN_PATTERN.fullmatch(normalized):
            raise BulkAffiliateError("BULK_AFFILIATE_ITEM_MISMATCH")
    elif normalized and not ITEM_ID_PATTERN.fullmatch(normalized):
        raise BulkAffiliateError("BULK_AFFILIATE_ITEM_MISMATCH")
    return normalized


class EbookBulkAffiliateRegistrationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load_items(self, selected_ids: list[str]) -> list[EbookItem]:
        items = list(self.session.scalars(
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.id.in_(selected_ids))
        ).unique())
        by_id = {item.id: item for item in items}
        if len(by_id) != len(selected_ids):
            raise BulkAffiliateError("BULK_AFFILIATE_ITEM_NOT_FOUND")
        ordered = [by_id[item_id] for item_id in selected_ids]
        if any(item.is_excluded for item in ordered):
            raise BulkAffiliateError("BULK_AFFILIATE_ITEM_EXCLUDED")
        return ordered

    def prefill(self, selected_ids: list[str]) -> tuple[EbookItem, ...]:
        return tuple(self.load_items(selected_ids))

    def _store_plan(
        self,
        *,
        store_name: str,
        form: BulkAffiliateStoreInput,
        existing: list[StoreOffer],
    ) -> BulkAffiliateStorePlan:
        current_hash = offer_state_hash(existing)
        if len(existing) > 1:
            return BulkAffiliateStorePlan(
                store_name, "NONE", "CONFLICT", (), current_hash,
                error_code="BULK_AFFILIATE_CONFLICT",
            )
        has_input = any((
            form.store_item_id.strip(), form.product_url.strip(),
            form.affiliate_url.strip(), form.price.strip(), form.image_url.strip(),
        ))
        current = existing[0] if existing else None
        if not has_input:
            return BulkAffiliateStorePlan(
                store_name, "NONE",
                "ALREADY_REGISTERED" if current and current.affiliate_url else "NO_INPUT",
                (), current_hash,
            )
        try:
            identifier = _normalized_identifier(store_name, form.store_item_id)
            try:
                product_url = normalize_store_url(
                    form.product_url, store_name=store_name,
                    purpose="product", required=False,
                ) or ""
            except StoreUrlPolicyError as exc:
                if str(exc) == "URL_PRODUCT_TYPE_NOT_ALLOWED":
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_ITEM_MISMATCH"
                    ) from exc
                if str(exc) == "URL_HOST_NOT_ALLOWED":
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_STORE_MISMATCH"
                    ) from exc
                raise BulkAffiliateError(
                    "BULK_AFFILIATE_INVALID_URL"
                ) from exc
            try:
                affiliate_url = normalize_store_url(
                    form.affiliate_url, store_name=store_name,
                    purpose="affiliate", required=True,
                ) or ""
            except StoreUrlPolicyError as exc:
                if str(exc) == "URL_HOST_NOT_ALLOWED":
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_STORE_MISMATCH"
                    ) from exc
                if str(exc) == "URL_PRODUCT_TYPE_NOT_ALLOWED":
                    raise BulkAffiliateError(
                        "BULK_AFFILIATE_STORE_MISMATCH"
                    ) from exc
                raise BulkAffiliateError(
                    "BULK_AFFILIATE_INVALID_AFFILIATE_URL"
                ) from exc
            price_yen = _price_yen(form.price)
            image_url = _image_url(form.image_url)
            if not identifier:
                identifier = (
                    store_item_id_from_url(product_url, store_name=store_name)
                    or store_item_id_from_url(affiliate_url, store_name=store_name)
                    or ""
                )
            if not identifier:
                raise BulkAffiliateError("BULK_AFFILIATE_ITEM_MISMATCH")
            for url in (product_url, affiliate_url):
                url_identifier = store_item_id_from_url(url, store_name=store_name)
                if url_identifier and url_identifier.casefold() != identifier.casefold():
                    raise BulkAffiliateError("BULK_AFFILIATE_ITEM_MISMATCH")
        except BulkAffiliateError as exc:
            status = (
                "ITEM_MISMATCH"
                if exc.code == "BULK_AFFILIATE_ITEM_MISMATCH"
                else "STORE_MISMATCH"
                if exc.code == "BULK_AFFILIATE_STORE_MISMATCH"
                else "INVALID_INPUT"
            )
            return BulkAffiliateStorePlan(
                store_name, "NONE", status, (), current_hash,
                error_code=exc.code,
            )

        desired = {
            "store_item_id": identifier,
            "product_url": product_url,
            "affiliate_url": affiliate_url,
            "price_yen": price_yen,
        }
        if current is None:
            return BulkAffiliateStorePlan(
                store_name, "CREATE", "CREATE_READY",
                tuple(key for key, value in desired.items() if value not in (None, "")),
                current_hash, identifier, product_url, affiliate_url,
                price_yen, image_url,
            )
        changed_fields = tuple(
            key for key, value in desired.items()
            if value not in (None, "") and getattr(current, key) != value
        )
        if not changed_fields:
            return BulkAffiliateStorePlan(
                store_name, "NONE", "ALREADY_REGISTERED", (), current_hash,
                identifier, product_url, affiliate_url, price_yen, image_url,
            )
        if current.affiliate_url and not form.overwrite:
            return BulkAffiliateStorePlan(
                store_name, "NONE", "BLOCKED", changed_fields, current_hash,
                identifier, product_url, affiliate_url, price_yen, image_url,
                "BULK_AFFILIATE_OVERWRITE_NOT_CONFIRMED",
            )
        return BulkAffiliateStorePlan(
            store_name, "UPDATE", "UPDATE_READY", changed_fields,
            current_hash, identifier, product_url, affiliate_url,
            price_yen, image_url,
        )

    def plan(
        self,
        selected_ids: list[str],
        inputs: Mapping[str, Mapping[str, BulkAffiliateStoreInput]],
    ) -> BulkAffiliatePlan:
        items = self.load_items(selected_ids)
        item_plans: list[BulkAffiliateItemPlan] = []
        errors: list[dict[str, str]] = []
        for item in items:
            stores = []
            for store_name in SUPPORTED_STORES:
                plan = self._store_plan(
                    store_name=store_name,
                    form=inputs.get(item.id, {}).get(
                        store_name, BulkAffiliateStoreInput()
                    ),
                    existing=[
                        offer for offer in item.offers
                        if offer.store_name == store_name
                    ],
                )
                stores.append(plan)
                if plan.error_code:
                    errors.append({
                        "code": plan.error_code,
                        "message": ERROR_MESSAGES[plan.error_code],
                        "ebook_item_id": item.id,
                        "store_name": store_name,
                    })
            ready_count = sum(
                store.status in {"CREATE_READY", "UPDATE_READY"}
                for store in stores
            )
            blocked = any(store.error_code for store in stores)
            item_status = (
                "BLOCKED" if blocked else
                "NO_CHANGES" if ready_count == 0 else
                "READY" if ready_count == len(SUPPORTED_STORES) else
                "PARTIALLY_READY"
            )
            item_plans.append(BulkAffiliateItemPlan(
                item.id, item.title, item.volume_label or "",
                item_status, tuple(stores),
            ))
        all_stores = [store for item in item_plans for store in item.stores]
        blocked_count = sum(bool(item.status == "BLOCKED") for item in item_plans)
        create_count = sum(store.operation == "CREATE" for store in all_stores)
        update_count = sum(store.operation == "UPDATE" for store in all_stores)
        unchanged_count = len(all_stores) - create_count - update_count
        if not blocked_count and create_count + update_count == 0:
            errors.append({
                "code": "BULK_AFFILIATE_NO_CHANGES",
                "message": ERROR_MESSAGES["BULK_AFFILIATE_NO_CHANGES"],
            })
        return BulkAffiliatePlan(
            ok=not errors,
            selected_count=len(items),
            create_count=create_count,
            update_count=update_count,
            unchanged_count=unchanged_count,
            blocked_count=blocked_count,
            items=tuple(item_plans),
            input_hash=canonical_input_hash(selected_ids, inputs),
            errors=tuple(errors),
        )

    def apply(
        self,
        selected_ids: list[str],
        inputs: Mapping[str, Mapping[str, BulkAffiliateStoreInput]],
        *,
        expected_input_hash: str,
        operator: str,
        correlation_id: str | None = None,
    ) -> BulkAffiliatePlan:
        if canonical_input_hash(selected_ids, inputs) != expected_input_hash:
            raise BulkAffiliateError("BULK_AFFILIATE_INPUT_HASH_MISMATCH")
        current_items = self.load_items(selected_ids)
        for item in current_items:
            for store_name in SUPPORTED_STORES:
                current_hash = offer_state_hash(
                    offer for offer in item.offers
                    if offer.store_name == store_name
                )
                if (
                    inputs.get(item.id, {}).get(
                        store_name, BulkAffiliateStoreInput()
                    ).expected_hash
                    != current_hash
                ):
                    raise BulkAffiliateError("BULK_AFFILIATE_STALE_DATA")
        plan = self.plan(selected_ids, inputs)
        if not plan.ok:
            raise BulkAffiliateError(plan.errors[0]["code"])
        run_id = correlation_id or str(uuid4())
        now = datetime.now(timezone.utc)
        for item_plan in plan.items:
            for store_plan in item_plan.stores:
                if store_plan.operation == "NONE":
                    continue
                form = inputs[item_plan.ebook_item_id][store_plan.store_name]
                existing = self.session.scalars(
                    select(StoreOffer).where(
                        StoreOffer.ebook_item_id == item_plan.ebook_item_id,
                        StoreOffer.store_name == store_plan.store_name,
                    )
                ).all()
                if len(existing) > 1:
                    raise BulkAffiliateError("BULK_AFFILIATE_CONFLICT")
                offer = existing[0] if existing else StoreOffer(
                    ebook_item_id=item_plan.ebook_item_id,
                    store_name=store_plan.store_name,
                    store_item_id=store_plan.store_item_id,
                )
                if not existing:
                    self.session.add(offer)
                offer.store_item_id = store_plan.store_item_id
                if store_plan.product_url:
                    offer.product_url = store_plan.product_url
                offer.affiliate_url = store_plan.affiliate_url
                if store_plan.price_yen is not None:
                    offer.price_yen = store_plan.price_yen
                    offer.price_amount = Decimal(store_plan.price_yen)
                    offer.currency = "JPY"
                offer.availability_status = "FOUND_CONFIRMED"
                offer.verification_method = "BULK_MANUAL_WEB_EDIT"
                offer.verified_at = now
                offer.last_checked_at = now
                evidence = {
                    "operation": store_plan.operation,
                    "store_name": store_plan.store_name,
                    "store_item_id": store_plan.store_item_id,
                    "affiliate_host": urlsplit(store_plan.affiliate_url).hostname,
                    "affiliate_url_present": True,
                    "price_yen": store_plan.price_yen,
                    "changed_fields": list(store_plan.changed_fields),
                    "correlation_id": run_id,
                }
                self.session.add(CatalogEditHistory(
                    ebook_item_id=item_plan.ebook_item_id,
                    field_name=f"{store_plan.store_name}.bulk_offer",
                    before_value=None,
                    after_value=json.dumps(evidence, sort_keys=True),
                    change_reason="BULK_AFFILIATE_STORE_OFFER_APPLIED",
                    changed_by=operator,
                ))
        self.session.flush()
        return plan

    def verify_readback(self, plan: BulkAffiliatePlan) -> bool:
        items = self.load_items(
            [item.ebook_item_id for item in plan.items]
        )
        items_by_id = {item.id: item for item in items}
        for item_plan in plan.items:
            item = items_by_id[item_plan.ebook_item_id]
            for store_plan in item_plan.stores:
                if store_plan.operation == "NONE":
                    continue
                matching = [
                    offer for offer in item.offers
                    if offer.store_name == store_plan.store_name
                ]
                if len(matching) != 1:
                    return False
                offer = matching[0]
                if (
                    offer.store_item_id != store_plan.store_item_id
                    or offer.affiliate_url != store_plan.affiliate_url
                    or (
                        store_plan.product_url
                        and offer.product_url != store_plan.product_url
                    )
                    or (
                        store_plan.price_yen is not None
                        and offer.price_yen != store_plan.price_yen
                    )
                ):
                    return False
        return True