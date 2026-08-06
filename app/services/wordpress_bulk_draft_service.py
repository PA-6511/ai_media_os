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


@dataclass(frozen=True)
class BulkExecutionResult:
    request_id: str
    item_results: tuple[BulkDraftItemResult, ...]
    completed_count: int
    failed_count: int
    reconciliation_required: bool


@dataclass
class BulkDraftRequest:
    request_id: str
    selected_item_ids: tuple[str, ...]
    created_at: datetime
    expires_at: datetime
    used: bool = False
    state: BulkDraftState = BulkDraftState.PREPARED


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
        self._request: BulkDraftRequest | None = None

    def prepare_request(
        self,
        *,
        now: datetime | None = None,
    ) -> BulkDraftRequest:
        if self._request is not None:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_ALREADY_PREPARED",
                "Bulk draft request has already been prepared.",
            )

        created_at = now or _utc_now()
        request = BulkDraftRequest(
            request_id=secrets.token_urlsafe(32),
            selected_item_ids=self.selected_item_ids,
            created_at=created_at,
            expires_at=created_at
            + timedelta(minutes=BULK_DRAFT_REQUEST_TTL_MINUTES),
        )
        self._request = request
        return request

    def create_request(
        self,
        *,
        now: datetime | None = None,
    ) -> BulkDraftRequest:
        return self.prepare_request(now=now)

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
    ) -> BulkDraftRequest:
        if request.used:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_TOKEN_REUSED",
                "Bulk draft request has already been used.",
            )
        if self._request is not request:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_TOKEN_INVALID",
                "Bulk draft request was not issued by this service.",
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
        if request.state is not BulkDraftState.PREPARED:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_INVALID_STATE",
                "Bulk draft request must be prepared before confirmation.",
            )

        request.used = True
        request.state = BulkDraftState.CONFIRMED
        self.state = BulkDraftState.CONFIRMED
        return request

    def execute_request(
        self,
        request: BulkDraftRequest,
    ) -> BulkExecutionResult:
        if self._request is not request:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_TOKEN_INVALID",
                "Bulk draft request was not issued by this service.",
            )
        if request.state in {
            BulkDraftState.RUNNING,
            BulkDraftState.COMPLETED,
            BulkDraftState.PARTIAL_FAILED,
            BulkDraftState.FAILED,
            BulkDraftState.RECONCILIATION_REQUIRED,
        }:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_REQUEST_REUSED",
                "Bulk draft request has already been executed.",
            )
        if (
            not request.used
            or request.state is not BulkDraftState.CONFIRMED
            or self.state is not BulkDraftState.CONFIRMED
        ):
            raise BulkWordPressDraftError(
                "BULK_DRAFT_NOT_CONFIRMED",
                "Bulk draft request must be confirmed before execution.",
            )

        request.state = BulkDraftState.RUNNING
        self.state = BulkDraftState.RUNNING
        item_results: list[BulkDraftItemResult] = []
        reconciliation_required = False

        for index, ebook_item_id in enumerate(
            request.selected_item_ids
        ):
            try:
                item_result = self.delegate_item(ebook_item_id)
            except Exception as exc:
                item_result = self._item_failure_result(
                    ebook_item_id,
                    exc,
                )

            item_results.append(item_result)
            if self._requires_reconciliation(item_result):
                reconciliation_required = True
                for remaining_item_id in request.selected_item_ids[
                    index + 1 :
                ]:
                    item_results.append(
                        BulkDraftItemResult(
                            ebook_item_id=remaining_item_id,
                            status=BulkDraftState.FAILED.value,
                            error_code=(
                                "BULK_ABORTED_AFTER_RECONCILIATION"
                            ),
                            message=(
                                "Execution was not attempted after a "
                                "reconciliation-required result."
                            ),
                        )
                    )
                break

        completed_count = sum(
            self._is_completed(item_result)
            for item_result in item_results
        )
        failed_count = len(item_results) - completed_count

        if reconciliation_required:
            final_state = BulkDraftState.RECONCILIATION_REQUIRED
        elif completed_count == len(item_results):
            final_state = BulkDraftState.COMPLETED
        elif completed_count == 0:
            final_state = BulkDraftState.FAILED
        else:
            final_state = BulkDraftState.PARTIAL_FAILED

        request.state = final_state
        self.state = final_state
        return BulkExecutionResult(
            request_id=request.request_id,
            item_results=tuple(item_results),
            completed_count=completed_count,
            failed_count=failed_count,
            reconciliation_required=reconciliation_required,
        )

    @staticmethod
    def _is_completed(result: BulkDraftItemResult) -> bool:
        return result.status.upper() in {
            "CREATED",
            "COMPLETED",
            "WORDPRESS_DRAFT_CREATED",
        }

    @staticmethod
    def _requires_reconciliation(
        result: BulkDraftItemResult,
    ) -> bool:
        values = (result.status, result.error_code or "")
        return any(
            "RECONCILIATION_REQUIRED" in value.upper()
            or value.lower() == "reconciliation_required"
            for value in values
        )

    @classmethod
    def _item_failure_result(
        cls,
        ebook_item_id: str,
        exc: Exception,
    ) -> BulkDraftItemResult:
        error_code = str(
            getattr(exc, "code", "BULK_DRAFT_ITEM_FAILED")
        )
        reconciliation_required = (
            "RECONCILIATION_REQUIRED" in error_code.upper()
            or error_code.lower() == "reconciliation_required"
        )
        return BulkDraftItemResult(
            ebook_item_id=ebook_item_id,
            status=(
                BulkDraftState.RECONCILIATION_REQUIRED.value
                if reconciliation_required
                else BulkDraftState.FAILED.value
            ),
            error_code=error_code,
            message=(
                str(exc)
                if isinstance(exc, BulkWordPressDraftError)
                else "Item execution failed."
            ),
        )

    def delegate_item(self, ebook_item_id: str) -> BulkDraftItemResult:
        if self._item_executor is None:
            raise BulkWordPressDraftError(
                "BULK_DRAFT_EXECUTOR_NOT_CONFIGURED",
                "Single-item draft executor is not configured.",
            )
        return self._item_executor(ebook_item_id)