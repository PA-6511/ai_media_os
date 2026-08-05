from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = (
    ROOT
    / "config/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_authorization_policy.json"
)
REQUEST = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_dmm_latest_alias_"
    "recheck_authorization_request.example.json"
)
APPROVAL = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m1_"
    "dmm_latest_alias_recheck_authorization_approval.json"
)
AUTHORIZATION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_authorization.json"
)
RECHECK_RESULT = (
    ROOT
    / "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_result.json"
)
CONSUMPTION = (
    ROOT
    / "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_consumption.json"
)
RESULT = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m1_result.json"
)
REPORT = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_m1_"
    "dmm_latest_alias_recheck_authorization_report.md"
)
BLOCKED = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m1_blocked.py"
)
BUILDER = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_m1.py"
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


def test_policy_is_authorization_only() -> None:
    boundary = load(POLICY)[
        "execution_boundary"
    ]

    assert (
        boundary[
            "authorization_artifact_creation_allowed"
        ]
        is True
    )
    assert (
        boundary["actual_network_recheck_allowed"]
        is False
    )
    assert (
        boundary["authorization_consumption_allowed"]
        is False
    )
    assert (
        boundary["network_connection_allowed"]
        is False
    )


def test_human_approval_digest() -> None:
    approval = load(APPROVAL)
    comparable = copy.deepcopy(approval)
    stored = comparable.pop(
        "approval_evidence_digest_sha256"
    )

    assert digest(comparable) == stored
    assert approval["human_explicit_approval"] is True


def test_authorization_digest() -> None:
    authorization = load(AUTHORIZATION)
    comparable = copy.deepcopy(
        authorization
    )
    stored = comparable.pop(
        "authorization_digest_sha256"
    )

    assert digest(comparable) == stored


def test_exact_target_and_get_only() -> None:
    target = load(AUTHORIZATION)[
        "target_request"
    ]

    assert target["method"] == "GET"
    assert target["url"] == (
        "https://book.dmm.com/product/"
        "861056/latest/"
    )
    assert target["initial_host"] == "book.dmm.com"
    assert target["request_body_allowed"] is False
    assert target["write_operation_allowed"] is False


def test_authentication_and_cookies_forbidden() -> None:
    target = load(AUTHORIZATION)[
        "target_request"
    ]

    assert target["authentication_allowed"] is False
    assert target["login_allowed"] is False
    assert target["cookie_send_allowed"] is False
    assert target["cookie_persistence_allowed"] is False
    assert target["credential_file_read_allowed"] is False

    assert "Authorization" in (
        target["forbidden_request_headers"]
    )
    assert "Cookie" in (
        target["forbidden_request_headers"]
    )


def test_redirect_contract() -> None:
    redirect = load(AUTHORIZATION)[
        "redirect_requirements"
    ]

    assert redirect["follow_redirects"] is True
    assert redirect["maximum_redirect_count"] == 5
    assert redirect["allowed_hosts"] == [
        "book.dmm.com"
    ]
    assert (
        redirect["cross_host_redirect_allowed"]
        is False
    )
    assert (
        redirect["https_downgrade_allowed"]
        is False
    )


def test_identity_requirements() -> None:
    identity = load(AUTHORIZATION)[
        "identity_requirements"
    ]

    assert (
        identity["expected_work_title"]
        == "ダークギャザリング"
    )
    assert identity["expected_volume_number"] == 20
    assert (
        identity["expected_author_name"]
        == "近藤憲一"
    )
    assert (
        identity["expected_publisher_name"]
        == "集英社"
    )
    assert identity["expected_series_id"] == "861056"


def test_canonical_resolution_contract() -> None:
    canonical = load(AUTHORIZATION)[
        "canonical_resolution_requirements"
    ]

    assert (
        canonical["canonical_product_url_required"]
        is True
    )
    assert canonical["allowed_hosts"] == [
        "book.dmm.com"
    ]
    assert (
        canonical[
            "canonical_url_must_not_equal_latest_alias"
        ]
        is True
    )
    assert (
        canonical[
            "latest_alias_as_final_affiliate_link_allowed"
        ]
        is False
    )


def test_failure_contract_hides_dmm() -> None:
    failure = load(AUTHORIZATION)[
        "failure_actions"
    ]

    assert (
        "HIDE_DMM_SLOT"
        in failure["communication_failure"]
    )
    assert (
        "HIDE_DMM_SLOT"
        in failure["identity_mismatch"]
    )
    assert (
        failure["automatic_fallback_url_allowed"]
        is False
    )
    assert failure["dummy_url_allowed"] is False


def test_authorization_is_unconsumed() -> None:
    authorization = load(AUTHORIZATION)

    assert authorization["single_use"] is True
    assert (
        authorization["authorization_consumed"]
        is False
    )
    assert (
        authorization["authorization_reuse_allowed"]
        is False
    )
    assert (
        authorization["actual_network_recheck_performed"]
        is False
    )


def test_source_artifacts_are_preserved() -> None:
    request = load(REQUEST)

    for path_field, hash_field in [
        (
            "store_link_finalization_plan_path",
            "store_link_finalization_plan_file_sha256",
        ),
        (
            "generated_article_path",
            "generated_article_file_sha256",
        ),
        (
            "content_human_review_path",
            "content_human_review_file_sha256",
        ),
        (
            "generation_consumption_path",
            "generation_consumption_file_sha256",
        ),
        (
            "article_input_path",
            "article_input_file_sha256",
        ),
    ]:
        path = ROOT / request[
            "source_bindings"
        ][path_field]

        assert file_sha256(path) == (
            request["source_bindings"][
                hash_field
            ]
        )


def test_no_recheck_outputs_exist() -> None:
    assert not RECHECK_RESULT.exists()
    assert not CONSUMPTION.exists()


def test_builder_contains_no_network_client() -> None:
    source = BUILDER.read_text(
        encoding="utf-8"
    )

    for forbidden in [
        "import requests",
        "urllib.request",
        "http.client",
        "import socket",
        "urlopen(",
        "requests.get(",
    ]:
        assert forbidden not in source


def test_blocked_runner_returns_three() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED),
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
        blocked["actual_dmm_recheck_allowed"]
        is False
    )
    assert (
        blocked["network_connection_allowed"]
        is False
    )
    assert blocked["http_request_allowed"] is False


def test_result_waits_for_execute_confirmation() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_DMM_LATEST_ALIAS_ONE_SHOT_READ_ONLY_"
        "RECHECK_AUTHORIZATION_FIXED_NO_NETWORK"
    )
    assert result["authorization_consumed"] is False
    assert (
        result["actual_network_recheck_performed"]
        is False
    )
    assert (
        result[
            "ready_for_dmm_recheck_execute_now_confirmation"
        ]
        is True
    )
    assert (
        result["ready_for_actual_dmm_recheck"]
        is False
    )
    assert result["ready_for_execution"] is False


def test_report_confirms_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "Method: `GET`" in report
    assert "Authentication: `false`" in report
    assert "Cookie send: `false`" in report
    assert (
        "Network recheck performed: `false`"
        in report
    )
    assert "Production status: `NO_GO`" in report
