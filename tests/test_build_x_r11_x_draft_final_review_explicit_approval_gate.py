from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_final_review_explicit_approval_gate import (
    APPROVAL_LABEL,
    EXPECTED_DRAFT_ID,
    EXPECTED_FINAL_TEXT,
    EXPECTED_LITERAL_CHARACTER_COUNT,
    EXPECTED_PUBLIC_URL,
    EXPECTED_TCO_CHARACTER_COUNT,
    EXPECTED_TEXT_SHA,
    XDraftFinalReviewApprovalError,
    validate_approval_label,
    validate_draft,
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


def valid_draft() -> dict:
    return {
        "draft_id": EXPECTED_DRAFT_ID,
        "revision": "PUBLIC_URL_BOUND_V1",
        "text": EXPECTED_FINAL_TEXT,
        "text_sha256": EXPECTED_TEXT_SHA,
        "literal_character_count": (
            EXPECTED_LITERAL_CHARACTER_COUNT
        ),
        "estimated_tco_character_count": (
            EXPECTED_TCO_CHARACTER_COUNT
        ),
        "public_url": EXPECTED_PUBLIC_URL,
        "public_url_count": 1,
        "public_url_placeholder_absent": True,
        "hashtags": [
            "#のあ先輩はともだち",
            "#コミック新刊",
        ],
    }


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        XDraftFinalReviewApprovalError,
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
        XDraftFinalReviewApprovalError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_valid_draft_passes() -> None:
    validate_draft(
        valid_draft()
    )


def test_wrong_draft_sha_fails() -> None:
    draft = valid_draft()

    draft["text_sha256"] = "0" * 64

    with pytest.raises(
        XDraftFinalReviewApprovalError,
        match="SHA mismatch",
    ):
        validate_draft(
            draft
        )
