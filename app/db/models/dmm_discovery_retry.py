from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DmmDiscoveryRetryJob(Base):
    __tablename__ = "dmm_discovery_retry_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'QUEUED',"
            "'RUNNING',"
            "'COMPLETED_NOT_FOUND',"
            "'FOUND_PENDING_REVIEW',"
            "'FAILED',"
            "'CANCELLED'"
            ")",
            name="valid_dmm_discovery_retry_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="valid_dmm_discovery_retry_attempt_count",
        ),
        UniqueConstraint(
            "source_evidence_id",
            name="uq_dmm_discovery_retry_source_evidence",
        ),
        Index(
            "ix_dmm_discovery_retry_due",
            "status",
            "retry_at",
        ),
        Index(
            "ix_dmm_discovery_retry_item_status",
            "ebook_item_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey(
            "ebook_items.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    source_evidence_id: Mapped[str] = mapped_column(
        ForeignKey(
            "store_discovery_evidence.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="QUEUED",
        server_default="QUEUED",
        index=True,
    )

    retry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    search_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    found_product_url: Mapped[str | None] = mapped_column(
        Text,
    )

    found_product_title: Mapped[str | None] = mapped_column(
        Text,
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
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
