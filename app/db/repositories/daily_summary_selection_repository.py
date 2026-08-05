from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DailySummarySelection,
    DailySummarySelectionHistory,
    EbookItem,
)


class DailySummarySelectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, *, ebook_item_id: str, summary_date: date
    ) -> DailySummarySelection | None:
        return self.session.scalar(
            select(DailySummarySelection).where(
                DailySummarySelection.ebook_item_id == ebook_item_id,
                DailySummarySelection.summary_date == summary_date,
            )
        )

    def list_for_date(self, summary_date: date) -> list[DailySummarySelection]:
        return list(
            self.session.scalars(
                select(DailySummarySelection)
                .where(DailySummarySelection.summary_date == summary_date)
                .order_by(DailySummarySelection.ebook_item_id)
            )
        )

    def list_items_for_date(self, summary_date: date) -> list[EbookItem]:
        return list(
            self.session.scalars(
                select(EbookItem)
                .where(EbookItem.release_date == summary_date)
                .order_by(
                    EbookItem.release_date,
                    EbookItem.title,
                    EbookItem.volume_label,
                    EbookItem.id,
                )
            )
        )

    def add_history(
        self,
        *,
        ebook_item_id: str,
        summary_date: date,
        before_state: str | None,
        after_state: str | None,
        changed_by: str,
        success: bool = True,
        error_code: str | None = None,
    ) -> DailySummarySelectionHistory:
        history = DailySummarySelectionHistory(
            operation="DAILY_SUMMARY_SELECTION_UPDATE",
            ebook_item_id=ebook_item_id,
            summary_date=summary_date,
            before_state=before_state,
            after_state=after_state,
            changed_by=changed_by,
            success=success,
            error_code=error_code,
        )
        self.session.add(history)
        return history