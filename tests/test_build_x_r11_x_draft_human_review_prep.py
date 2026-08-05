from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_human_review_prep import (
    EXPECTED_DRAFT_TEXT,
    XDraftHumanReviewPrepError,
    build_review_checklist,
    validate_pending_checklist,
    validate_reviewable_draft_text,
)


def test_fixed_draft_text_passes() -> None:
    result = validate_reviewable_draft_text(
        EXPECTED_DRAFT_TEXT
    )

    assert result[
        "character_limit_passed"
    ] is True


def test_changed_draft_text_fails() -> None:
    changed = EXPECTED_DRAFT_TEXT.replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XDraftHumanReviewPrepError,
        match="differs from fixed text",
    ):
        validate_reviewable_draft_text(
            changed
        )


def test_eight_pending_checks_pass() -> None:
    validate_pending_checklist(
        build_review_checklist()
    )


def test_duplicate_check_id_fails() -> None:
    checklist = build_review_checklist()

    checklist[1]["check_id"] = (
        checklist[0]["check_id"]
    )

    with pytest.raises(
        XDraftHumanReviewPrepError,
        match="not unique",
    ):
        validate_pending_checklist(
            checklist
        )


def test_non_pending_decision_fails() -> None:
    checklist = build_review_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        XDraftHumanReviewPrepError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )
