from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import EbookItem, WorkflowHistory


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

    def set_wordpress_post_id(
        self,
        item: EbookItem,
        value: str | int | None,
        *,
        changed_by: str,
        note: str = "",
    ) -> bool:
        if isinstance(value, bool):
            raise ValueError(
                "wordpress_post_id must be a positive integer or None"
            )

        if value is None:
            normalized = None
        else:
            normalized = str(value).strip()

            if (
                not normalized
                or not normalized.isdigit()
                or int(normalized) <= 0
            ):
                raise ValueError(
                    "wordpress_post_id must be a positive integer or None"
                )

        self._validate_actor(changed_by)

        before = item.wordpress_post_id

        if before == normalized:
            return False

        now = _utc_now()

        item.wordpress_post_id = normalized
        item.last_checked_at = now
        item.wordpress_updated_at = now

        # wordpress_post_id is intentionally not written to
        # workflow_history because the production schema only permits
        # workflow fields such as wordpress_status.
        self.session.flush()

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
