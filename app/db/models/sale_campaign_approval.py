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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SaleCampaignApprovalRequest(Base):
    __tablename__ = "sale_campaign_approval_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'PENDING', 'APPROVED', 'REJECTED', 'ON_HOLD', "
            "'EXPIRED', 'CANCELLED'"
            ")",
            name="valid_sale_campaign_approval_status",
        ),
        CheckConstraint(
            "expires_at > requested_at",
            name="valid_sale_campaign_approval_expiration",
        ),
        Index(
            "uq_sale_campaign_approval_pending_campaign",
            "campaign_id",
            unique=True,
            sqlite_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("sale_roundup_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    )
    requested_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    decided_by: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    decision_note: Mapped[str | None] = mapped_column(Text)
    slack_team_id: Mapped[str | None] = mapped_column(String(64))
    slack_channel_id: Mapped[str | None] = mapped_column(String(64))
    slack_message_ts: Mapped[str | None] = mapped_column(String(64))
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
