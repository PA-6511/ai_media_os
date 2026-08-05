from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DailySummaryRun, DailySummaryRunHistory


class DailySummaryRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_date(self, summary_date: date) -> DailySummaryRun | None:
        return self.session.scalar(
            select(DailySummaryRun).where(
                DailySummaryRun.summary_date == summary_date
            )
        )

    def save(self, run: DailySummaryRun) -> DailySummaryRun:
        self.session.add(run)
        self.session.flush()
        return run

    def add_history(
        self,
        *,
        run: DailySummaryRun,
        success: bool,
        error_code: str | None = None,
    ) -> DailySummaryRunHistory:
        history = DailySummaryRunHistory(
            operation=run.operation,
            summary_date=run.summary_date,
            summary_key=run.summary_key,
            selected_item_ids_json=run.selected_item_ids_json,
            selected_count=run.selected_count,
            input_hash=run.input_hash,
            wordpress_post_id=run.wordpress_post_id,
            wordpress_status=run.wordpress_status,
            remote_response_id=run.remote_response_id,
            success=success,
            error_code=error_code,
        )
        self.session.add(history)
        self.session.flush()
        return history