from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from app.services.approved_wordpress_draft_x_input_adapter import (
    ApprovedWordPressDraftAdapterError,
    ApprovedWordPressDraftSnapshot,
    ApprovedWordPressDraftXInputAdapter,
)


def valid_snapshot(
    **overrides: object,
) -> ApprovedWordPressDraftSnapshot:
    values = {
        "approval_request_id": (
            "approval-x-r5-001"
        ),
        "approval_status": "APPROVED",
        "approval_scope": (
            "X_DRAFT_GENERATION"
        ),
        "approved_by": "human-reviewer",
        "approved_at": (
            "2026-07-17T20:30:00+09:00"
        ),
        "ebook_item_id": "x-r5-item-001",
        "title": "X-R5 テスト作品",
        "volume_label": "第1巻",
        "release_date": "2026-07-17",
        "category": "コミック新刊",
        "author_name": "山田 太郎",
        "article_url": (
            "https://books.example.jp/posts/"
            "x-r5-item-001"
        ),
        "wordpress_draft_id": 50001,
        "wordpress_status": "DRAFT",
    }
    values.update(overrides)

    return ApprovedWordPressDraftSnapshot(
        **values
    )


def test_approved_snapshot_is_adapted() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    result = adapter.adapt(
        valid_snapshot()
    )

    assert result.status == (
        "PASS_APPROVED_WORDPRESS_DRAFT_ADAPTER"
    )
    assert result.approval_status == (
        "APPROVED"
    )
    assert result.approval_scope == (
        "X_DRAFT_GENERATION"
    )
    assert len(result.source_digest_sha256) == 64

    draft = result.x_draft_input

    assert draft.ebook_item_id == (
        "x-r5-item-001"
    )
    assert draft.wordpress_draft_id == 50001
    assert draft.wordpress_status == "DRAFT"
    assert draft.release_date == "2026-07-17"
    assert draft.category == "コミック新刊"


def test_nfkc_normalization_is_applied() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    result = adapter.adapt(
        valid_snapshot(
            title=" Ｘ－Ｒ５ テスト作品 ",
            volume_label=" 第１巻 ",
            author_name=" 山田　太郎 ",
        )
    )

    draft = result.x_draft_input

    assert draft.title == "X-R5 テスト作品"
    assert draft.volume_label == "第1巻"
    assert draft.author_name == "山田 太郎"


@pytest.mark.parametrize(
    "approval_status",
    [
        "PENDING",
        "REJECTED",
        "CANCELLED",
        "UNREVIEWED",
    ],
)
def test_non_approved_status_is_rejected(
    approval_status: str,
) -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match=(
            "approval_status must be APPROVED"
        ),
    ):
        adapter.adapt(
            valid_snapshot(
                approval_status=approval_status
            )
        )


def test_wrong_approval_scope_is_rejected() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match=(
            "approval_scope must be "
            "X_DRAFT_GENERATION"
        ),
    ):
        adapter.adapt(
            valid_snapshot(
                approval_scope=(
                    "WORDPRESS_PUBLISH"
                )
            )
        )


def test_empty_approver_is_rejected() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match="approved_by must not be empty",
    ):
        adapter.adapt(
            valid_snapshot(
                approved_by="",
            )
        )


@pytest.mark.parametrize(
    "approved_at",
    [
        "2026-07-17",
        "2026-07-17T20:30:00",
        "not-a-date",
    ],
)
def test_invalid_approved_at_is_rejected(
    approved_at: str,
) -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match="approved_at",
    ):
        adapter.adapt(
            valid_snapshot(
                approved_at=approved_at
            )
        )


def test_non_draft_wordpress_status_is_rejected() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match=(
            "wordpress_status must be DRAFT"
        ),
    ):
        adapter.adapt(
            valid_snapshot(
                wordpress_status="PUBLISHED"
            )
        )


@pytest.mark.parametrize(
    "wordpress_draft_id",
    [
        0,
        -1,
        True,
        "50001",
    ],
)
def test_invalid_wordpress_draft_id_is_rejected(
    wordpress_draft_id: object,
) -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    with pytest.raises(
        ApprovedWordPressDraftAdapterError,
        match="wordpress_draft_id",
    ):
        adapter.adapt(
            valid_snapshot(
                wordpress_draft_id=(
                    wordpress_draft_id
                )
            )
        )


def test_source_digest_is_deterministic() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )

    first = adapter.adapt(
        valid_snapshot()
    )
    second = adapter.adapt(
        valid_snapshot()
    )

    assert (
        first.source_digest_sha256
        == second.source_digest_sha256
    )


def test_result_is_frozen() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )
    result = adapter.adapt(
        valid_snapshot()
    )

    with pytest.raises(FrozenInstanceError):
        result.approval_status = (  # type: ignore[misc]
            "REJECTED"
        )


def test_result_is_json_serializable() -> None:
    adapter = (
        ApprovedWordPressDraftXInputAdapter()
    )
    result = adapter.adapt(
        valid_snapshot()
    )

    serialized = json.dumps(
        result.to_dict(),
        ensure_ascii=False,
    )

    assert (
        "PASS_APPROVED_WORDPRESS_DRAFT_ADAPTER"
        in serialized
    )
    assert "X-R5 テスト作品" in serialized
    assert "X_DRAFT_GENERATION" in serialized
