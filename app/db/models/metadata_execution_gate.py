from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ImageRightsEvidence(Base):
    """Append-only evidence about permission to execute with a cover image."""

    __tablename__ = "image_rights_evidence"
    __table_args__ = (
        CheckConstraint(
            "rights_status IN "
            "('VERIFIED_ALLOWED', 'VERIFIED_NOT_ALLOWED', 'UNRESOLVED')",
            name="valid_image_rights_status",
        ),
        CheckConstraint(
            "length(trim(source_type)) > 0",
            name="image_rights_source_type_not_blank",
        ),
        CheckConstraint(
            "length(trim(source_reference)) > 0",
            name="image_rights_source_reference_not_blank",
        ),
        CheckConstraint(
            "length(trim(evidence_type)) > 0",
            name="image_rights_evidence_type_not_blank",
        ),
        CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="image_rights_evidence_reference_not_blank",
        ),
        CheckConstraint(
            "length(trim(verified_by)) > 0",
            name="image_rights_verified_by_not_blank",
        ),
        Index(
            "ix_image_rights_candidate_verified",
            "candidate_id",
            "verified_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    rights_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(Text, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class StoreDiscoveryEvidence(Base):
    """Append-only evidence that a store was checked and no offer was found."""

    __tablename__ = "store_discovery_evidence"
    __table_args__ = (
        CheckConstraint(
            "store_name IN ('amazon', 'rakuten_kobo', 'dmm')",
            name="valid_store_discovery_store_name",
        ),
        CheckConstraint(
            "discovery_status = 'VERIFIED_NOT_FOUND'",
            name="valid_store_discovery_status",
        ),
        CheckConstraint(
            "length(trim(verification_method)) > 0",
            name="store_discovery_verification_method_not_blank",
        ),
        CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="store_discovery_evidence_reference_not_blank",
        ),
        CheckConstraint(
            "length(trim(verified_by)) > 0",
            name="store_discovery_verified_by_not_blank",
        ),
        Index(
            "ix_store_discovery_candidate_store_verified",
            "candidate_id",
            "store_name",
            "verified_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    store_name: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    discovery_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="VERIFIED_NOT_FOUND"
    )
    verification_method: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_reference: Mapped[str] = mapped_column(Text, nullable=False)
    verified_by: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


class MetadataGateEvaluationEvent(Base):
    """Immutable evaluation evidence; deliberately not an authorization token."""

    __tablename__ = "metadata_gate_evaluation_events"
    __table_args__ = (
        CheckConstraint(
            "length(metadata_snapshot_digest) = 64",
            name="valid_metadata_gate_snapshot_digest",
        ),
        CheckConstraint(
            "length(trim(execution_context)) > 0",
            name="metadata_gate_execution_context_not_blank",
        ),
        CheckConstraint(
            "length(trim(gate_version)) > 0",
            name="metadata_gate_version_not_blank",
        ),
        Index(
            "ix_metadata_gate_candidate_evaluated",
            "candidate_id",
            "evaluated_at",
        ),
    )

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    execution_context: Mapped[str] = mapped_column(String(64), nullable=False)
    overall_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    blocking_reasons_json: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_profile_json: Mapped[str] = mapped_column(Text, nullable=False)
    per_field_result_json: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_snapshot_digest: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    evidence_references_json: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    gate_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )


@event.listens_for(StoreDiscoveryEvidence, "before_update")
@event.listens_for(StoreDiscoveryEvidence, "before_delete")
def _prevent_store_discovery_mutation(*_: object) -> None:
    raise ValueError("store discovery evidence is immutable")


@event.listens_for(ImageRightsEvidence, "before_update")
@event.listens_for(ImageRightsEvidence, "before_delete")
def _prevent_image_rights_mutation(*_: object) -> None:
    raise ValueError("image rights evidence is immutable")


@event.listens_for(MetadataGateEvaluationEvent, "before_update")
@event.listens_for(MetadataGateEvaluationEvent, "before_delete")
def _prevent_metadata_gate_event_mutation(*_: object) -> None:
    raise ValueError("metadata gate evaluation events are immutable")
