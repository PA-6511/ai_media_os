from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EbookTag(Base):
    __tablename__ = "ebook_tags"
    __table_args__ = (
        UniqueConstraint("tag_key", name="uq_ebook_tags_tag_key"),
        UniqueConstraint("slug", name="uq_ebook_tags_slug"),
        Index(
            "ix_ebook_tags_group_active_order",
            "tag_group",
            "is_active",
            "display_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tag_key: Mapped[str] = mapped_column(String(64), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_group: Mapped[str] = mapped_column(String(32), nullable=False)
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
    )
    is_filterable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("1"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class EbookItemTag(Base):
    __tablename__ = "ebook_item_tags"
    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_ebook_item_tags_confidence",
        ),
        CheckConstraint(
            """
            assignment_source IN (
                'MANUAL',
                'IMPORT',
                'RULE',
                'AI',
                'PUBLISHER'
            )
            """,
            name="ck_ebook_item_tags_assignment_source",
        ),
        CheckConstraint(
            """
            review_status IN (
                'UNREVIEWED',
                'PENDING',
                'APPROVED',
                'REJECTED'
            )
            """,
            name="ck_ebook_item_tags_review_status",
        ),
        UniqueConstraint(
            "ebook_item_id",
            "tag_id",
            name="uq_ebook_item_tags_item_tag",
        ),
        Index(
            "ix_ebook_item_tags_item_review",
            "ebook_item_id",
            "review_status",
        ),
        Index(
            "ix_ebook_item_tags_tag_review",
            "tag_id",
            "review_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    ebook_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ebook_tags.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'MANUAL'"),
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=4),
        nullable=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'PENDING'"),
    )
    assigned_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
