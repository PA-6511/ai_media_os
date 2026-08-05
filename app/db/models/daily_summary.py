from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DailySummarySelection(Base):
    __tablename__ = "daily_summary_selections"
    __table_args__ = (
        UniqueConstraint(
            "ebook_item_id",
            "summary_date",
            name="daily_summary_selection_identity",
        ),
        CheckConstraint(
            "inclusion_state IN "
            "('AUTO_INCLUDED', 'HUMAN_INCLUDED', 'HUMAN_EXCLUDED')",
            name="valid_daily_summary_inclusion_state",
        ),
        CheckConstraint(
            "selection_source IN ('AUTO', 'HUMAN')",
            name="valid_daily_summary_selection_source",
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
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    inclusion_state: Mapped[str] = mapped_column(String(32), nullable=False)
    selection_source: Mapped[str] = mapped_column(String(16), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    selected_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class DailySummarySelectionHistory(Base):
    __tablename__ = "daily_summary_selection_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    before_state: Mapped[str | None] = mapped_column(String(32))
    after_state: Mapped[str | None] = mapped_column(String(32))
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_code: Mapped[str | None] = mapped_column(String(64))


class DailySummaryRun(Base):
    __tablename__ = "daily_summary_runs"
    __table_args__ = (
        UniqueConstraint("summary_date", name="daily_summary_run_date_identity"),
        UniqueConstraint("summary_key", name="daily_summary_run_key_identity"),
        CheckConstraint(
            "wordpress_status IS NULL OR wordpress_status IN "
            "('draft', 'future', 'publish', 'trash')",
            name="valid_daily_summary_wordpress_status",
        ),
        CheckConstraint(
            "execution_status IN "
            "('PREVIEWED', 'CREATING', 'UPDATING', 'SUCCEEDED', 'FAILED')",
            name="valid_daily_summary_execution_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    wordpress_post_id: Mapped[str | None] = mapped_column(String(64), index=True)
    wordpress_status: Mapped[str | None] = mapped_column(String(16))
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_item_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    execution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    remote_response_id: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class DailySummaryRunHistory(Base):
    __tablename__ = "daily_summary_run_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    selected_item_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    wordpress_post_id: Mapped[str | None] = mapped_column(String(64))
    wordpress_status: Mapped[str | None] = mapped_column(String(16))
    remote_response_id: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )