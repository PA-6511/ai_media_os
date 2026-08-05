from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import EbookItem
from app.db.repositories.workflow_approval_repository import (
    WorkflowApprovalRepository,
)
from app.services.workflow_approval_service import (
    WorkflowApprovalDecisionResult,
    WorkflowApprovalError,
    WorkflowApprovalService,
    WorkflowApprovalTicket,
)


_ALLOWED_REQUEST_REVIEW_STATUSES = {
    "NOT_REVIEWED",
    "IN_REVIEW",
    "REJECTED",
}

_ALLOWED_DECISIONS = {
    "APPROVE",
    "REJECT",
}


class LocalReviewReadyApprovalError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LocalReviewReadyRequestResult:
    ticket: WorkflowApprovalTicket


class LocalReviewReadyApprovalService:
    """Local GUI boundary for the formal REVIEW_READY approval flow."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = WorkflowApprovalRepository(session)

    @staticmethod
    def _translate_error(exc: WorkflowApprovalError) -> None:
        raise LocalReviewReadyApprovalError(
            exc.code,
            str(exc),
        ) from exc

    def create_request(
        self,
        *,
        ebook_item_id: str,
        requested_by: str = "human:local_gui",
        ttl_minutes: int = 60,
    ) -> LocalReviewReadyRequestResult:
        normalized_item_id = (ebook_item_id or "").strip()

        if not normalized_item_id:
            raise LocalReviewReadyApprovalError(
                "invalid_request",
                "ebook_item_id is required.",
            )

        item = self.session.get(EbookItem, normalized_item_id)

        if item is None:
            raise LocalReviewReadyApprovalError(
                "item_not_found",
                "ebook item was not found.",
            )

        if item.is_excluded:
            raise LocalReviewReadyApprovalError(
                "excluded_item",
                "Excluded ebook items cannot be submitted for approval.",
            )

        if item.workflow_status != "REVIEW":
            raise LocalReviewReadyApprovalError(
                "invalid_current_status",
                "workflow_status must be REVIEW.",
            )

        if item.review_status not in _ALLOWED_REQUEST_REVIEW_STATUSES:
            raise LocalReviewReadyApprovalError(
                "invalid_review_status",
                "review_status does not permit an approval request.",
            )

        if item.review_status == "IN_REVIEW":
            pending = self.repository.find_pending(
                ebook_item_id=item.id,
                approval_type="REVIEW_READY",
            )

            if pending is None:
                raise LocalReviewReadyApprovalError(
                    "approval_state_mismatch",
                    "IN_REVIEW requires a pending approval request.",
                )

        try:
            ticket = WorkflowApprovalService(
                self.session
            ).create_request(
                item_id=item.id,
                approval_type="REVIEW_READY",
                requested_by=requested_by,
                ttl_minutes=ttl_minutes,
            )
        except WorkflowApprovalError as exc:
            self._translate_error(exc)

        return LocalReviewReadyRequestResult(ticket=ticket)

    def decide_request(
        self,
        *,
        ebook_item_id: str,
        approval_request_id: str,
        token: str,
        decision: str,
        decided_by: str = "human:local_gui",
        note: str = "",
    ) -> WorkflowApprovalDecisionResult:
        normalized_item_id = (ebook_item_id or "").strip()
        normalized_request_id = (
            approval_request_id or ""
        ).strip()
        normalized_decision = (decision or "").strip().upper()
        normalized_note = str(note or "").strip()

        if not normalized_item_id or not normalized_request_id:
            raise LocalReviewReadyApprovalError(
                "invalid_request",
                "ebook_item_id and approval_request_id are required.",
            )

        if normalized_decision not in _ALLOWED_DECISIONS:
            raise LocalReviewReadyApprovalError(
                "invalid_decision",
                "decision must be APPROVE or REJECT.",
            )

        if len(normalized_note) > 1000:
            raise LocalReviewReadyApprovalError(
                "invalid_note",
                "note exceeds maximum length.",
            )

        request = self.repository.get(normalized_request_id)

        if request is None:
            raise LocalReviewReadyApprovalError(
                "request_not_found",
                "approval request was not found.",
            )

        if request.ebook_item_id != normalized_item_id:
            raise LocalReviewReadyApprovalError(
                "request_item_mismatch",
                "approval request does not belong to the ebook item.",
            )

        if request.approval_type != "REVIEW_READY":
            raise LocalReviewReadyApprovalError(
                "invalid_approval_type",
                "approval request type must be REVIEW_READY.",
            )

        if request.status != "PENDING":
            raise LocalReviewReadyApprovalError(
                "already_decided",
                "approval request is no longer pending.",
            )

        item = self.session.get(EbookItem, normalized_item_id)

        if item is None:
            raise LocalReviewReadyApprovalError(
                "item_not_found",
                "ebook item was not found.",
            )

        if item.is_excluded:
            raise LocalReviewReadyApprovalError(
                "excluded_item",
                "Excluded ebook items cannot be approved.",
            )

        if item.review_status != "IN_REVIEW":
            raise LocalReviewReadyApprovalError(
                "approval_state_mismatch",
                "review_status must be IN_REVIEW.",
            )

        try:
            return WorkflowApprovalService(
                self.session
            ).decide_request(
                request_id=request.id,
                token=token,
                decision=normalized_decision,
                decided_by=decided_by,
                note=normalized_note,
            )
        except WorkflowApprovalError as exc:
            self._translate_error(exc)

