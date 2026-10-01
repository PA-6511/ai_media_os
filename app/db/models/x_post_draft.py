from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """
    Store timezone-aware datetimes as naive UTC in SQLite,
    then restore UTC tzinfo when loading them.

    The underlying SQL column remains DATETIME, so this does
    not require another Alembic migration.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "datetime must be timezone-aware"
            )

        return (
            value
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    def process_result_value(
        self,
        value: datetime | None,
        dialect,
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )


class XPostDraft(Base):
    __tablename__ = "x_post_drafts"

    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_id",
            name="uq_x_post_drafts_source",
        ),
        CheckConstraint(
            "source_type IN ('new_release', 'sale')",
            name="ck_x_post_drafts_source_type",
        ),
        CheckConstraint(
            "status IN "
            "('DRAFT', 'READY_TO_POST', 'POSTED', 'EXPIRED', 'ERROR')",
            name="ck_x_post_drafts_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    source_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    ebook_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    feedback_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    generated_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
        index=True,
    )

    paid_partnership: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="DRAFT",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
