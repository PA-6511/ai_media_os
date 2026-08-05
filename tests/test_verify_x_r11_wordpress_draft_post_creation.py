from __future__ import annotations

import pytest

from scripts.verify_x_r11_wordpress_draft_post_creation import (
    PostCreationVerificationError,
    validate_duplicate_state,
    validate_execution_evidence,
)


def valid_duplicate_state() -> dict:
    return {
        "duplicate_found": True,
        "exact_slug_match_count": 1,
        "exact_title_match_count": 1,
        "matched_post_ids": [195],
    }


def test_exact_created_post_duplicate_passes() -> None:
    validate_duplicate_state(
        valid_duplicate_state()
    )


def test_multiple_slug_matches_fail() -> None:
    value = valid_duplicate_state()
    value["exact_slug_match_count"] = 2

    with pytest.raises(
        PostCreationVerificationError,
        match="must equal one",
    ):
        validate_duplicate_state(value)


def test_wrong_post_id_fails() -> None:
    value = valid_duplicate_state()
    value["matched_post_ids"] = [196]

    with pytest.raises(
        PostCreationVerificationError,
        match="only to post 195",
    ):
        validate_duplicate_state(value)


def test_valid_execution_locks_pass() -> None:
    digest = "a" * 64

    validate_execution_evidence(
        execution_claim={
            "lock_type": (
                "X_R11_WORDPRESS_DRAFT_"
                "CREATION_EXECUTION_CLAIM"
            ),
            "creation_request_id": (
                "xr11-wp-draft-create-"
                "baf4e4451e14b3b4b3984bd2"
            ),
            "approval_certificate_digest_sha256": (
                "794843a83eb52837ea01181754f3f3f66"
                "89f1eb4c8ca6225adc85884203962fa"
            ),
            "payload_preview_digest_sha256": digest,
            "maximum_post_create_count": 1,
            "execution_claimed": True,
            "reexecution_allowed": False,
        },
        consumption_lock={
            "lock_type": (
                "X_R11_WORDPRESS_DRAFT_"
                "CREATION_APPROVAL_CONSUMPTION"
            ),
            "creation_request_id": (
                "xr11-wp-draft-create-"
                "baf4e4451e14b3b4b3984bd2"
            ),
            "approval_certificate_digest_sha256": (
                "794843a83eb52837ea01181754f3f3f66"
                "89f1eb4c8ca6225adc85884203962fa"
            ),
            "wordpress_post_id": 195,
            "wordpress_post_status": "draft",
            "approval_consumed": True,
            "reexecution_allowed": False,
        },
        payload_digest=digest,
    )
