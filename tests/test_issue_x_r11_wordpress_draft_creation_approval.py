from __future__ import annotations

import pytest

from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)
from scripts.issue_x_r11_wordpress_draft_creation_approval import (
    APPROVAL_LABEL,
    CreationApprovalError,
    validate_approval_label,
    verify_final_gate,
)


DIGEST_FIELD = (
    "wordpress_draft_final_gate_digest_sha256"
)


def valid_final_gate() -> dict:
    return {
        "status": (
            "PASS_WORDPRESS_DRAFT_FINAL_GATE_"
            "READY_AWAITING_EXPLICIT_"
            "CREATION_APPROVAL"
        ),
        "final_gate_state": (
            "READY_AWAITING_EXPLICIT_"
            "WORDPRESS_DRAFT_CREATION_APPROVAL"
        ),
        "creation_request_id": (
            "xr11-wp-draft-create-"
            "baf4e4451e14b3b4b3984bd2"
        ),
        "next_approval_label": APPROVAL_LABEL,
        "next_approval_scope": (
            "WORDPRESS_DRAFT_CREATION_ONLY"
        ),
        "next_approval_issued": False,
        "next_approval_consumed": False,
        "draft_creation_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "wordpress_draft_request": {
            "title": (
                "のあ先輩はともだち。 "
                "第11巻｜配信開始"
            ),
            "slug": (
                "noa-senpai-wa-tomodachi-"
                "11-6ffa7a8d"
            ),
            "status": "draft",
            "category_ids": [43],
            "maximum_create_count": 1,
            "expected_api_method": "POST_ONCE",
        },
    }


def seal_final_gate(
    value: dict,
) -> str:
    payload = {
        key: item
        for key, item in value.items()
        if key != DIGEST_FIELD
    }

    digest = canonical_digest(payload)
    value[DIGEST_FIELD] = digest

    return digest


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        CreationApprovalError,
        match="exactly equal",
    ):
        validate_approval_label(
            "APPROVED"
        )


def test_invalid_request_status_fails() -> None:
    value = valid_final_gate()

    value[
        "wordpress_draft_request"
    ]["status"] = "publish"

    digest = seal_final_gate(value)

    with pytest.raises(
        CreationApprovalError,
        match="must equal draft",
    ):
        verify_final_gate(
            value,
            expected_digest=digest,
        )


def test_create_count_above_one_fails() -> None:
    value = valid_final_gate()

    value[
        "wordpress_draft_request"
    ]["maximum_create_count"] = 2

    digest = seal_final_gate(value)

    with pytest.raises(
        CreationApprovalError,
        match="must equal one",
    ):
        verify_final_gate(
            value,
            expected_digest=digest,
        )
