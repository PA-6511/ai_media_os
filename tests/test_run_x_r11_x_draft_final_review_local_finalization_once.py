from __future__ import annotations

import hashlib

import pytest

from scripts.run_x_r11_x_draft_final_review_local_finalization_once import (
    EXPECTED_APPROVAL_GATE_DIGEST,
    EXPECTED_DRAFT_ID,
    EXPECTED_FINAL_TEXT,
    EXPECTED_LITERAL_CHARACTER_COUNT,
    EXPECTED_PUBLIC_URL,
    EXPECTED_REVIEW_DIGEST,
    EXPECTED_TEXT_SHA,
    XDraftLocalFinalizationError,
    validate_approval_gate,
    validate_issuance_lock,
    validate_source_text,
)


def valid_gate() -> dict:
    payload = {
        "phase": "test",
        "status": (
            "PASS_X_DRAFT_FINAL_REVIEW_"
            "EXPLICIT_APPROVAL_GATE_READY"
        ),
        "approval_gate_state": (
            "READY_AWAITING_ONE_SHOT_"
            "LOCAL_X_DRAFT_FINALIZATION"
        ),
        "approval_request_id": (
            "xr11-x-final-review-"
            "d5112969c7ba2a6fa2f02f8d"
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_certificate_digest_sha256": (
            "1" * 64
        ),
        "human_decision": "APPROVED",
        "final_human_review_completed": True,
        "x_final_review_approval_issued": True,
        "x_final_review_approval_consumed": False,
        "local_finalization_runner_allowed": True,
        "x_draft": {
            "draft_id": EXPECTED_DRAFT_ID,
            "text_sha256": EXPECTED_TEXT_SHA,
            "literal_character_count": (
                EXPECTED_LITERAL_CHARACTER_COUNT
            ),
            "estimated_tco_character_count": 117,
            "public_url": EXPECTED_PUBLIC_URL,
        },
        "x_post_approval_issued": False,
        "manual_x_posting_allowed": False,
        "x_post_execution_allowed": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
    }

    from scripts.build_x_r9_preflight_approval_pack import (
        canonical_digest,
    )

    return {
        **payload,
        "x_draft_final_review_explicit_"
        "approval_gate_digest_sha256": (
            canonical_digest(payload)
        ),
    }


def test_valid_source_text_passes() -> None:
    validate_source_text(
        EXPECTED_FINAL_TEXT
    )


def test_changed_source_text_fails() -> None:
    changed = EXPECTED_FINAL_TEXT.replace(
        "第11巻",
        "第12巻",
        1,
    )

    with pytest.raises(
        XDraftLocalFinalizationError,
        match="text mismatch",
    ):
        validate_source_text(
            changed
        )


def test_expected_text_sha_is_fixed() -> None:
    assert hashlib.sha256(
        EXPECTED_FINAL_TEXT.encode("utf-8")
    ).hexdigest() == EXPECTED_TEXT_SHA


def test_consumed_gate_fails(
    monkeypatch,
) -> None:
    gate = valid_gate()

    gate[
        "x_final_review_approval_consumed"
    ] = True

    import scripts.run_x_r11_x_draft_final_review_local_finalization_once as module

    from scripts.build_x_r9_preflight_approval_pack import (
        canonical_digest,
    )

    digest_field = (
        "x_draft_final_review_explicit_"
        "approval_gate_digest_sha256"
    )

    digest_payload = {
        key: value
        for key, value in gate.items()
        if key != digest_field
    }

    gate[digest_field] = canonical_digest(
        digest_payload
    )

    monkeypatch.setattr(
        module,
        "EXPECTED_APPROVAL_GATE_DIGEST",
        gate[digest_field],
    )

    with pytest.raises(
        XDraftLocalFinalizationError,
        match="already consumed",
    ):
        validate_approval_gate(
            gate
        )


def test_valid_issuance_lock_passes() -> None:
    validate_issuance_lock(
        {
            "lock_type": (
                "X_R11_X_DRAFT_FINAL_REVIEW_"
                "APPROVAL_ISSUANCE"
            ),
            "approval_request_id": (
                "xr11-x-final-review-"
                "d5112969c7ba2a6fa2f02f8d"
            ),
            "source_review_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "approval_label": (
                "APPROVED_FOR_X_R11_X_DRAFT_"
                "FINAL_REVIEW_ONLY"
            ),
            "approval_scope": (
                "ONE_LOCAL_X_DRAFT_FINAL_REVIEW_"
                "ONLY_NO_X_POST"
            ),
            "approval_certificate_digest_sha256": (
                "2" * 64
            ),
            "approval_gate_digest_sha256": (
                EXPECTED_APPROVAL_GATE_DIGEST
            ),
            "approval_issued": True,
            "approval_consumed": False,
            "reissuance_allowed": False,
            "x_post_allowed": False,
        },
        certificate_digest="2" * 64,
    )


def test_issuance_lock_x_post_allowed_fails() -> None:
    value = {
        "lock_type": (
            "X_R11_X_DRAFT_FINAL_REVIEW_"
            "APPROVAL_ISSUANCE"
        ),
        "approval_request_id": (
            "xr11-x-final-review-"
            "d5112969c7ba2a6fa2f02f8d"
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": (
            "APPROVED_FOR_X_R11_X_DRAFT_"
            "FINAL_REVIEW_ONLY"
        ),
        "approval_scope": (
            "ONE_LOCAL_X_DRAFT_FINAL_REVIEW_"
            "ONLY_NO_X_POST"
        ),
        "approval_certificate_digest_sha256": (
            "2" * 64
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_APPROVAL_GATE_DIGEST
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "reissuance_allowed": False,
        "x_post_allowed": True,
    }

    with pytest.raises(
        XDraftLocalFinalizationError,
        match="permits X posting",
    ):
        validate_issuance_lock(
            value,
            certificate_digest="2" * 64,
        )
