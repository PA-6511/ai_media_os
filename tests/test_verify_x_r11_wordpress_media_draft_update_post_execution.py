from __future__ import annotations

import hashlib

import pytest

from scripts.verify_x_r11_wordpress_media_draft_update_post_execution import (
    EXPECTED_MEDIA_ID,
    EXPECTED_MEDIA_SOURCE_URL,
    EXPECTED_POST_ID,
    PostExecutionVerificationError,
    validate_consumption_lock,
    validate_execution_claim,
    validate_single_media_duplicate,
    validate_updated_post,
)


def valid_duplicate_state() -> dict:
    return {
        "duplicate_found": True,
        "exact_match_count": 1,
        "matched_media_ids": [
            EXPECTED_MEDIA_ID
        ],
    }


def test_single_media_duplicate_passes() -> None:
    validate_single_media_duplicate(
        valid_duplicate_state()
    )


def test_multiple_media_matches_fail() -> None:
    value = valid_duplicate_state()
    value["exact_match_count"] = 2

    with pytest.raises(
        PostExecutionVerificationError,
        match="must equal one",
    ):
        validate_single_media_duplicate(
            value
        )


def test_wrong_media_id_fails() -> None:
    value = valid_duplicate_state()
    value["matched_media_ids"] = [999]

    with pytest.raises(
        PostExecutionVerificationError,
        match="only to media 196",
    ):
        validate_single_media_duplicate(
            value
        )


def test_valid_execution_claim_passes() -> None:
    validate_execution_claim(
        {
            "lock_type": (
                "X_R11_WORDPRESS_MEDIA_DRAFT_"
                "UPDATE_EXECUTION_CLAIM"
            ),
            "approval_request_id": (
                "xr11-wp-media-draft-update-"
                "5b2faab0d29b9fe830daae75"
            ),
            "approval_gate_digest_sha256": (
                "f608821d973164a21236c5b478425357"
                "3138a1b7f1033e81e264ec6eac5ac775"
            ),
            "source_review_digest_sha256": (
                "5b2faab0d29b9fe830daae7578d97a5b"
                "5d7fff20612a5a8afb963962f0a3d11b"
            ),
            "media_sha256": (
                "fcd5ed6e8a2136f45a380e055d3a34e7"
                "fe1e0d90cfaed9c8bcc8839c95a890c7"
            ),
            "target_post_id": EXPECTED_POST_ID,
            "maximum_media_create_count": 1,
            "maximum_draft_update_count": 1,
            "execution_claimed": True,
            "reexecution_allowed": False,
        }
    )


def test_valid_consumption_lock_passes() -> None:
    validate_consumption_lock(
        {
            "lock_type": (
                "X_R11_WORDPRESS_MEDIA_DRAFT_"
                "UPDATE_APPROVAL_CONSUMPTION"
            ),
            "approval_request_id": (
                "xr11-wp-media-draft-update-"
                "5b2faab0d29b9fe830daae75"
            ),
            "approval_gate_digest_sha256": (
                "f608821d973164a21236c5b478425357"
                "3138a1b7f1033e81e264ec6eac5ac775"
            ),
            "approval_consumed": True,
            "consumed_for_execution_attempt": True,
            "reexecution_allowed": False,
        }
    )


def test_valid_updated_post_passes() -> None:
    content = (
        '<figure class="ebook-cover-image">'
        f'<img src="{EXPECTED_MEDIA_SOURCE_URL}" '
        'alt="のあ先輩はともだち。 第11巻 書影">'
        "</figure>"
    )

    result = validate_updated_post(
        {
            "id": EXPECTED_POST_ID,
            "status": "draft",
            "slug": (
                "noa-senpai-wa-tomodachi-"
                "11-6ffa7a8d"
            ),
            "title": {
                "raw": (
                    "のあ先輩はともだち。 "
                    "第11巻｜配信開始"
                )
            },
            "categories": [43],
            "content": {
                "raw": content
            },
            "link": (
                "https://hoshido.jp/?p=195"
            ),
        },
        expected_content_sha256=(
            hashlib.sha256(
                content.encode("utf-8")
            ).hexdigest()
        ),
        media_source_url=(
            EXPECTED_MEDIA_SOURCE_URL
        ),
    )

    assert result["post_id"] == 195
    assert result["status"] == "draft"
