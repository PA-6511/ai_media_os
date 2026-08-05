from __future__ import annotations

import json

import pytest

from scripts.build_x_r12_slack_draft_review_delivery_prep import (
    APPROVAL_TOKENS,
    EXPECTED_AFFILIATE_URL,
    EXPECTED_TEXT_SHA,
    EXPECTED_X_ACCOUNT_HANDLE,
    SlackDraftPrepError,
    build_review_request,
    build_slack_payload,
    validate_policy,
)


REQUIRED_CHECKS = [
    "PR_DISCLOSURE_PRESENT",
    "AFFILIATE_URL_VERIFIED",
    "STORE_MATCH_VERIFIED",
]


DRAFT_TEXT = (
    "【PR・新刊】\n"
    "『のあ先輩はともだち。』"
    "11巻 配信開始📚\n"
    "あきやまえんま／集英社\n"
    "\n"
    "Kobo：https://a.r10.to/hPKo3p\n"
    "\n"
    "#のあ先輩はともだち "
    "#あきやまえんま"
)


def valid_policy() -> dict:
    return {
        "schema_version": (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_POLICY_V1"
        ),
        "phase": (
            "X-R12-SLACK-DRAFT-REVIEW-"
            "DELIVERY-PREP"
        ),
        "status": "PREP_ONLY_NO_DELIVERY",
        "delivery": {
            "transport": (
                "SLACK_INCOMING_WEBHOOK"
            ),
            "credential_env_key": (
                "SLACK_X_DRAFT_REVIEW_WEBHOOK_URL"
            ),
            "credential_read_allowed_in_prep": False,
            "slack_api_call_allowed_in_prep": False,
            "message_send_allowed_in_prep": False,
            "interactive_buttons_enabled": False,
        },
        "review": {
            "human_approval_required": True,
            "approval_tokens": APPROVAL_TOKENS,
            "approval_expires_after_text_change": True,
            "approval_expires_after_url_change": True,
            "approval_expires_after_account_change": True,
        },
        "posting": {
            "x_posting_mode": "MANUAL",
            "x_api_allowed": False,
            "browser_automation_allowed": False,
            "automatic_posting_allowed": False,
        },
        "production_status": "NO_GO",
    }


def test_policy_passes() -> None:
    validate_policy(valid_policy())


def test_policy_rejects_slack_send() -> None:
    value = valid_policy()

    value[
        "delivery"
    ][
        "message_send_allowed_in_prep"
    ] = True

    with pytest.raises(
        SlackDraftPrepError,
        match="send is allowed",
    ):
        validate_policy(value)


def test_review_request_is_bound() -> None:
    request = build_review_request(
        draft_text=DRAFT_TEXT,
        required_checks=REQUIRED_CHECKS,
    )

    assert request[
        "x_account_handle"
    ] == EXPECTED_X_ACCOUNT_HANDLE

    assert request[
        "affiliate_url"
    ] == EXPECTED_AFFILIATE_URL

    assert request[
        "draft_text_sha256"
    ] == EXPECTED_TEXT_SHA

    assert request[
        "approval_binding"
    ]["invalidate_on_any_change"] is True


def test_slack_payload_passes() -> None:
    request = build_review_request(
        draft_text=DRAFT_TEXT,
        required_checks=REQUIRED_CHECKS,
    )

    payload = build_slack_payload(request)

    assert payload["text"].startswith(
        "【X投稿レビュー待ち】"
    )

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
    )

    assert "APPROVE" in serialized
    assert "REVISE" in serialized
    assert "REJECT" in serialized
    assert EXPECTED_AFFILIATE_URL in serialized


def test_missing_pr_disclosure_fails() -> None:
    request = build_review_request(
        draft_text=DRAFT_TEXT.replace(
            "【PR・新刊】",
            "【新刊】",
        ),
        required_checks=REQUIRED_CHECKS,
    )

    with pytest.raises(
        SlackDraftPrepError,
        match="PR disclosure",
    ):
        build_slack_payload(request)


def test_slack_credential_leak_fails() -> None:
    request = build_review_request(
        draft_text=(
            DRAFT_TEXT
            + "\nhttps://hooks.slack.com/services/"
            + "T000/B000/SECRET"
        ),
        required_checks=REQUIRED_CHECKS,
    )

    with pytest.raises(
        SlackDraftPrepError,
        match="credential leaked",
    ):
        build_slack_payload(request)
