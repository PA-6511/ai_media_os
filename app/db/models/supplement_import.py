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


class SupplementImportRun(Base):
    __tablename__ = "supplement_import_runs"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "target_release_date",
            "raw_text_hash",
            name="supplement_import_run_input_identity",
        ),
        CheckConstraint(
            "status IN ('PARSED', 'IMPORTING', 'IMPORTED', 'FAILED')",
            name="valid_supplement_import_run_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_release_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    raw_text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PARSED")
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class SupplementImportCandidate(Base):
    __tablename__ = "supplement_import_candidates"
    __table_args__ = (
        UniqueConstraint(
            "import_run_id",
            "candidate_key",
            name="supplement_import_candidate_identity",
        ),
        CheckConstraint(
            "parser_confidence IN ('HIGH', 'REVIEW_REQUIRED', 'UNPARSED')",
            name="valid_supplement_parser_confidence",
        ),
        CheckConstraint(
            "match_status IN "
            "('NEW_CANDIDATE', 'EXACT_DUPLICATE', 'POSSIBLE_DUPLICATE', 'INVALID')",
            name="valid_supplement_match_status",
        ),
        CheckConstraint(
            "import_status IN ('PENDING', 'IMPORTED', 'SKIPPED')",
            name="valid_supplement_import_status",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("supplement_import_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    volume_label: Mapped[str | None] = mapped_column(String(100))
    release_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255))
    author_name: Mapped[str | None] = mapped_column(String(255))
    imprint_name: Mapped[str | None] = mapped_column(String(255))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parser_confidence: Mapped[str] = mapped_column(String(32), nullable=False)
    parser_warnings: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    match_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    matched_ebook_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="SET NULL"), index=True
    )
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    import_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    imported_ebook_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class SupplementParseHistory(Base):
    __tablename__ = "supplement_parse_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    import_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("supplement_import_runs.id", ondelete="SET NULL"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_release_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parsed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    unparsed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


class SupplementImportHistory(Base):
    __tablename__ = "supplement_import_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("supplement_import_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    selected_candidate_ids: Mapped[str] = mapped_column(Text, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_ebook_item_ids: Mapped[str] = mapped_column(Text, nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_skipped_count: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


class SupplementRegistrationCancellationHistory(Base):
    __tablename__ = "supplement_registration_cancellation_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("supplement_import_runs.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("supplement_import_candidates.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ebook_item_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    operator: Mapped[str] = mapped_column(String(128), nullable=False)
    cancellation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_workflow_status: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    previous_wordpress_status: Mapped[str] = mapped_column(String(32), nullable=False)
    dependency_checks_json: Mapped[str] = mapped_column(Text, nullable=False)
    cancelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
