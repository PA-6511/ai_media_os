from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import EbookItem, WorkflowHistory



class WorkflowStateRepositoryError(ValueError):
    """Base fail-closed workflow-state repository error."""

    code = "WORKFLOW_STATE_REPOSITORY_ERROR"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.code)


class WordPressPostIdInvalidError(WorkflowStateRepositoryError):
    code = "WORDPRESS_POST_ID_INVALID"


class WordPressPostIdTooLongError(WorkflowStateRepositoryError):
    code = "WORDPRESS_POST_ID_TOO_LONG"


class WordPressPostIdItemNotPersistedError(
    WorkflowStateRepositoryError
):
    code = "WORDPRESS_POST_ID_ITEM_NOT_PERSISTED"


class WordPressPostIdRebindForbiddenError(
    WorkflowStateRepositoryError
):
    code = "WORDPRESS_POST_ID_REBIND_FORBIDDEN"


class WordPressPostIdAlreadyBoundError(
    WorkflowStateRepositoryError
):
    code = "WORDPRESS_POST_ID_ALREADY_BOUND"


class WordPressPostIdUniquenessConflictError(
    WorkflowStateRepositoryError
):
    code = "WORDPRESS_POST_ID_UNIQUENESS_CONFLICT"


_ALLOWED_VALUES = {
    "wordpress_status": {
        "NOT_CREATED",
        "DRAFT",
        "SCHEDULED",
        "PUBLISHED",
        "ERROR",
    },
    "x_status": {
        "NOT_CREATED",
        "DRAFT",
        "POSTED",
        "ERROR",
    },
    "affiliate_status": {
        "UNCHECKED",
        "MISSING",
        "READY",
        "REVIEW",
    },
    "image_status": {
        "UNCHECKED",
        "MISSING",
        "READY",
        "REVIEW",
    },
    "review_status": {
        "NOT_REVIEWED",
        "IN_REVIEW",
        "APPROVED",
        "REJECTED",
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _history_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


class WorkflowStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _validate_actor(changed_by: str) -> str:
        actor = (changed_by or "").strip()

        if not actor:
            raise ValueError("changed_by is required")

        return actor

    def _set_value(
        self,
        item: EbookItem,
        *,
        field_name: str,
        value: Any,
        changed_by: str,
        note: str = "",
    ) -> bool:
        actor = self._validate_actor(changed_by)
        before = getattr(item, field_name)

        if before == value:
            return False

        now = _utc_now()

        setattr(item, field_name, value)
        item.last_checked_at = now

        if field_name == "wordpress_status":
            item.wordpress_updated_at = now

        self.session.add(
            WorkflowHistory(
                ebook_item=item,
                field_name=field_name,
                before_value=_history_value(before),
                after_value=_history_value(value),
                changed_by=actor,
                note=note or None,
            )
        )

        self.session.flush()
        return True

    def _set_enum(
        self,
        item: EbookItem,
        *,
        field_name: str,
        value: str,
        changed_by: str,
        note: str = "",
    ) -> bool:
        normalized = (value or "").strip().upper()
        allowed = _ALLOWED_VALUES[field_name]

        if normalized not in allowed:
            raise ValueError(
                f"Invalid {field_name}: {normalized}"
            )

        return self._set_value(
            item,
            field_name=field_name,
            value=normalized,
            changed_by=changed_by,
            note=note,
        )

    def set_wordpress_status(
        self,
        item: EbookItem,
        value: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        return self._set_enum(
            item,
            field_name="wordpress_status",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    @staticmethod
    def _normalize_wordpress_post_id(
        value: str | int,
    ) -> str:
        invalid_message = (
            "wordpress_post_id must be a positive integer "
            "with 1 to 20 ASCII digits and no leading zero"
        )

        if isinstance(value, bool):
            raise WordPressPostIdInvalidError(invalid_message)

        if isinstance(value, int):
            if value <= 0:
                raise WordPressPostIdInvalidError(
                    invalid_message
                )

            normalized = str(value)
        elif isinstance(value, str):
            normalized = value

            if (
                not normalized
                or not normalized.isascii()
                or not normalized.isdigit()
                or normalized.startswith("0")
            ):
                raise WordPressPostIdInvalidError(
                    invalid_message
                )
        else:
            raise WordPressPostIdInvalidError(
                invalid_message
            )

        if len(normalized) > 20:
            raise WordPressPostIdTooLongError(
                "wordpress_post_id must be a positive integer "
                "with at most 20 ASCII digits"
            )

        return normalized

    def set_wordpress_post_id(
        self,
        item: EbookItem,
        value: str | int | None,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        self._validate_actor(changed_by)

        before = getattr(
            item,
            "wordpress_post_id",
            None,
        )

        if value is None:
            if before is None:
                return False

            raise WordPressPostIdRebindForbiddenError(
                "Existing WordPress post ID cannot be cleared "
                "through the ordinary workflow path"
            )

        # Input validation must happen before item identity or
        # session access so invalid values always fail closed
        # with the fixed domain error.
        normalized = self._normalize_wordpress_post_id(
            value
        )

        if before == normalized:
            return False

        if before is not None:
            raise WordPressPostIdRebindForbiddenError(
                "Existing WordPress post ID cannot be replaced "
                "through the ordinary workflow path"
            )

        item_id = getattr(item, "id", None)

        if not isinstance(item_id, str) or not item_id:
            raise WordPressPostIdItemNotPersistedError(
                "A persisted ebook item ID is required "
                "before binding a WordPress post ID"
            )

        session = getattr(self, "session", None)

        if session is None:
            raise WordPressPostIdItemNotPersistedError(
                "A database session is required before binding "
                "a WordPress post ID"
            )

        with session.no_autoflush:
            conflict_id = session.scalar(
                select(EbookItem.id)
                .where(
                    EbookItem.wordpress_post_id
                    == normalized,
                    EbookItem.id != item_id,
                )
                .limit(1)
            )

        if conflict_id is not None:
            raise WordPressPostIdAlreadyBoundError(
                "WordPress post ID is already bound "
                "to another ebook workflow"
            )

        now = _utc_now()
        item.wordpress_post_id = normalized
        item.last_checked_at = now
        item.wordpress_updated_at = now

        try:
            # Transaction ownership remains with the caller.
            # The caller must rollback after a failed flush.
            session.flush()
        except IntegrityError as exc:
            raise WordPressPostIdUniquenessConflictError(
                "WordPress post ID uniqueness conflict"
            ) from exc

        return True

    def mark_wordpress_draft_created(
        self,
        item: EbookItem,
        post_id: str | int,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        post_id_changed = self.set_wordpress_post_id(
            item,
            post_id,
            changed_by=changed_by,
            note=note,
        )

        status_changed = self.set_wordpress_status(
            item,
            "DRAFT",
            changed_by=changed_by,
            note=note,
        )

        return post_id_changed or status_changed
    def set_x_status(
        self,
        item: EbookItem,
        value: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        return self._set_enum(
            item,
            field_name="x_status",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    def set_affiliate_status(
        self,
        item: EbookItem,
        value: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        return self._set_enum(
            item,
            field_name="affiliate_status",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    def set_image_status(
        self,
        item: EbookItem,
        value: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        return self._set_enum(
            item,
            field_name="image_status",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    def set_review_status(
        self,
        item: EbookItem,
        value: str,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        return self._set_enum(
            item,
            field_name="review_status",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    def start_review(
        self,
        item: EbookItem,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        if item.workflow_status != "NEW" or item.review_status != "NOT_REVIEWED":
            raise ValueError(
                "Review can start only from NEW + NOT_REVIEWED"
            )
        workflow_changed = self._set_value(
            item,
            field_name="workflow_status",
            value="REVIEW",
            changed_by=changed_by,
            note=note,
        )
        review_changed = self.set_review_status(
            item,
            "IN_REVIEW",
            changed_by=changed_by,
            note=note,
        )
        return workflow_changed or review_changed

    def repair_ready_not_reviewed(
        self,
        item: EbookItem,
        *,
        changed_by: str,
        note: str,
    ) -> bool:
        if item.workflow_status != "READY" or item.review_status != "NOT_REVIEWED":
            raise ValueError(
                "Repair requires READY + NOT_REVIEWED"
            )
        return self._set_value(
            item,
            field_name="workflow_status",
            value="NEW",
            changed_by=changed_by,
            note=note,
        )

    def reset_for_metadata_review(
        self,
        item: EbookItem,
        *,
        changed_by: str,
        note: str,
    ) -> bool:
        if item.workflow_status not in {"NEW", "REVIEW", "READY"}:
            raise ValueError(
                "Metadata review reset requires NEW, REVIEW, or READY"
            )
        review_changed = self.set_review_status(
            item,
            "NOT_REVIEWED",
            changed_by=changed_by,
            note=note,
        )
        workflow_changed = self._set_value(
            item,
            field_name="workflow_status",
            value="NEW",
            changed_by=changed_by,
            note=note,
        )
        return review_changed or workflow_changed

    def set_publish_ready(
        self,
        item: EbookItem,
        value: bool,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        if not isinstance(value, bool):
            raise ValueError("publish_ready must be boolean")

        return self._set_value(
            item,
            field_name="publish_ready",
            value=value,
            changed_by=changed_by,
            note=note,
        )

    def set_last_error(
        self,
        item: EbookItem,
        value: str | None,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        normalized = None if value is None else str(value)

        return self._set_value(
            item,
            field_name="last_error",
            value=normalized,
            changed_by=changed_by,
            note=note,
        )
