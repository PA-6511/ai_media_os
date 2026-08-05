from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)


class XDraftReadRepositoryError(RuntimeError):
    """Raised when read-only X draft source retrieval fails."""


@dataclass(frozen=True)
class ApprovedWordPressDraftReadModel:
    approval_request_id: str
    approval_type: str
    approval_status: str
    decided_by: str | None
    decided_at: datetime | None

    ebook_item_id: str
    source_item_id: str
    title: str
    volume_label: str | None
    author_name: str | None
    release_date: date | None
    item_type: str
    is_excluded: bool

    workflow_status: str
    wordpress_status: str
    wordpress_post_id: str | None
    review_status: str


class XDraftReadRepository:
    """
    Read-only repository for X draft source data.

    This repository performs SELECT operations only. It does not
    add, update, delete, flush, commit, or mutate ORM objects.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def _assert_session_clean(self) -> None:
        if (
            self.session.new
            or self.session.dirty
            or self.session.deleted
        ):
            raise XDraftReadRepositoryError(
                "read-only session contains pending mutations"
            )

    def get_approved_wordpress_draft(
        self,
        approval_request_id: str,
    ) -> ApprovedWordPressDraftReadModel | None:
        normalized_id = approval_request_id.strip()

        if not normalized_id:
            raise XDraftReadRepositoryError(
                "approval_request_id must not be empty"
            )

        self._assert_session_clean()

        statement = (
            select(
                WorkflowApprovalRequest,
                EbookItem,
            )
            .join(
                EbookItem,
                WorkflowApprovalRequest.ebook_item_id
                == EbookItem.id,
            )
            .where(
                WorkflowApprovalRequest.id
                == normalized_id
            )
        )

        with self.session.no_autoflush:
            row = self.session.execute(
                statement
            ).one_or_none()

        self._assert_session_clean()

        if row is None:
            return None

        approval, item = row

        return ApprovedWordPressDraftReadModel(
            approval_request_id=approval.id,
            approval_type=approval.approval_type,
            approval_status=approval.status,
            decided_by=approval.decided_by,
            decided_at=approval.decided_at,
            ebook_item_id=item.id,
            source_item_id=item.source_item_id,
            title=item.title,
            volume_label=item.volume_label,
            author_name=item.author_name,
            release_date=item.release_date,
            item_type=item.item_type,
            is_excluded=item.is_excluded,
            workflow_status=item.workflow_status,
            wordpress_status=item.wordpress_status,
            wordpress_post_id=item.wordpress_post_id,
            review_status=item.review_status,
        )

    def find_latest_eligible_approval_ids(
        self,
        *,
        limit: int = 10,
    ) -> Sequence[str]:
        if limit < 1 or limit > 100:
            raise XDraftReadRepositoryError(
                "limit must be between 1 and 100"
            )

        self._assert_session_clean()

        statement = (
            select(WorkflowApprovalRequest.id)
            .join(
                EbookItem,
                WorkflowApprovalRequest.ebook_item_id
                == EbookItem.id,
            )
            .where(
                WorkflowApprovalRequest.status
                == "APPROVED",
                WorkflowApprovalRequest.approval_type
                == "REVIEW_READY",
                EbookItem.workflow_status == "READY",
                EbookItem.review_status == "APPROVED",
                EbookItem.wordpress_status == "DRAFT",
                EbookItem.wordpress_post_id.is_not(None),
                EbookItem.is_excluded.is_(False),
            )
            .order_by(
                WorkflowApprovalRequest.decided_at.desc(),
                WorkflowApprovalRequest.id.desc(),
            )
            .limit(limit)
        )

        with self.session.no_autoflush:
            identifiers = list(
                self.session.scalars(
                    statement
                ).all()
            )

        self._assert_session_clean()

        return identifiers
