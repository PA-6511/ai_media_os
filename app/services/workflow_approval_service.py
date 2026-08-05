from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.db.repositories.workflow_approval_repository import (
    WorkflowApprovalRepository,
)
from app.db.repositories.workflow_repository import (
    WorkflowRepository,
)
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)


_APPROVAL_SPECS = {
    "REVIEW_READY": {
        "expected": "REVIEW",
        "requested": "READY",
    },
    "PUBLISH_SCHEDULE": {
        "expected": "READY",
        "requested": "SCHEDULED",
    },
}

_ALLOWED_DECISIONS = {
    "APPROVE",
    "REJECT",
    "HOLD",
}


class WorkflowApprovalError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WorkflowApprovalTicket:
    request_id: str
    token: str
    approval_type: str
    expires_at: datetime


@dataclass(frozen=True)
class WorkflowApprovalDecisionResult:
    request_id: str
    decision: str
    request_status: str
    before_workflow_status: str
    after_workflow_status: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


class WorkflowApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = WorkflowApprovalRepository(
            session
        )

    def create_request(
        self,
        *,
        item_id: str,
        approval_type: str,
        requested_by: str,
        ttl_minutes: int = 1440,
    ) -> WorkflowApprovalTicket:
        normalized_type = (
            approval_type or ""
        ).strip().upper()

        actor = (requested_by or "").strip()

        if normalized_type not in _APPROVAL_SPECS:
            raise WorkflowApprovalError(
                "invalid_approval_type",
                "Approval type is not supported.",
            )

        if not actor:
            raise WorkflowApprovalError(
                "invalid_requester",
                "requested_by is required.",
            )

        if ttl_minutes < 1 or ttl_minutes > 10080:
            raise WorkflowApprovalError(
                "invalid_expiration",
                "ttl_minutes must be between 1 and 10080.",
            )

        item = self.session.get(EbookItem, item_id)

        if item is None:
            raise WorkflowApprovalError(
                "item_not_found",
                "ebook item was not found.",
            )

        spec = _APPROVAL_SPECS[normalized_type]
        expected = spec["expected"]
        requested = spec["requested"]

        if item.workflow_status != expected:
            raise WorkflowApprovalError(
                "invalid_current_status",
                (
                    "Current workflow status does not "
                    "match the approval requirement."
                ),
            )

        now = _utc_now()

        existing = self.repository.find_pending(
            ebook_item_id=item.id,
            approval_type=normalized_type,
        )

        if existing is not None:
            if _as_utc(existing.expires_at) <= now:
                existing.status = "EXPIRED"
                existing.decided_by = "system:expiration"
                existing.decided_at = now
                existing.decision_note = (
                    "Expired before replacement request."
                )
                self.session.flush()
            else:
                raise WorkflowApprovalError(
                    "duplicate_pending",
                    (
                        "A pending approval request "
                        "already exists."
                    ),
                )

        raw_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(
            minutes=ttl_minutes
        )

        request = WorkflowApprovalRequest(
            ebook_item_id=item.id,
            approval_type=normalized_type,
            expected_current_status=expected,
            requested_status=requested,
            request_nonce_hash=_hash_token(raw_token),
            requested_by=actor,
            requested_at=now,
            expires_at=expires_at,
        )

        try:
            if normalized_type == "REVIEW_READY":
                WorkflowStateRepository(
                    self.session
                ).set_review_status(
                    item,
                    "IN_REVIEW",
                    changed_by=actor,
                    note=(
                        "Workflow approval request created."
                    ),
                )

            self.repository.add(request)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return WorkflowApprovalTicket(
            request_id=request.id,
            token=raw_token,
            approval_type=normalized_type,
            expires_at=expires_at,
        )

    def decide_request(
        self,
        *,
        request_id: str,
        token: str,
        decision: str,
        decided_by: str,
        note: str = "",
    ) -> WorkflowApprovalDecisionResult:
        normalized_decision = (
            decision or ""
        ).strip().upper()

        actor = (decided_by or "").strip()

        if normalized_decision not in _ALLOWED_DECISIONS:
            raise WorkflowApprovalError(
                "invalid_decision",
                "Decision is not supported.",
            )

        if not actor:
            raise WorkflowApprovalError(
                "invalid_decider",
                "decided_by is required.",
            )

        request = self.repository.get_for_update(
            request_id
        )

        if request is None:
            raise WorkflowApprovalError(
                "request_not_found",
                "Approval request was not found.",
            )

        supplied_hash = _hash_token(token or "")

        if not hmac.compare_digest(
            supplied_hash,
            request.request_nonce_hash,
        ):
            raise WorkflowApprovalError(
                "invalid_token",
                "Approval token is invalid.",
            )

        if request.status != "PENDING":
            raise WorkflowApprovalError(
                "already_decided",
                "Approval request is no longer pending.",
            )

        now = _utc_now()

        if _as_utc(request.expires_at) <= now:
            request.status = "EXPIRED"
            request.decided_by = actor
            request.decided_at = now
            request.decision_note = (
                note or "Approval request expired."
            )
            self.session.commit()

            raise WorkflowApprovalError(
                "expired",
                "Approval request has expired.",
            )

        item = self.session.get(
            EbookItem,
            request.ebook_item_id,
        )

        if item is None:
            request.status = "FAILED"
            request.decided_by = actor
            request.decided_at = now
            request.decision_note = (
                note or "Referenced ebook item is missing."
            )
            self.session.commit()

            raise WorkflowApprovalError(
                "item_not_found",
                "Referenced ebook item was not found.",
            )

        before_status = item.workflow_status

        if (
            before_status
            != request.expected_current_status
        ):
            request.status = "FAILED"
            request.decided_by = actor
            request.decided_at = now
            request.decision_note = (
                note
                or (
                    "Workflow state changed before "
                    "approval decision."
                )
            )
            self.session.commit()

            raise WorkflowApprovalError(
                "stale_state",
                (
                    "Workflow state no longer matches "
                    "the approval request."
                ),
            )

        try:
            if normalized_decision == "APPROVE":
                if (
                    request.approval_type
                    == "REVIEW_READY"
                ):
                    WorkflowStateRepository(
                        self.session
                    ).set_review_status(
                        item,
                        "APPROVED",
                        changed_by=actor,
                        note=(
                            "Approval request approved."
                        ),
                    )

                WorkflowRepository(
                    self.session
                ).set_workflow_status(
                    item,
                    request.requested_status,
                    changed_by=actor,
                    note=(
                        note
                        or "Approved through approval service."
                    ),
                )

                request.status = "APPROVED"

            elif normalized_decision == "REJECT":
                if (
                    request.approval_type
                    == "REVIEW_READY"
                ):
                    WorkflowStateRepository(
                        self.session
                    ).set_review_status(
                        item,
                        "REJECTED",
                        changed_by=actor,
                        note=(
                            note
                            or "Approval request rejected."
                        ),
                    )

                request.status = "REJECTED"

            else:
                WorkflowRepository(
                    self.session
                ).set_workflow_status(
                    item,
                    "HOLD",
                    changed_by=actor,
                    note=(
                        note
                        or "Approval request placed on hold."
                    ),
                )

                request.status = "HELD"

            request.decided_by = actor
            request.decided_at = now
            request.decision_note = note or None

            self.session.commit()

        except ValueError as exc:
            self.session.rollback()

            raise WorkflowApprovalError(
                "transition_failed",
                "Workflow transition was rejected.",
            ) from exc

        except Exception:
            self.session.rollback()
            raise

        return WorkflowApprovalDecisionResult(
            request_id=request.id,
            decision=normalized_decision,
            request_status=request.status,
            before_workflow_status=before_status,
            after_workflow_status=item.workflow_status,
        )
