from __future__ import annotations

import pytest

from scripts.build_x_r11_x_manual_posting_readiness_prep import (
    EXPECTED_CHECK_COUNT,
    EXPECTED_FINAL_TEXT,
    EXPECTED_TEXT_SHA,
    XManualPostingReadinessError,
    build_checklist,
    build_evidence_template,
    validate_finalized_text,
    validate_pending_checklist,
    validate_pending_evidence_template,
)


def test_finalized_text_passes() -> None:
    validate_finalized_text(
        EXPECTED_FINAL_TEXT
    )


def test_changed_finalized_text_fails() -> None:
    changed = EXPECTED_FINAL_TEXT.replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XManualPostingReadinessError,
        match="text mismatch",
    ):
        validate_finalized_text(
            changed
        )


def test_twelve_pending_checks_pass() -> None:
    checklist = build_checklist()

    assert len(checklist) == (
        EXPECTED_CHECK_COUNT
    )

    validate_pending_checklist(
        checklist
    )


def test_non_pending_check_fails() -> None:
    checklist = build_checklist()

    checklist[0][
        "human_decision"
    ] = "APPROVED"

    with pytest.raises(
        XManualPostingReadinessError,
        match="remain pending",
    ):
        validate_pending_checklist(
            checklist
        )


def test_pending_evidence_template_passes() -> None:
    template = build_evidence_template()

    assert template[
        "expected_text_sha256"
    ] == EXPECTED_TEXT_SHA

    validate_pending_evidence_template(
        template
    )


def test_prefilled_evidence_template_fails() -> None:
    template = build_evidence_template()

    template[
        "paid_partnership_disclosure_enabled"
    ] = True

    with pytest.raises(
        XManualPostingReadinessError,
        match="remain empty",
    ):
        validate_pending_evidence_template(
            template
        )
