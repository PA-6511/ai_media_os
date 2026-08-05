from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_x_r13_pre_post_slack_approval_flow_prep import (
    EXPECTED_BINDINGS,
    EXPECTED_CLOSEOUT_DIGEST,
    EXPECTED_FLOW_ORDER,
    EXPECTED_INDEX_SHA,
    EXPECTED_REVIEW_DIGEST,
    PHASE,
    STATUS,
    Xr13PrepError,
    build_prep_payload,
    validate_policy,
)


def valid_policy() -> dict:
    return {
        "schema_version": (
            "X_R13_PRE_POST_SLACK_"
            "APPROVAL_FLOW_POLICY_V1"
        ),
        "phase": PHASE,
        "status": (
            "PREP_ONLY_NO_DELIVERY_NO_POSTING"
        ),
        "source_baseline": {
            "x_r12_closeout_digest_sha256": (
                EXPECTED_CLOSEOUT_DIGEST
            ),
            "x_r12_review_result_digest_sha256": (
                EXPECTED_REVIEW_DIGEST
            ),
            "evidence_index_sha256": (
                EXPECTED_INDEX_SHA
            ),
        },
        "flow_order": list(
            EXPECTED_FLOW_ORDER
        ),
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
            "one_shot_delivery_required": True,
            "automatic_retry_allowed": False,
            "interactive_buttons_enabled": False,
            "thread_reply_review_enabled": True,
        },
        "review": {
            "human_approval_required": True,
            "exact_tokens": [
                "APPROVE",
                "REVISE",
                "REJECT",
            ],
            "approval_evidence_mode": (
                "MANUAL_SCREENSHOT_AND_EXACT_TOKEN"
            ),
            "reaction_only_approval_allowed": False,
            "slack_api_read_required": False,
            "pre_post_approval_required": True,
            "retrospective_approval_is_normal_path": False,
        },
        "approval_binding": {
            "required_fields": sorted(
                EXPECTED_BINDINGS
            ),
            "invalidate_on_text_change": True,
            "invalidate_on_url_change": True,
            "invalidate_on_account_change": True,
            "invalidate_on_store_change": True,
            "invalidate_on_link_route_change": True,
            "posting_authorization_only_after_approve": True,
            "approved_state": (
                "APPROVED_BEFORE_POSTING"
            ),
            "pre_post_approval": True,
            "retroactive_content_review": False,
        },
        "posting": {
            "mode": "HUMAN_MANUAL",
            "one_manual_x_post_authorized_after_approval": True,
            "x_api_allowed": False,
            "browser_automation_allowed": False,
            "automatic_posting_allowed": False,
            "additional_x_post_allowed": False,
            "x_post_url_registration_required": True,
            "metrics_capture_required": True,
        },
        "storage": {
            "canonical_draft_storage": (
                "LOCAL_JSON"
            ),
            "slack_is_canonical_storage": False,
            "database_write_allowed_in_prep": False,
            "workflow_write_allowed_in_prep": False,
            "wordpress_write_allowed_in_prep": False,
        },
        "failure_policy": {
            "failure_action": "STOP",
            "delivery_failure_requires_manual_reconciliation": True,
            "approval_ambiguity_action": "STOP",
            "draft_change_after_approval_action": (
                "INVALIDATE_AND_REVIEW_AGAIN"
            ),
            "automatic_retry_allowed": False,
        },
        "production_status": "NO_GO",
    }


def test_valid_policy_passes() -> None:
    validate_policy(valid_policy())


def test_wrong_flow_order_fails() -> None:
    policy = valid_policy()
    policy["flow_order"] = list(
        reversed(EXPECTED_FLOW_ORDER)
    )

    with pytest.raises(
        Xr13PrepError,
        match="flow order",
    ):
        validate_policy(policy)


def test_missing_approve_token_fails() -> None:
    policy = valid_policy()
    policy["review"]["exact_tokens"] = [
        "REVISE",
        "REJECT",
    ]

    with pytest.raises(
        Xr13PrepError,
        match="review tokens",
    ):
        validate_policy(policy)


def test_retrospective_normal_path_fails() -> None:
    policy = valid_policy()

    policy["review"][
        "retrospective_approval_is_normal_path"
    ] = True

    with pytest.raises(
        Xr13PrepError,
        match="retrospective",
    ):
        validate_policy(policy)


def test_x_api_enabled_fails() -> None:
    policy = valid_policy()

    policy["posting"][
        "x_api_allowed"
    ] = True

    with pytest.raises(
        Xr13PrepError,
        match="unsafe posting",
    ):
        validate_policy(policy)


def test_missing_binding_fails() -> None:
    policy = valid_policy()

    policy["approval_binding"][
        "required_fields"
    ].remove("affiliate_url")

    with pytest.raises(
        Xr13PrepError,
        match="approval bindings",
    ):
        validate_policy(policy)


def test_text_invalidation_disabled_fails() -> None:
    policy = valid_policy()

    policy["approval_binding"][
        "invalidate_on_text_change"
    ] = False

    with pytest.raises(
        Xr13PrepError,
        match="required binding flag",
    ):
        validate_policy(policy)


def test_prep_payload_is_safe() -> None:
    payload = build_prep_payload(
        policy_path=Path("/tmp/policy.json"),
        closeout_path=Path("/tmp/closeout.json"),
        evidence_index_path=Path("/tmp/index.json"),
        report_path=Path("/tmp/report.md"),
    )

    assert payload["status"] == STATUS
    assert payload["candidate_bound"] is False

    assert payload["target_flow"][
        "pre_post_approval"
    ] is True

    assert payload["target_flow"][
        "retroactive_content_review"
    ] is False

    assert payload["safety"][
        "slack_message_sent"
    ] is False

    assert payload["safety"][
        "posting_authorization_issued"
    ] is False

    assert payload["safety"][
        "x_post_executed"
    ] is False

    assert payload["safety"][
        "database_write"
    ] is False
