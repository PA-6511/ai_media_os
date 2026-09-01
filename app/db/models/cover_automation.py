from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoreCoverPolicyAgreement(Base):
    """Current responsible-person agreement for one store cover policy."""

    __tablename__ = "store_cover_policy_agreements"
    __table_args__ = (
        CheckConstraint(
            "store_name IN ('rakuten_kobo', 'amazon', 'dmm')",
            name="valid_store_cover_policy_store",
        ),
        CheckConstraint(
            "length(trim(responsible_name)) > 0",
            name="store_cover_policy_responsible_not_blank",
        ),
        CheckConstraint(
            "length(trim(policy_version)) > 0",
            name="store_cover_policy_version_not_blank",
        ),
    )

    store_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    responsible_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agreed: Mapped[bool] = mapped_column(nullable=False, default=False)
    agreed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class CoverAutomationAuditQueue(Base):
    """Slack-notification candidate queue; it contains no API credentials."""

    __tablename__ = "cover_automation_audit_queue"
    __table_args__ = (
        CheckConstraint(
            "store_name IN ('rakuten_kobo', 'amazon', 'dmm')",
            name="valid_cover_audit_store",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'NOTIFIED', 'RESOLVED')",
            name="valid_cover_audit_status",
        ),
        Index(
            "ix_cover_audit_item_reason_status",
            "ebook_item_id",
            "reason_code",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    safe_detail: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", server_default="PENDING"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
