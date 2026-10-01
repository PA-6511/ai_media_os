from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.repositories.x_post_draft_repository import (
    XPostDraftRepository,
)


_ALLOWED_SOURCE_TYPES = {
    "new_release",
    "sale",
}


@dataclass(frozen=True)
class XPostDraftSaveRequest:
    source_type: str
    source_id: str
    generated_text: str

    scheduled_at: datetime | None = None
    paid_partnership: bool = True

    ebook_item_id: str | None = None
    feedback_id: str | None = None


@dataclass(frozen=True)
class XPostDraftSaveResult:
    draft_id: str
    source_type: str
    source_id: str
    status: str
    scheduled_at: datetime | None
    paid_partnership: bool
    generated_text: str


class XPostDraftPersistenceService:
    def __init__(self, session: Session) -> None:
        self.repository = XPostDraftRepository(session)

    def save(
        self,
        request: XPostDraftSaveRequest,
    ) -> XPostDraftSaveResult:
        source_type = request.source_type.strip().lower()
        source_id = request.source_id.strip()
        generated_text = request.generated_text.strip()

        if source_type not in _ALLOWED_SOURCE_TYPES:
            raise ValueError(
                f"unsupported source_type: {source_type}"
            )

        if not source_id:
            raise ValueError("source_id is required")

        if not generated_text:
            raise ValueError("generated_text is required")

        if not isinstance(request.paid_partnership, bool):
            raise ValueError(
                "paid_partnership must be boolean"
            )

        if request.scheduled_at is not None:
            if (
                request.scheduled_at.tzinfo is None
                or request.scheduled_at.utcoffset() is None
            ):
                raise ValueError(
                    "scheduled_at must be timezone-aware"
                )

        draft = self.repository.upsert_draft(
            source_type=source_type,
            source_id=source_id,
            generated_text=generated_text,
            scheduled_at=request.scheduled_at,
            paid_partnership=request.paid_partnership,
            ebook_item_id=(
                request.ebook_item_id.strip()
                if request.ebook_item_id
                else None
            ),
            feedback_id=(
                request.feedback_id.strip()
                if request.feedback_id
                else None
            ),
        )

        return XPostDraftSaveResult(
            draft_id=draft.id,
            source_type=draft.source_type,
            source_id=draft.source_id,
            status=draft.status,
            scheduled_at=draft.scheduled_at,
            paid_partnership=draft.paid_partnership,
            generated_text=draft.generated_text,
        )
