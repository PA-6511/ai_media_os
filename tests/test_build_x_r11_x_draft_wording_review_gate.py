from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_wording_review_gate import (
    APPROVAL_LABEL,
    EXPECTED_DRAFT_ID,
    EXPECTED_DRAFT_TEXT,
    EXPECTED_DRAFT_TEXT_SHA,
    XDraftWordingGateError,
    validate_approval_label,
    validate_fixed_draft,
    validate_pending_checklist,
)


def pending_checklist() -> list[dict]:
    return [
        {
            "check_id": f"CHECK_{index}",
            "human_decision": "PENDING",
        }
        for index in range(8)
    ]


def valid_draft() -> dict:
    return {
        "draft_id": EXPECTED_DRAFT_ID,
        "text": EXPECTED_DRAFT_TEXT,
        "text_sha256": EXPECTED_DRAFT_TEXT_SHA,
    }


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        XDraftWordingGateError,
        match="exactly equal",
    ):
        validate_approval_label(
            "APPROVED"
        )


def test_eight_pending_checks_pass() -> None:
    validate_pending_checklist(
        pending_checklist()
    )


def test_non_pending_check_fails() -> None:
    checklist = pending_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        XDraftWordingGateError,
        match="pending state",
    ):
        validate_pending_checklist(
            checklist
        )


def test_fixed_draft_passes() -> None:
    validate_fixed_draft(
        valid_draft()
    )


def test_changed_draft_fails() -> None:
    draft = valid_draft()

    draft["text"] = draft[
        "text"
    ].replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XDraftWordingGateError,
        match="differs from fixed wording",
    ):
        validate_fixed_draft(
            draft
        )
