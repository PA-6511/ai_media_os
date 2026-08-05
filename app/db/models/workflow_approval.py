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
