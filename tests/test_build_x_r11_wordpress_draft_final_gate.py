from __future__ import annotations

import pytest

from scripts.build_x_r11_wordpress_draft_final_gate import (
    EXPECTED_REVIEW_APPROVAL_LABEL,
    FinalGateError,
    validate_approval_label,
    validate_pending_checklist,
)


def pending_checklist() -> list[dict]:
    return [
        {
            "check_id": f"CHECK_{index}",
            "description": "review item",
            "human_decision": "PENDING",
        }
        for index in range(8)
    ]


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        EXPECTED_REVIEW_APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        FinalGateError,
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
        FinalGateError,
        match="original pending state",
    ):
        validate_pending_checklist(
            checklist
        )
