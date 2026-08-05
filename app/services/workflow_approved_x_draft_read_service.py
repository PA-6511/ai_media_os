from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.db.repositories.x_draft_read_repository import (
    ApprovedWordPressDraftReadModel,
    XDraftReadRepository,
)
from app.services.approved_wordpress_draft_x_input_adapter import (
    ApprovedWordPressDraftAdapterResult,
    ApprovedWordPressDraftSnapshot,
    ApprovedWordPressDraftXInputAdapter,
)


SOURCE_APPROVAL_TYPE = "REVIEW_READY"
TARGET_APPROVAL_SCOPE = "X_DRAFT_GENERATION"

CATEGORY_BY_ITEM_TYPE = {
    "tankobon": "コミック新刊",
    "light_novel": "ライトノベル新刊",
    "general_book": "一般書籍新刊",
}


class WorkflowApprovedXDraftReadError(ValueError):
    """Raised when DB data is not eligible for X draft generation."""


@dataclass(frozen=True)
class WorkflowApprovedXDraftReadResult:
    status: str
    source_approval_type: str
    mapped_approval_scope: str
    article_url_source: str
    read_model: ApprovedWordPressDraftReadModel
    adapter_result: ApprovedWordPressDraftAdapterResult

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WorkflowApprovedXDraftReadError(message)


def normalize_database_datetime(
    value: datetime | None,
    field_name: str,
) -> str:
    require(
        value is not None,
        f"{field_name} must not be null",
    )

    normalized = value

    # SQLite may return a naive datetime even when timezone=True.
    if normalized.tzinfo is None:
        normalized = normalized.replace(
            tzinfo=timezone.utc
        )

    return normalized.isoformat()


def normalize_wordpress_base_url(
    value: str,
) -> str:
    require(
        isinstance(value, str),
        "wordpress_base_url must be a string",
    )

    normalized = value.strip().rstrip("/")
    parsed = urlparse(normalized)

    require(
        parsed.scheme.lower() == "https",
        "wordpress_base_url must use https",
    )
    require(
        bool(parsed.hostname),
        "wordpress_base_url must contain a hostname",
    )
    require(
        parsed.username is None
        and parsed.password is None,
        (
            "wordpress_base_url must not contain "
            "credentials"
        ),
    )

    return normalized


def normalize_wordpress_post_id(
    value: int | str,
) -> int:
    require(
        not isinstance(value, bool),
        "wordpress_post_id must be a positive integer",
    )

    if isinstance(value, int):
        normalized = value
    elif isinstance(value, str):
        raw = value.strip()

        require(
            bool(raw),
            "wordpress_post_id must not be empty",
        )
        require(
            raw.isdecimal(),
            (
                "wordpress_post_id must contain "
                "decimal digits only"
            ),
        )

        normalized = int(raw)
    else:
        raise WorkflowApprovedXDraftReadError(
            "wordpress_post_id must be a positive integer"
        )

    require(
        normalized >= 1,
        "wordpress_post_id must be at least 1",
    )

    return normalized


def build_wordpress_article_url(
    *,
    wordpress_base_url: str,
    wordpress_post_id: int | str,
) -> str:
    base_url = normalize_wordpress_base_url(
        wordpress_base_url
    )
    normalized_post_id = (
        normalize_wordpress_post_id(
            wordpress_post_id
        )
    )

    return (
        f"{base_url}/?p={normalized_post_id}"
    )


class WorkflowApprovedXDraftReadService:
    """
    Reads an approved Workflow request and WP draft from a
    read-only repository, then passes it to the X-R5 adapter.

    No database write, Workflow mutation, WordPress API call,
    X-FB write, X API call, or X post is performed.
    """

    def __init__(
        self,
        session: Session,
        *,
        wordpress_base_url: str,
        adapter: (
            ApprovedWordPressDraftXInputAdapter
            | None
        ) = None,
    ) -> None:
        self.repository = XDraftReadRepository(
            session
        )
        self.wordpress_base_url = (
            normalize_wordpress_base_url(
                wordpress_base_url
            )
        )
        self.adapter = (
            adapter
            or ApprovedWordPressDraftXInputAdapter()
        )

    def find_latest_candidate_ids(
        self,
        *,
        limit: int = 10,
    ) -> list[str]:
        return list(
            self.repository
            .find_latest_eligible_approval_ids(
                limit=limit
            )
        )

    def read_and_adapt(
        self,
        approval_request_id: str,
    ) -> WorkflowApprovedXDraftReadResult:
        source = (
            self.repository
            .get_approved_wordpress_draft(
                approval_request_id
            )
        )

        require(
            source is not None,
            "approval request was not found",
        )

        require(
            source.approval_status == "APPROVED",
            "approval status must be APPROVED",
        )
        require(
            source.approval_type
            == SOURCE_APPROVAL_TYPE,
            (
                "approval type must be "
                "REVIEW_READY"
            ),
        )
        require(
            source.workflow_status == "READY",
            "workflow status must be READY",
        )
        require(
            source.review_status == "APPROVED",
            "review status must be APPROVED",
        )
        require(
            source.wordpress_status == "DRAFT",
            "wordpress status must be DRAFT",
        )
        require(
            source.wordpress_post_id is not None,
            "wordpress_post_id must not be null",
        )
        require(
            not source.is_excluded,
            "excluded ebook item is forbidden",
        )
        require(
            source.item_type
            in CATEGORY_BY_ITEM_TYPE,
            (
                "unsupported item_type for X draft: "
                f"{source.item_type}"
            ),
        )
        require(
            source.volume_label is not None
            and bool(source.volume_label.strip()),
            "volume_label must not be empty",
        )
        require(
            source.author_name is not None
            and bool(source.author_name.strip()),
            "author_name must not be empty",
        )
        require(
            source.release_date is not None,
            "release_date must not be null",
        )
        require(
            source.decided_by is not None
            and bool(source.decided_by.strip()),
            "decided_by must not be empty",
        )

        wordpress_post_id = (
            normalize_wordpress_post_id(
                source.wordpress_post_id
            )
        )

        article_url = build_wordpress_article_url(
            wordpress_base_url=(
                self.wordpress_base_url
            ),
            wordpress_post_id=(
                wordpress_post_id
            ),
        )

        adapter_result = self.adapter.adapt(
            ApprovedWordPressDraftSnapshot(
                approval_request_id=(
                    source.approval_request_id
                ),
                approval_status=(
                    source.approval_status
                ),
                approval_scope=(
                    TARGET_APPROVAL_SCOPE
                ),
                approved_by=source.decided_by,
                approved_at=(
                    normalize_database_datetime(
                        source.decided_at,
                        "decided_at",
                    )
                ),
                ebook_item_id=(
                    source.source_item_id
                ),
                title=source.title,
                volume_label=(
                    source.volume_label
                ),
                release_date=(
                    source.release_date.isoformat()
                ),
                category=(
                    CATEGORY_BY_ITEM_TYPE[
                        source.item_type
                    ]
                ),
                author_name=source.author_name,
                article_url=article_url,
                wordpress_draft_id=(
                    wordpress_post_id
                ),
                wordpress_status=(
                    source.wordpress_status
                ),
            )
        )

        return WorkflowApprovedXDraftReadResult(
            status=(
                "PASS_READ_ONLY_WORKFLOW_TO_X_ADAPTER"
            ),
            source_approval_type=(
                source.approval_type
            ),
            mapped_approval_scope=(
                TARGET_APPROVAL_SCOPE
            ),
            article_url_source=(
                "WORDPRESS_BASE_URL_PLUS_POST_ID"
            ),
            read_model=source,
            adapter_result=adapter_result,
        )
