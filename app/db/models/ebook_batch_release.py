from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EbookBatchReservationReleaseEvent(Base):
    """Immutable evidence for one controlled RESERVED -> RELEASED change."""

    __tablename__ = "ebook_batch_reservation_release_events"
    __table_args__ = (
        CheckConstraint(
            "before_state = 'RESERVED' AND after_state = 'RELEASED'",
            name="valid_batch_reservation_release_transition",
        ),
        CheckConstraint(
            "slot_index >= 1 AND slot_index <= 5",
            name="valid_batch_reservation_release_slot",
        ),
        CheckConstraint(
            "candidate_workflow_state = 'REVIEW' "
            "AND candidate_review_status = 'NOT_REVIEWED'",
            name="valid_batch_reservation_release_candidate_state",
        ),
        CheckConstraint(
            "approval_execution_eligibility = 'INELIGIBLE'",
            name="valid_batch_reservation_release_approval_state",
        ),
        CheckConstraint(
            "execution_evidence_status = 'ABSENT'",
            name="valid_batch_reservation_release_execution_evidence",
        ),
        CheckConstraint(
            "length(trim(reason)) > 0",
            name="batch_reservation_release_reason_not_blank",
        ),
        CheckConstraint(
            "length(trim(release_actor)) > 0",
            name="batch_reservation_release_actor_not_blank",
        ),
        CheckConstraint(
            "length(snapshot_digest) = 64",
            name="valid_batch_reservation_release_snapshot_digest",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    # Batch tables intentionally remain SQL-only in this codebase. Database
    # foreign keys are installed by the migration.
    batch_item_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
    )
    batch_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    candidate_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approval_remediation_event_id: Mapped[str] = mapped_column(
        ForeignKey(
            "workflow_approval_remediation_events.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    release_actor: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    before_state: Mapped[str] = mapped_column(String(32), nullable=False)
    after_state: Mapped[str] = mapped_column(String(32), nullable=False)
    slot_index: Mapped[int] = mapped_column(nullable=False)
    source_batch_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
        index=True,
    )
    candidate_workflow_state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    candidate_review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    approval_execution_eligibility: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    execution_evidence_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    snapshot_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )


@event.listens_for(EbookBatchReservationReleaseEvent, "before_update")
@event.listens_for(EbookBatchReservationReleaseEvent, "before_delete")
def _prevent_batch_reservation_release_event_mutation(*_: object) -> None:
    raise ValueError("ebook batch reservation release events are immutable")
