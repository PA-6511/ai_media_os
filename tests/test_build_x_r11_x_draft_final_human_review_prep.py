from __future__ import annotations

import pytest

from scripts.build_x_r11_x_draft_final_human_review_prep import (
    EXPECTED_FINAL_TEXT,
    EXPECTED_FINAL_TEXT_SHA,
    EXPECTED_HASHTAGS,
    EXPECTED_LITERAL_CHARACTER_COUNT,
    EXPECTED_TCO_CHARACTER_COUNT,
    XDraftFinalHumanReviewError,
    build_review_checklist,
    estimate_tco_character_count,
    extract_hashtags,
    sha256_text,
    validate_final_text,
    validate_pending_checklist,
)


def test_valid_final_text_passes() -> None:
    result = validate_final_text(
        EXPECTED_FINAL_TEXT
    )

    assert result[
        "text_sha256"
    ] == EXPECTED_FINAL_TEXT_SHA

    assert result[
        "literal_character_count"
    ] == EXPECTED_LITERAL_CHARACTER_COUNT

    assert result[
        "estimated_tco_character_count"
    ] == EXPECTED_TCO_CHARACTER_COUNT


def test_changed_final_text_fails() -> None:
    changed = EXPECTED_FINAL_TEXT.replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XDraftFinalHumanReviewError,
        match="text mismatch",
    ):
        validate_final_text(
            changed
        )


def test_character_count_passes() -> None:
    assert len(
        EXPECTED_FINAL_TEXT
    ) == EXPECTED_LITERAL_CHARACTER_COUNT

    assert estimate_tco_character_count(
        EXPECTED_FINAL_TEXT
    ) == EXPECTED_TCO_CHARACTER_COUNT


def test_hashtags_pass() -> None:
    assert extract_hashtags(
        EXPECTED_FINAL_TEXT
    ) == EXPECTED_HASHTAGS


def test_ten_pending_checks_pass() -> None:
    validate_pending_checklist(
        build_review_checklist()
    )


def test_non_pending_check_fails() -> None:
    checklist = build_review_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        XDraftFinalHumanReviewError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )
