from __future__ import annotations

import pytest

from scripts.build_x_r11_x_manual_posting_explicit_approval_gate import (
    APPROVAL_LABEL,
    DISCLOSURE_ATTESTATION,
    OFFICIAL_SURFACE_ATTESTATION,
    RELATIONSHIP_ATTESTATION,
    XManualPostingApprovalError,
    build_conditionally_approved_checklist,
    validate_approval_label,
    validate_approved_checklist,
    validate_attestations,
    validate_x_account_handle,
)


def pending_checklist() -> list[dict]:
    check_ids = [
        "X_ACCOUNT_IDENTITY",
        "RAKUTEN_RELATIONSHIP_CLASSIFICATION",
        "SPECIAL_CAMPAIGN_STOP_RULE",
        "FROZEN_TEXT_SHA",
        "PUBLIC_URL",
        "WORDPRESS_PUBLIC_STATUS",
        "X_PAID_PARTNERSHIP_DISCLOSURE",
        "DISCLOSURE_VISIBLE_BEFORE_POST",
        "TEXT_NOT_MODIFIED",
        "CHARACTER_COUNT",
        "NO_AUTOMATION_OR_API",
        "POST_EVIDENCE_CAPTURE",
    ]

    return [
        {
            "check_id": check_id,
            "human_decision": "PENDING",
            "blocking": True,
        }
        for check_id in check_ids
    ]


def test_exact_approval_label_passes() -> None:
    validate_approval_label(
        APPROVAL_LABEL
    )


def test_wrong_approval_label_fails() -> None:
    with pytest.raises(
        XManualPostingApprovalError,
        match="exactly equal",
    ):
        validate_approval_label(
            "APPROVED"
        )


def test_valid_x_handle_passes() -> None:
    validate_x_account_handle(
        "@test_account"
    )


def test_invalid_x_handle_fails() -> None:
    with pytest.raises(
        XManualPostingApprovalError,
        match="must begin with @",
    ):
        validate_x_account_handle(
            "invalid handle"
        )


def test_exact_attestations_pass() -> None:
    validate_attestations(
        relationship_attestation=(
            RELATIONSHIP_ATTESTATION
        ),
        disclosure_attestation=(
            DISCLOSURE_ATTESTATION
        ),
        official_surface_attestation=(
            OFFICIAL_SURFACE_ATTESTATION
        ),
    )


def test_conditional_checklist_passes() -> None:
    result = (
        build_conditionally_approved_checklist(
            pending_checklist(),
            x_account_handle="@test_account",
        )
    )

    validate_approved_checklist(
        result
    )
