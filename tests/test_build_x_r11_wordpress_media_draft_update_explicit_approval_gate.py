from __future__ import annotations

import pytest

from scripts.build_x_r11_wordpress_media_draft_update_explicit_approval_gate import (
    APPROVAL_LABEL,
    MediaDraftUpdateApprovalError,
    validate_approval_label,
    validate_draft_update_request,
    validate_media_request,
    validate_pending_checklist,
)


def pending_checklist() -> list[dict]:
    return [
        {
            "check_id": f"CHECK_{index}",
            "human_decision": "PENDING",
        }
        for index in range(10)
    ]


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        MediaDraftUpdateApprovalError,
        match="exactly equal",
    ):
        validate_approval_label(
            "APPROVED"
        )


def test_ten_pending_checks_pass() -> None:
    validate_pending_checklist(
        pending_checklist()
    )


def test_non_pending_check_fails() -> None:
    checklist = pending_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        MediaDraftUpdateApprovalError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_media_create_count_above_one_fails(
    tmp_path,
) -> None:
    binary = tmp_path / "cover.jpg"
    binary.write_bytes(b"test")

    with pytest.raises(
        MediaDraftUpdateApprovalError,
        match="must equal one",
    ):
        validate_media_request(
            {
                "api_method": "POST_ONCE",
                "resource": "/wp-json/wp/v2/media",
                "filename": (
                    "noa-senpai-wa-tomodachi-"
                    "11-cover.jpg"
                ),
                "content_type": "image/jpeg",
                "maximum_create_count": 2,
                "execution_allowed": False,
                "binary_path": str(binary),
            }
        )


def test_draft_update_publish_status_fails(
    tmp_path,
) -> None:
    preview = tmp_path / "preview.html"

    preview.write_text(
        "{{WORDPRESS_MEDIA_SOURCE_URL}}",
        encoding="utf-8",
    )

    with pytest.raises(
        MediaDraftUpdateApprovalError,
        match="status lock mismatch",
    ):
        validate_draft_update_request(
            {
                "api_method": "POST_ONCE",
                "resource": (
                    "/wp-json/wp/v2/posts/195"
                ),
                "post_status_must_remain": (
                    "publish"
                ),
                "original_content_sha256": (
                    "ae18a9116741fea0ea51bc105ed89a6c5"
                    "14bf512bc02d1d0c69f6998695aef5b"
                ),
                "media_source_url_placeholder": (
                    "{{WORDPRESS_MEDIA_SOURCE_URL}}"
                ),
                "placeholder_count": 1,
                "remote_source_url_removed": True,
                "execution_allowed": False,
                "content_preview_path": str(
                    preview
                ),
                "content_preview_sha256": (
                    "unused"
                ),
            }
        )
