from __future__ import annotations

import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


BULK_DRAFT_MAX_ITEMS = 5
BULK_DRAFT_REQUEST_TTL_MINUTES = 15


class BulkDraftState(str, Enum):
    PREPARED = "PREPARED"
    CONFIRMED = "CONFIRMED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


class BulkWordPressDraftError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BulkDraftItemResult:
    ebook_item_id: str
    status: str
    wordpress_post_id: int | None = None
    error_code: str | None = None
    message: str = ""


@dataclass
class BulkDraftRequest:
    request_id: str
    selected_item_ids: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    used: bool = False


ItemExecutor = Callable[[str], BulkDraftItemResult]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BulkWordPressDraftService:
    def __init__(
        self,
        selected_item_ids: Sequence[str],
        *,
        item_executor: ItemExecutor | None = None,
    ) -> None:
        item_ids = tuple(selected_item_ids)
        if not item_ids:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_EMPTY",
                "At least one ebook item is required.",
            )
        if len(item_ids) > BULK_DRAFT_MAX_ITEMS:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_LIMIT_EXCEEDED",
                "Bulk WordPress draft creation is limited to five items.",
            )

        self.selected_item_ids = item_ids
        self.state = BulkDraftState.PREPARED
        self._item_executor = item_executor

    def create_request(
        self,
        *,
        now: datetime | None = None,
    ) -> BulkDraftRequest:
        created_at = now or _utc_now()
        return BulkDraftRequest(
            request_id=secrets.token_urlsafe(32),
            selected_item_ids=self.selected_item_ids,
            created_at=created_at,
            expires_at=created_at
            + timedelta(minutes=BULK_DRAFT_REQUEST_TTL_MINUTES),
        )

    @staticmethod
    def is_request_expired(
        request: BulkDraftRequest,
        *,
        now: datetime | None = None,
    ) -> bool:
        checked_at = now or _utc_now()
        return checked_at >= request.expires_at

    def confirm_request(
        self,
        request: BulkDraftRequest,
        *,
        now: datetime | None = None,
    ) -> None:
        if request.used:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_TOKEN_REUSED",
                "Bulk draft request has already been used.",
            )
        if self.is_request_expired(request, now=now):
            raise BulkWordPressDraftError(
                "BULK_DRAFT_TOKEN_EXPIRED",
                "Bulk draft request has expired.",
            )
        if request.selected_item_ids != self.selected_item_ids:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_REQUEST_MISMATCH",
                "Bulk draft request does not match the selected items.",
            )

        request.used = True
        self.state = BulkDraftState.CONFIRMED

    def delegate_item(self, ebook_item_id: str) -> BulkDraftItemResult:
        if self._item_executor is None:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_EXECUTOR_NOT_CONFIGURED",
                "Single-item draft executor is not configured.",
            )
        return self._item_executor(ebook_item_id)