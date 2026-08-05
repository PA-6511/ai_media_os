from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "one_shot_recheck_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_execute_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m2_"
    "execute_now_approval.json"
)
AUTHORIZATION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_authorization.json"
)
CONSUMPTION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_consumption.json"
)
RECHECK_RESULT = (
    ROOT
    / "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_result.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m2_result.json"
)
ARTICLE = (
    ROOT
    / "exchange/content/new_release/fresh/"
    "new-release-comic-20260703-001.article.json"
)
PLAN = (
    ROOT
    / "exchange/plans/new_release/fresh/"
    "new-release-comic-20260703-001."
    "store_link_finalization_plan.json"
)
RUNNER = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m2.py"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m2_"
    "dmm_latest_alias_recheck_report.md"
)


def load(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_policy_is_one_shot_get_only() -> None:
    policy = load(POLICY)
    target = policy[
        "target_contract"
    ]

    assert target["method"] == "GET"
    assert target["automatic_retry_allowed"] is False
    assert target["authentication_allowed"] is False
    assert target["cookie_send_allowed"] is False
    assert target["request_body_allowed"] is False
    assert target["proxy_environment_use_allowed"] is False


def test_execute_approval_digest() -> None:
    approval = load(APPROVAL)
    comparable = copy.deepcopy(
        approval
    )
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True


def test_source_authorization_is_preserved() -> None:
    request = load(REQUEST)

    assert (
        file_sha256(AUTHORIZATION)
        == request["source_bindings"][
            "authorization_file_sha256"
        ]
    )

    authorization = load(AUTHORIZATION)

    assert authorization["authorization_consumed"] is False


def test_consumption_evidence_digest() -> None:
    evidence = load(CONSUMPTION)
    comparable = copy.deepcopy(
        evidence
    )
    stored = comparable.pop(
        "consumption_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert evidence["authorization_consumed"] is True
    assert evidence["consumption_is_authoritative"] is True
    assert evidence["authorization_reuse_allowed"] is False
    assert evidence["automatic_retry_allowed"] is False


def test_recheck_result_digest() -> None:
    result = load(RECHECK_RESULT)
    comparable = copy.deepcopy(
        result
    )
    stored = comparable.pop(
        "dmm_recheck_result_digest_sha256"
    )

    assert digest(comparable) == stored


def test_result_binds_consumption() -> None:
    result = load(RECHECK_RESULT)
    consumption = load(CONSUMPTION)

    assert (
        result[
            "consumption_evidence_digest_sha256"
        ]
        == consumption[
            "consumption_evidence_digest_sha256"
        ]
    )
    assert (
        result["attempt_id"]
        == consumption["attempt_id"]
    )


def test_request_used_no_auth_or_cookie() -> None:
    request = load(RECHECK_RESULT)[
        "request"
    ]

    assert request["method"] == "GET"
    assert request["request_body_used"] is False
    assert request["authentication_used"] is False
    assert request["login_used"] is False
    assert request["cookie_sent"] is False
    assert request["cookie_persisted"] is False
    assert request["credential_file_read"] is False
    assert request["automatic_retry_performed"] is False


def test_redirect_chain_is_allowlisted() -> None:
    network = load(RECHECK_RESULT)[
        "network"
    ]

    assert network["redirect_count"] <= 5

    for redirect in network[
        "redirect_chain"
    ]:
        parsed = urlparse(
            redirect["to_url"]
        )

        assert parsed.scheme == "https"
        assert parsed.hostname == "book.dmm.com"
        assert parsed.username is None
        assert parsed.password is None


def test_only_allowlisted_response_headers_saved() -> None:
    headers = load(RECHECK_RESULT)[
        "network"
    ]["response_headers_allowlisted"]

    allowed = {
        "content-type",
        "content-encoding",
        "location",
        "last-modified",
        "etag",
    }

    assert set(headers).issubset(
        allowed
    )
    assert "set-cookie" not in headers
    assert "cookie" not in headers


def test_full_response_body_not_persisted() -> None:
    result = load(RECHECK_RESULT)
    serialized = json.dumps(
        result,
        ensure_ascii=False,
    )

    assert (
        result["network"][
            "full_response_body_persisted"
        ]
        is False
    )
    assert "response_body_base64" not in serialized
    assert "response_body_text" not in serialized
    assert "raw_html" not in serialized


def test_decision_is_consistent() -> None:
    result = load(RECHECK_RESULT)
    success = result[
        "verification"
    ]["successful_match"]

    if success:
        assert result["dmm_slot_available"] is True
        assert result["dmm_slot_must_be_hidden"] is False
        assert result["human_review_required"] is False
        assert (
            result["extracted_identity"][
                "canonical_product_url"
            ]
            is not None
        )
    else:
        assert result["dmm_slot_available"] is False
        assert result["dmm_slot_must_be_hidden"] is True
        assert result["human_review_required"] is True


def test_no_final_affiliate_link_generated() -> None:
    recheck = load(RECHECK_RESULT)
    result = load(RESULT)

    assert (
        recheck["final_affiliate_link_generated"]
        is False
    )
    assert (
        result["final_affiliate_link_generated"]
        is False
    )
    assert (
        result["final_affiliate_link_validated"]
        is False
    )


def test_article_and_plan_are_preserved() -> None:
    request = load(REQUEST)
    bindings = request[
        "source_bindings"
    ]

    assert (
        file_sha256(ARTICLE)
        == bindings[
            "generated_article_file_sha256"
        ]
    )
    assert (
        file_sha256(PLAN)
        == bindings[
            "store_link_finalization_plan_file_sha256"
        ]
    )


def test_production_boundary_remains_closed() -> None:
    result = load(RESULT)

    assert result["article_modified"] is False
    assert (
        result[
            "article_url_injection_performed"
        ]
        is False
    )
    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result["wordpress_access_performed"]
        is False
    )
    assert (
        result["wordpress_write_performed"]
        is False
    )
    assert result["wordpress_published"] is False
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_rerun_is_blocked_without_changes() -> None:
    consumption_hash_before = file_sha256(
        CONSUMPTION
    )
    result_hash_before = file_sha256(
        RECHECK_RESULT
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--execute",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    blocked = json.loads(
        completed.stderr
    )

    assert (
        blocked["status"]
        == (
            "BLOCKED_DMM_RECHECK_"
            "AUTHORIZATION_ALREADY_CONSUMED"
        )
    )
    assert (
        blocked["authorization_reuse_allowed"]
        is False
    )
    assert (
        blocked["automatic_retry_allowed"]
        is False
    )

    assert (
        file_sha256(CONSUMPTION)
        == consumption_hash_before
    )
    assert (
        file_sha256(RECHECK_RESULT)
        == result_hash_before
    )


def test_result_records_terminal_state() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_DMM_LATEST_ALIAS_ONE_SHOT_"
        "RECHECK_EXECUTED_AUTH_CONSUMED_"
        "NO_LINK_GENERATION"
    )
    assert result["authorization_consumed"] is True
    assert result["consumption_evidence_created"] is True
    assert result["authorization_reuse_allowed"] is False
    assert result["automatic_retry_allowed"] is False
    assert result["network_attempt_performed"] is True


def test_report_confirms_no_body_and_no_write() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Authorization consumed: `true`" in report
    assert "Automatic retry allowed: `false`" in report
    assert "Full response body persisted: `false`" in report
    assert "Final affiliate link generated: `false`" in report
    assert "Article modified: `false`" in report
    assert "Production status: `NO_GO`" in report
