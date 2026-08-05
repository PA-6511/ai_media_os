from __future__ import annotations

import pytest

from scripts.verify_x_r11_wordpress_publication_post_execution import (
    EXPECTED_APPROVAL_GATE_DIGEST,
    EXPECTED_APPROVAL_REQUEST_ID,
    EXPECTED_CONTENT_SHA,
    EXPECTED_MEDIA_ID,
    EXPECTED_POST_ID,
    EXPECTED_PUBLIC_URL,
    EXPECTED_REVIEW_DIGEST,
    PublicationVerificationError,
    validate_consumption_lock,
    validate_execution_claim,
    validate_receipt_summary,
)


def valid_execution_claim() -> dict:
    return {
        "lock_type": (
            "X_R11_WORDPRESS_PUBLICATION_"
            "EXECUTION_CLAIM"
        ),
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_APPROVAL_GATE_DIGEST
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "target_post_id": EXPECTED_POST_ID,
        "required_pre_execution_status": "draft",
        "required_post_execution_status": "publish",
        "required_content_sha256": (
            EXPECTED_CONTENT_SHA
        ),
        "required_media_id": EXPECTED_MEDIA_ID,
        "maximum_publication_update_count": 1,
        "execution_claimed": True,
        "reexecution_allowed": False,
    }


def valid_consumption_lock() -> dict:
    return {
        "lock_type": (
            "X_R11_WORDPRESS_PUBLICATION_"
            "APPROVAL_CONSUMPTION"
        ),
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_APPROVAL_GATE_DIGEST
        ),
        "approval_consumed": True,
        "consumed_for_execution_attempt": True,
        "reexecution_allowed": False,
    }


def valid_receipt_summary() -> dict:
    post_common = {
        "post_id": EXPECTED_POST_ID,
        "title": (
            "のあ先輩はともだち。 "
            "第11巻｜配信開始"
        ),
        "slug": (
            "noa-senpai-wa-tomodachi-"
            "11-6ffa7a8d"
        ),
        "category_ids": [43],
        "content_sha256": (
            EXPECTED_CONTENT_SHA
        ),
    }

    return {
        "status": (
            "PASS_WORDPRESS_PUBLICATION_ONE_SHOT"
        ),
        "execution_state": (
            "WORDPRESS_POST_195_PUBLISHED_"
            "PUBLIC_URL_VERIFIED_X_STILL_BLOCKED"
        ),
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "source_approval_gate_digest_sha256": (
            EXPECTED_APPROVAL_GATE_DIGEST
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "actual_publication_update_count": 1,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "wordpress_publication_executed": True,
        "wordpress_post_status": "publish",
        "public_url_available": True,
        "public_url": EXPECTED_PUBLIC_URL,
        "x_public_url_replacement_allowed": True,
        "x_post_execution_allowed": False,
        "x_api_call": False,
        "x_post": False,
        "wordpress_post_before": {
            **post_common,
            "status": "draft",
            "link": "https://hoshido.jp/?p=195",
        },
        "wordpress_post_after": {
            **post_common,
            "status": "publish",
            "link": EXPECTED_PUBLIC_URL,
        },
        "public_page_verification": {
            "http_status": 200,
            "resolved_url": EXPECTED_PUBLIC_URL,
        },
    }


def test_valid_execution_claim_passes() -> None:
    validate_execution_claim(
        valid_execution_claim()
    )


def test_execution_claim_reexecution_fails() -> None:
    value = valid_execution_claim()

    value["reexecution_allowed"] = True

    with pytest.raises(
        PublicationVerificationError,
        match="permits rerun",
    ):
        validate_execution_claim(
            value
        )


def test_valid_consumption_lock_passes() -> None:
    validate_consumption_lock(
        valid_consumption_lock()
    )


def test_unconsumed_approval_fails() -> None:
    value = valid_consumption_lock()

    value["approval_consumed"] = False

    with pytest.raises(
        PublicationVerificationError,
        match="was not consumed",
    ):
        validate_consumption_lock(
            value
        )


def test_valid_receipt_summary_passes() -> None:
    validate_receipt_summary(
        valid_receipt_summary()
    )


def test_wrong_public_url_fails() -> None:
    value = valid_receipt_summary()

    value["public_url"] = (
        "https://hoshido.jp/wrong/"
    )

    with pytest.raises(
        PublicationVerificationError,
        match="public URL mismatch",
    ):
        validate_receipt_summary(
            value
        )
