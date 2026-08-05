from __future__ import annotations

import pytest

from scripts.build_x_r11_wordpress_publication_explicit_approval_gate import (
    APPROVAL_LABEL,
    PublicationApprovalGateError,
    validate_approval_label,
    validate_pending_checklist,
    validate_publication_preview,
)


def pending_checklist() -> list[dict]:
    return [
        {
            "check_id": f"CHECK_{index}",
            "human_decision": "PENDING",
        }
        for index in range(12)
    ]


def valid_publication_preview() -> dict:
    return {
        "request_id": (
            "xr11-wp-publish-"
            "48ca178ad9af187afa505ac4"
        ),
        "api_method": "POST_ONCE",
        "resource": "/wp-json/wp/v2/posts/195",
        "payload": {
            "status": "publish",
        },
        "target_post_id": 195,
        "maximum_update_count": 1,
        "required_pre_execution_status": "draft",
        "required_post_execution_status": "publish",
        "content_change_allowed": False,
        "title_change_allowed": False,
        "slug_change_allowed": False,
        "category_change_allowed": False,
        "media_change_allowed": False,
        "publication_only": True,
        "execution_allowed": False,
    }


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        PublicationApprovalGateError,
        match="exactly equal",
    ):
        validate_approval_label(
            "APPROVED"
        )


def test_twelve_pending_checks_pass() -> None:
    validate_pending_checklist(
        pending_checklist()
    )


def test_non_pending_check_fails() -> None:
    checklist = pending_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        PublicationApprovalGateError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_publication_preview_passes() -> None:
    validate_publication_preview(
        valid_publication_preview()
    )


def test_publication_preview_content_change_fails() -> None:
    preview = valid_publication_preview()

    preview[
        "content_change_allowed"
    ] = True

    with pytest.raises(
        PublicationApprovalGateError,
        match="unexpected change",
    ):
        validate_publication_preview(
            preview
        )
