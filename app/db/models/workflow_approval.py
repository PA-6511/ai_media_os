from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkflowApprovalRequest(Base):
    __tablename__ = "workflow_approval_requests"
    __table_args__ = (
        CheckConstraint(
            "approval_type IN "
            "('REVIEW_READY', 'PUBLISH_SCHEDULE')",
            name="valid_workflow_approval_type",
        ),
        CheckConstraint(
            "status IN "
            "('PENDING', 'APPROVED', 'REJECTED', 'HELD', "
            "'EXPIRED', 'CANCELLED', 'FAILED')",
            name="valid_workflow_approval_status",
        ),
        CheckConstraint(
            "("
            "approval_type = 'REVIEW_READY' "
            "AND expected_current_status = 'REVIEW' "
            "AND requested_status = 'READY'"
            ") OR ("
            "approval_type = 'PUBLISH_SCHEDULE' "
            "AND expected_current_status = 'READY' "
            "AND requested_status = 'SCHEDULED'"
            ")",
            name="valid_workflow_approval_transition",
        ),
        CheckConstraint(
            "expires_at > requested_at",
            name="valid_workflow_approval_expiration",
        ),
        Index(
            "ix_workflow_approval_pending_lookup",
            "ebook_item_id",
            "approval_type",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    approval_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    expected_current_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    requested_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
    )

    request_nonce_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    requested_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    decided_by: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    decision_note: Mapped[str | None] = mapped_column(Text)

    slack_team_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    slack_channel_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    slack_message_ts: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )

    ebook_item: Mapped["EbookItem"] = relationship(
        "EbookItem",
    )

    remediation_events: Mapped[
        list["WorkflowApprovalRemediationEvent"]
    ] = relationship(
        "WorkflowApprovalRemediationEvent",
        back_populates="superseded_approval_request",
        passive_deletes=True,
    )

    @property
    def execution_eligibility(self) -> str:
        if any(
            event.expected_execution_eligibility
            == "INELIGIBLE"
            for event in self.remediation_events
        ):
            return "INELIGIBLE"

        return "ELIGIBLE"


class WorkflowApprovalRemediationEvent(Base):
    """Immutable evidence that supersedes an unsafe approval."""

    __tablename__ = "workflow_approval_remediation_events"
    __table_args__ = (
        CheckConstraint(
            "event_type = 'AUTOMATED_APPROVAL_REMEDIATION'",
            name="valid_approval_remediation_event_type",
        ),
        CheckConstraint(
            "before_workflow_state = 'READY' "
            "AND before_review_status = 'APPROVED' "
            "AND after_workflow_state = 'REVIEW' "
            "AND after_review_status = 'NOT_REVIEWED'",
            name="valid_approval_remediation_transition",
        ),
        CheckConstraint(
            "human_decision_evidence_status = 'NOT_PROVEN'",
            name="valid_approval_remediation_human_evidence",
        ),
        CheckConstraint(
            "expected_execution_eligibility = 'INELIGIBLE'",
            name="valid_approval_remediation_execution_eligibility",
        ),
        CheckConstraint(
            "length(metadata_snapshot_digest) = 64",
            name="valid_approval_remediation_metadata_digest",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0",
            name="approval_remediation_reason_not_blank",
        ),
        CheckConstraint(
            "length(trim(remediation_actor)) > 0",
            name="approval_remediation_actor_not_blank",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="AUTOMATED_APPROVAL_REMEDIATION",
        server_default="AUTOMATED_APPROVAL_REMEDIATION",
    )
    candidate_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    superseded_approval_request_id: Mapped[str] = mapped_column(
        ForeignKey(
            "workflow_approval_requests.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
        index=True,
    )
    # The batch schema currently has no ORM model. The migration adds the
    # database-level RESTRICT foreign key for this identifier.
    related_batch_item_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_actor: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
    before_workflow_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    before_review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    after_workflow_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    after_review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    metadata_snapshot_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    human_decision_evidence_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NOT_PROVEN",
        server_default="NOT_PROVEN",
    )
    expected_execution_eligibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="INELIGIBLE",
        server_default="INELIGIBLE",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    superseded_approval_request: Mapped[
        WorkflowApprovalRequest
    ] = relationship(
        back_populates="remediation_events",
    )


@event.listens_for(
    WorkflowApprovalRemediationEvent,
    "before_update",
)
@event.listens_for(
    WorkflowApprovalRemediationEvent,
    "before_delete",
)
def _prevent_approval_remediation_event_mutation(
    *_: object,
) -> None:
    raise ValueError(
        "workflow approval remediation events are immutable"
    )
