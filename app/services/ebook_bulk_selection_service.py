from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories.ebook_query_repository import EbookQueryRepository
from app.services.ebook_query_service import EbookSearchFilters

from app.services.ebook_affiliate_readiness_service import (
    affiliate_store_registration_state,
    build_ebook_affiliate_readiness,
)


BULK_SELECTION_MAX_COUNT = 5


@dataclass(frozen=True)
class EbookBulkCapabilities:
    affiliate_registration_capability: str
    wordpress_draft_capability: str
    wordpress_schedule_capability: str


@dataclass(frozen=True)
class EbookBulkSelectionError:
    code: str
    message: str


@dataclass(frozen=True)
class EbookBulkSelectionItem:
    ebook_item_id: str
    title: str
    volume_label: str
    affiliate_registration_capability: str
    wordpress_draft_capability: str
    wordpress_schedule_capability: str


@dataclass(frozen=True)
class EbookBulkSelectionResult:
    ok: bool
    selected_count: int
    max_count: int
    items: tuple[EbookBulkSelectionItem, ...]
    errors: tuple[EbookBulkSelectionError, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "selected_count": self.selected_count,
            "max_count": self.max_count,
            "items": [asdict(item) for item in self.items],
            "errors": [asdict(error) for error in self.errors],
        }


BULK_SELECTION_ERROR_MESSAGES = {
    "BULK_SELECTION_EMPTY": "作品を選択してください",
    "BULK_SELECTION_LIMIT_EXCEEDED": "一括処理は最大5件です",
    "BULK_SELECTION_DUPLICATE_ID": "同じ作品が重複して選択されています",
    "BULK_SELECTION_INVALID_ID": "作品IDの形式が不正です",
    "BULK_SELECTION_ITEM_NOT_FOUND": "選択された作品が見つかりません",
    "BULK_SELECTION_NOT_IN_CURRENT_RESULT": "現在の検索条件に含まれない作品です",
    "BULK_SELECTION_NOT_IN_CURRENT_PAGE": "現在のページに含まれない作品です",
    "BULK_SELECTION_EXCLUDED": "除外済み作品は選択できません",
    "BULK_SELECTION_CSRF_FAILED": "操作確認に失敗しました",
    "BULK_SELECTION_QUERY_FAILED": "選択内容を確認できませんでした",
}


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _offers(item: Any) -> list[Any]:
    return list(_value(item, "offers", ()) or ())


def build_ebook_bulk_capabilities(item: Any) -> EbookBulkCapabilities:
    item_id = str(_value(item, "id", "") or "").strip()
    title = str(_value(item, "title", "") or "").strip()
    workflow_status = str(
        _value(item, "workflow_status", "") or ""
    ).upper()
    review_status = str(
        _value(item, "review_status", "") or ""
    ).upper()
    wordpress_status = str(
        _value(item, "wordpress_status", "NOT_CREATED") or "NOT_CREATED"
    ).upper()
    wordpress_post_id = str(
        _value(item, "wordpress_post_id", "") or ""
    ).strip()

    if not item_id or not title or bool(_value(item, "is_excluded", False)):
        return EbookBulkCapabilities(
            affiliate_registration_capability="INVALID",
            wordpress_draft_capability="INVALID_STATE",
            wordpress_schedule_capability="INVALID_STATE",
        )

    offers = _offers(item)
    readiness = build_ebook_affiliate_readiness(offers)
    registration_states = {
        affiliate_store_registration_state(offers, store_name=store_name)
        for store_name in ("amazon", "rakuten_kobo", "dmm")
    }
    if readiness.affiliate_ready_count == 3:
        affiliate_capability = "ALREADY_REGISTERED"
    elif "invalid" in registration_states or not offers:
        affiliate_capability = "NEEDS_INPUT"
    else:
        affiliate_capability = "READY_TO_REGISTER"

    valid_workflow_states = {
        "NEW", "REVIEW", "READY", "SCHEDULED", "PUBLISHED", "HOLD", "ERROR"
    }
    valid_wordpress_states = {
        "NOT_CREATED", "DRAFT", "SCHEDULED", "PUBLISHED", "ERROR"
    }
    state_is_valid = (
        workflow_status in valid_workflow_states
        and wordpress_status in valid_wordpress_states
    )
    if not state_is_valid:
        draft_capability = "INVALID_STATE"
    elif wordpress_post_id or wordpress_status in {
        "DRAFT", "SCHEDULED", "PUBLISHED"
    }:
        draft_capability = "ALREADY_CREATED"
    elif review_status != "APPROVED":
        draft_capability = "NOT_APPROVED"
    elif workflow_status != "READY" or wordpress_status != "NOT_CREATED":
        draft_capability = "INVALID_STATE"
    elif any(
        not str(_value(item, field_name, "") or "").strip()
        for field_name in ("author_name", "publisher_name")
    ):
        draft_capability = "MISSING_REQUIRED_DATA"
    else:
        draft_capability = "READY"

    if not state_is_valid:
        schedule_capability = "INVALID_STATE"
    elif review_status != "APPROVED":
        schedule_capability = "NOT_APPROVED"
    elif wordpress_status == "NOT_CREATED":
        schedule_capability = "NOT_DRAFT"
    elif wordpress_status != "DRAFT":
        schedule_capability = "INVALID_STATE"
    elif not wordpress_post_id:
        schedule_capability = "MISSING_POST_ID"
    else:
        schedule_capability = "READY"

    return EbookBulkCapabilities(
        affiliate_registration_capability=affiliate_capability,
        wordpress_draft_capability=draft_capability,
        wordpress_schedule_capability=schedule_capability,
    )


