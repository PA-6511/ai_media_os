from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.db.models import EbookItem
from app.db.repositories.workflow_repository import WorkflowRepository


_GUI_TARGETS = frozenset(
    {
        "REVIEW",
        "READY",
        "SCHEDULED",
        "PUBLISHED",
    }
)

_WORKFLOW_ACTION_TOKEN = secrets.token_urlsafe(32)


class WorkflowActionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WorkflowActionResult:
    item_id: str
    before_status: str
    after_status: str


def get_workflow_action_token() -> str:
    return _WORKFLOW_ACTION_TOKEN


def safe_database_return_path(value: str | None) -> str:
    raw = (value or "").strip()

    if not raw:
        return "/database-search"

    parsed = urlsplit(raw)

    if parsed.scheme or parsed.netloc:
        return "/database-search"

    if parsed.path not in {
        "/database-search",
        "/affiliate-settings",
        "/supplement-import",
    }:
        return "/database-search"

    return urlunsplit(
        (
            "",
            "",
            parsed.path,
            parsed.query,
            "",
        )
    )


def execute_workflow_action(
    session: Session,
    *,
    item_id: str,
    new_status: str,
    csrf_token: str,
    changed_by: str = "human:local_gui",
    note: str = "Updated from local database GUI",
) -> WorkflowActionResult:
    if not hmac.compare_digest(
        csrf_token or "",
        get_workflow_action_token(),
    ):
        raise WorkflowActionError(
            "invalid_token",
            "Workflow action token is invalid.",
        )

    normalized_item_id = (item_id or "").strip()
    normalized_status = (new_status or "").strip().upper()
    normalized_changed_by = (changed_by or "").strip()

    if not normalized_item_id:
        raise WorkflowActionError(
            "invalid_request",
            "ebook item id is required.",
        )

    if normalized_status not in _GUI_TARGETS:
        raise WorkflowActionError(
            "invalid_target",
            "Workflow target is not allowed from the GUI.",
        )

    if not normalized_changed_by:
        raise WorkflowActionError(
            "invalid_request",
            "changed_by is required.",
        )

    item = session.get(EbookItem, normalized_item_id)

    if item is None:
        raise WorkflowActionError(
            "item_not_found",
            "ebook item was not found.",
        )

    before_status = item.workflow_status

    if (
        before_status == "REVIEW"
        and normalized_status == "READY"
    ):
        raise WorkflowActionError(
            "REVIEW_READY_REQUIRES_APPROVAL",
            (
                "REVIEW_READY_REQUIRES_APPROVAL: "
                "Use the formal approval workflow."
            ),
        )

    try:
        WorkflowRepository(session).set_workflow_status(
            item,
            normalized_status,
            changed_by=normalized_changed_by,
            note=note,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        raise WorkflowActionError(
            "invalid_transition",
            "The requested workflow transition is not allowed.",
        ) from exc
    except Exception as exc:
        session.rollback()
        raise WorkflowActionError(
            "internal_error",
            "The workflow update could not be completed.",
        ) from exc

    return WorkflowActionResult(
        item_id=item.id,
        before_status=before_status,
        after_status=item.workflow_status,
    )
