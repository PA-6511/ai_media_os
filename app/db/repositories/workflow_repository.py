from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EbookItem, WorkflowHistory

_ALLOWED = {
    "NEW": {"REVIEW", "HOLD", "ERROR"},
    "REVIEW": {"READY", "HOLD", "ERROR"},
    "READY": {"SCHEDULED", "HOLD", "ERROR"},
    "SCHEDULED": {"PUBLISHED", "HOLD", "ERROR"},
    "PUBLISHED": set(),
    "HOLD": {"REVIEW", "READY", "ERROR"},
    "ERROR": {"REVIEW", "HOLD"},
}


class WorkflowRepository:

    def __init__(self, session: Session):
        self.session = session

    def set_workflow_status(
        self,
        item: EbookItem,
        new_status: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> None:

        before = item.workflow_status

        if before == new_status:
            return

        allowed = _ALLOWED.get(before, set())

        if new_status not in allowed:
            raise ValueError(
                f"Illegal transition {before} -> {new_status}"
            )

        item.workflow_status = new_status
        item.last_checked_at = datetime.now(timezone.utc)

        self.session.add(
            WorkflowHistory(
                ebook_item=item,
                field_name="workflow_status",
                before_value=before,
                after_value=new_status,
                changed_by=changed_by,
                note=note,
            )
        )

        self.session.flush()