class EbookBulkSelectionService:
    def __init__(self, session: Session) -> None:
        self.repository = EbookQueryRepository(session)

    @staticmethod
    def failure(code: str) -> EbookBulkSelectionResult:
        return EbookBulkSelectionResult(
            ok=False,
            selected_count=0,
            max_count=BULK_SELECTION_MAX_COUNT,
            items=(),
            errors=(
                EbookBulkSelectionError(
                    code=code,
                    message=BULK_SELECTION_ERROR_MESSAGES[code],
                ),
            ),
        )

    def validate(
        self,
        selected_ebook_item_ids: list[Any],
        *,
        filters: EbookSearchFilters,
    ) -> EbookBulkSelectionResult:
        if not selected_ebook_item_ids:
            return self.failure("BULK_SELECTION_EMPTY")
        if len(selected_ebook_item_ids) > BULK_SELECTION_MAX_COUNT:
            return self.failure("BULK_SELECTION_LIMIT_EXCEEDED")

        normalized_ids: list[str] = []
        for raw_item_id in selected_ebook_item_ids:
            if not isinstance(raw_item_id, str):
                return self.failure("BULK_SELECTION_INVALID_ID")
            try:
                normalized_ids.append(str(UUID(raw_item_id.strip())))
            except (ValueError, AttributeError):
                return self.failure("BULK_SELECTION_INVALID_ID")
        if len(set(normalized_ids)) != len(normalized_ids):
            return self.failure("BULK_SELECTION_DUPLICATE_ID")

        items = self.repository.list_items_by_ids(normalized_ids)
        items_by_id = {item.id: item for item in items}
        if len(items_by_id) != len(normalized_ids):
            return self.failure("BULK_SELECTION_ITEM_NOT_FOUND")
        if any(items_by_id[item_id].is_excluded for item_id in normalized_ids):
            return self.failure("BULK_SELECTION_EXCLUDED")

        current_page_items = self.repository.search_items(**asdict(filters))
        current_page_ids = {item.id for item in current_page_items}

        matching_arguments = asdict(
            replace(filters, limit=BULK_SELECTION_MAX_COUNT, offset=0)
        )
        matching_items = self.repository.search_items(
            **matching_arguments,
            item_ids=normalized_ids,
        )
        matching_ids = {item.id for item in matching_items}
        if any(item_id not in matching_ids for item_id in normalized_ids):
            return self.failure("BULK_SELECTION_NOT_IN_CURRENT_RESULT")
        if any(item_id not in current_page_ids for item_id in normalized_ids):
            return self.failure("BULK_SELECTION_NOT_IN_CURRENT_PAGE")

        selected_items: list[EbookBulkSelectionItem] = []
        for item_id in normalized_ids:
            item = items_by_id[item_id]
            capabilities = build_ebook_bulk_capabilities(item)
            selected_items.append(
                EbookBulkSelectionItem(
                    ebook_item_id=item.id,
                    title=item.title,
                    volume_label=item.volume_label or "",
                    affiliate_registration_capability=(
                        capabilities.affiliate_registration_capability
                    ),
                    wordpress_draft_capability=(
                        capabilities.wordpress_draft_capability
                    ),
                    wordpress_schedule_capability=(
                        capabilities.wordpress_schedule_capability
                    ),
                )
            )
        return EbookBulkSelectionResult(
            ok=True,
            selected_count=len(selected_items),
            max_count=BULK_SELECTION_MAX_COUNT,
            items=tuple(selected_items),
            errors=(),
        )