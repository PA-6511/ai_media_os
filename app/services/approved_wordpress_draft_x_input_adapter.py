from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.x_draft_generation_service import (
    DEFAULT_CONTRACT_PATH,
    XDraftInput,
    load_contract,
    validate_input,
)


APPROVED_STATUS = "APPROVED"
X_DRAFT_APPROVAL_SCOPE = "X_DRAFT_GENERATION"


class ApprovedWordPressDraftAdapterError(ValueError):
    """Raised when an approved WP draft cannot become XDraftInput."""


@dataclass(frozen=True)
class ApprovedWordPressDraftSnapshot:
    """
    Normalized boundary object supplied by an upstream repository.

    This adapter does not query a database or modify workflow state.
    """

    approval_request_id: str
    approval_status: str
    approval_scope: str
    approved_by: str
    approved_at: str

    ebook_item_id: str
    title: str
    volume_label: str
    release_date: str
    category: str
    author_name: str
    article_url: str

    wordpress_draft_id: int
    wordpress_status: str


@dataclass(frozen=True)
class ApprovedWordPressDraftAdapterResult:
    status: str
    approval_request_id: str
    approval_status: str
    approval_scope: str
    approved_by: str
    approved_at: str
    source_digest_sha256: str
    x_draft_input: XDraftInput

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApprovedWordPressDraftAdapterError(message)


def normalize_text(value: str, field_name: str) -> str:
    require(
        isinstance(value, str),
        f"{field_name} must be a string",
    )

    normalized = unicodedata.normalize(
        "NFKC",
        value,
    ).strip()

    require(
        bool(normalized),
        f"{field_name} must not be empty",
    )

    return normalized


def normalize_approved_at(value: str) -> str:
    normalized = normalize_text(
        value,
        "approved_at",
    )

    parse_value = (
        normalized[:-1] + "+00:00"
        if normalized.endswith("Z")
        else normalized
    )

    try:
        parsed = datetime.fromisoformat(
            parse_value
        )
    except ValueError as exc:
        raise ApprovedWordPressDraftAdapterError(
            "approved_at must be an ISO-8601 datetime"
        ) from exc

    require(
        parsed.tzinfo is not None
        and parsed.utcoffset() is not None,
        "approved_at must include timezone",
    )

    return parsed.isoformat()


def build_source_digest(
    *,
    approval_request_id: str,
    approval_status: str,
    approval_scope: str,
    approved_by: str,
    approved_at: str,
    x_draft_input: XDraftInput,
) -> str:
    payload = {
        "approval_request_id": (
            approval_request_id
        ),
        "approval_status": approval_status,
        "approval_scope": approval_scope,
        "approved_by": approved_by,
        "approved_at": approved_at,
        "x_draft_input": asdict(x_draft_input),
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


class ApprovedWordPressDraftXInputAdapter:
    """
    Converts an explicitly approved WP draft snapshot into XDraftInput.

    No database access, workflow mutation, file write, WordPress write,
    X API call, or external API call is performed.
    """

    def __init__(
        self,
        *,
        contract_path: Path = DEFAULT_CONTRACT_PATH,
    ) -> None:
        self.contract = load_contract(
            contract_path
        )

    def adapt(
        self,
        snapshot: ApprovedWordPressDraftSnapshot,
    ) -> ApprovedWordPressDraftAdapterResult:
        require(
            isinstance(
                snapshot,
                ApprovedWordPressDraftSnapshot,
            ),
            (
                "snapshot must be "
                "ApprovedWordPressDraftSnapshot"
            ),
        )

        approval_request_id = normalize_text(
            snapshot.approval_request_id,
            "approval_request_id",
        )
        approval_status = normalize_text(
            snapshot.approval_status,
            "approval_status",
        ).upper()
        approval_scope = normalize_text(
            snapshot.approval_scope,
            "approval_scope",
        ).upper()
        approved_by = normalize_text(
            snapshot.approved_by,
            "approved_by",
        )
        approved_at = normalize_approved_at(
            snapshot.approved_at
        )

        require(
            approval_status == APPROVED_STATUS,
            "approval_status must be APPROVED",
        )
        require(
            approval_scope
            == X_DRAFT_APPROVAL_SCOPE,
            (
                "approval_scope must be "
                "X_DRAFT_GENERATION"
            ),
        )

        draft_input = XDraftInput(
            ebook_item_id=normalize_text(
                snapshot.ebook_item_id,
                "ebook_item_id",
            ),
            title=normalize_text(
                snapshot.title,
                "title",
            ),
            volume_label=normalize_text(
                snapshot.volume_label,
                "volume_label",
            ),
            release_date=normalize_text(
                snapshot.release_date,
                "release_date",
            ),
            category=normalize_text(
                snapshot.category,
                "category",
            ),
            author_name=normalize_text(
                snapshot.author_name,
                "author_name",
            ),
            article_url=normalize_text(
                snapshot.article_url,
                "article_url",
            ),
            wordpress_draft_id=(
                snapshot.wordpress_draft_id
            ),
            wordpress_status=normalize_text(
                snapshot.wordpress_status,
                "wordpress_status",
            ),
        )

        try:
            validated_input = validate_input(
                draft_input,
                self.contract,
            )
        except Exception as exc:
            raise ApprovedWordPressDraftAdapterError(
                "XDraftInput validation failed: "
                f"{exc}"
            ) from exc

        digest = build_source_digest(
            approval_request_id=(
                approval_request_id
            ),
            approval_status=approval_status,
            approval_scope=approval_scope,
            approved_by=approved_by,
            approved_at=approved_at,
            x_draft_input=validated_input,
        )

        return ApprovedWordPressDraftAdapterResult(
            status=(
                "PASS_APPROVED_WORDPRESS_DRAFT_ADAPTER"
            ),
            approval_request_id=(
                approval_request_id
            ),
            approval_status=approval_status,
            approval_scope=approval_scope,
            approved_by=approved_by,
            approved_at=approved_at,
            source_digest_sha256=digest,
            x_draft_input=validated_input,
        )
