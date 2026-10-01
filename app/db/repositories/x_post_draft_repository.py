from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.x_post_draft import XPostDraft


class XPostDraftRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_source(
        self,
        *,
        source_type: str,
        source_id: str,
    ) -> XPostDraft | None:
        return self.session.scalar(
            select(XPostDraft).where(
                XPostDraft.source_type == source_type,
                XPostDraft.source_id == source_id,
            )
        )

    def upsert_draft(
        self,
        *,
        source_type: str,
        source_id: str,
        generated_text: str,
        scheduled_at: datetime | None,
        paid_partnership: bool,
        ebook_item_id: str | None = None,
        feedback_id: str | None = None,
    ) -> XPostDraft:
        existing = self.find_by_source(
            source_type=source_type,
            source_id=source_id,
        )

        now = datetime.now(timezone.utc)

        if existing is None:
            draft = XPostDraft(
                source_type=source_type,
                source_id=source_id,
                ebook_item_id=ebook_item_id,
                feedback_id=feedback_id,
                generated_text=generated_text,
                scheduled_at=scheduled_at,
                paid_partnership=paid_partnership,
                status="DRAFT",
                created_at=now,
                updated_at=now,
            )
            self.session.add(draft)
            self.session.flush()
            return draft

        if existing.status == "POSTED":
            raise ValueError(
                "posted X draft cannot be overwritten"
            )

        existing.ebook_item_id = ebook_item_id
        existing.feedback_id = feedback_id
        existing.generated_text = generated_text
        existing.scheduled_at = scheduled_at
        existing.paid_partnership = paid_partnership
        existing.updated_at = now

        self.session.flush()
        return existing
