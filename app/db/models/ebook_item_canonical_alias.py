from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EbookItemCanonicalAlias(Base):
    __tablename__ = "ebook_item_canonical_aliases"
    __table_args__ = (
        CheckConstraint(
            "alias_item_id <> canonical_item_id",
            name="ck_ebook_item_canonical_alias_distinct_ids",
        ),
        Index(
            "ix_ebook_item_canonical_aliases_canonical_item_id",
            "canonical_item_id",
        ),
    )

    # Deliberately no FK: an alias remains useful after its duplicate row is removed.
    alias_item_id: Mapped[str] = mapped_column(Text, primary_key=True)
    canonical_item_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey(
            "ebook_items.id",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    merge_reason: Mapped[str] = mapped_column(Text, nullable=False)
    merge_plan_sha256: Mapped[str | None] = mapped_column(Text)
