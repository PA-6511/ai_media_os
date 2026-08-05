from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = ROOT / (
    "config/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_authorization_policy.json"
)
REQUEST = ROOT / (
    "exchange/examples/"
    "new_release_wp_fresh_dmm_post_parser_fix_"
    "recheck_authorization_request.example.json"
)
APPROVAL = ROOT / (
    "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_m3_"
    "post_parser_fix_recheck_authorization_approval.json"
)
AUTHORIZATION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "authorization.json"
)
PLANNED_RECHECK = ROOT / (
    "exchange/rechecks/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "result.json"
)
PLANNED_CONSUMPTION = ROOT / (
    "exchange/authorizations/new_release/fresh/"
    "new-release-comic-20260703-001."
    "dmm_latest_alias_recheck_post_parser_fix_"
    "consumption.json"
)
RESULT = ROOT / (
    "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_m3_result.json"
)
REPORT = ROOT / (
    "reports/"
    "ls_new_batch_4g_2e_recovery_m3_"
    "post_parser_fix_dmm_recheck_authorization_report.md"
)
BUILDER = ROOT / (
    "scripts/"
    "build_ls_new_batch_4g_2e_recovery_m3.py"
)
BLOCKED = ROOT / (
    "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_m3_blocked.py"
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
            "new_authorization_artifact_creation_allowed"
        ]
        is True
    )
    assert (
        boundary["actual_network_recheck_allowed"]
        is False
    )
    assert (
        boundary[
            "new_authorization_consumption_allowed"
        ]
        is False
    )
    assert (
        boundary[
            "existing_authorization_reuse_allowed"
        ]
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


def test_new_authorization_digest() -> None:
    authorization = load(AUTHORIZATION)
    comparable = copy.deepcopy(
        authorization
    )
    stored = comparable.pop(
        "authorization_digest_sha256"
    )

    assert digest(comparable) == stored


def test_new_authorization_has_separate_identity() -> None:
    authorization = load(AUTHORIZATION)

    assert authorization["authorization_id"] == (
        "DMM_LATEST_ALIAS_861056_POST_PARSER_"
        "FIX_ONE_SHOT_READ_ONLY_RECHECK_"
        "AUTHORIZATION_V1"
    )
    assert (
        "post_parser_fix"
        in AUTHORIZATION.name
    )
    assert (
        authorization[
            "old_authorization_reuse_allowed"
        ]
        is False
    )


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


def test_auth_cookie_and_retry_forbidden() -> None:
    target = load(AUTHORIZATION)[
        "target_request"
    ]

    assert target["authentication_allowed"] is False
    assert target["login_allowed"] is False
    assert target["cookie_send_allowed"] is False
    assert target["cookie_persistence_allowed"] is False
    assert target["automatic_retry_allowed"] is False
    assert (
        target["proxy_environment_use_allowed"]
        is False
    )


def test_redirect_contract() -> None:
    redirect = load(AUTHORIZATION)[
        "redirect_requirements"
    ]

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


def test_remediated_parser_is_bound() -> None:
    authorization = load(AUTHORIZATION)
    parser = authorization[
        "parser_binding"
    ]

    assert parser["runner_file_sha256"] == (
        "adfe2cbb8478458e8940eb0d67de4aa8"
        "e223ba6923353a2f0f0dc4d35e37e35f"
    )
    assert parser[
        "null_safe_meta_fallback_verified"
    ] is True
    assert (
        parser[
            "runner_change_after_authorization_allowed"
        ]
        is False
    )


def test_historical_artifacts_are_preserved() -> None:
    request = load(REQUEST)
    bindings = request[
        "source_bindings"
    ]

    for path_field, hash_field in [
        (
            "m2_fix1_result_path",
            "m2_fix1_result_file_sha256",
        ),
        (
            "old_m2_result_path",
            "old_m2_result_file_sha256",
        ),
        (
            "old_m2_recheck_result_path",
            "old_m2_recheck_result_file_sha256",
        ),
        (
            "old_m2_consumption_path",
            "old_m2_consumption_file_sha256",
        ),
        (
            "old_m2_execute_approval_path",
            "old_m2_execute_approval_file_sha256",
        ),
        (
            "old_m1_authorization_path",
            "old_m1_authorization_file_sha256",
        ),
        (
            "generated_article_path",
            "generated_article_file_sha256",
        ),
        (
            "store_link_plan_path",
            "store_link_plan_file_sha256",
        ),
    ]:
        path = ROOT / bindings[
            path_field
        ]

        assert file_sha256(path) == (
            bindings[hash_field]
        )


def test_new_terminal_artifacts_do_not_exist() -> None:
    assert not PLANNED_RECHECK.exists()
    assert not PLANNED_CONSUMPTION.exists()


def test_builder_has_no_network_client() -> None:
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
        blocked[
            "new_authorization_consumption_allowed"
        ]
        is False
    )
    assert (
        blocked["old_authorization_reuse_allowed"]
        is False
    )
    assert (
        blocked["network_connection_allowed"]
        is False
    )


def test_result_waits_for_execute_confirmation() -> None:
    result = load(RESULT)

    assert result["status"] == (
        "PASS_DMM_RECHECK_POST_REMEDIATION_"
        "ONE_SHOT_AUTHORIZATION_FIXED_NO_NETWORK"
    )
    assert result["authorization_consumed"] is False
    assert result["old_authorization_reused"] is False
    assert (
        result["actual_network_recheck_performed"]
        is False
    )
    assert (
        result[
            "ready_for_post_fix_dmm_recheck_execute_now_confirmation"
        ]
        is True
    )
    assert (
        result["ready_for_actual_dmm_recheck"]
        is False
    )


def test_production_boundary_is_closed() -> None:
    result = load(RESULT)

    assert (
        result["final_affiliate_link_generated"]
        is False
    )
    assert result["article_modified"] is False
    assert (
        result["article_url_injection_performed"]
        is False
    )
    assert result["fresh_payload_created"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result["network_connection_performed"]
        is False
    )
    assert result["http_request_performed"] is False
    assert (
        result["wordpress_write_performed"]
        is False
    )
    assert result["execution_allowed"] is False
    assert result["production_status"] == "NO_GO"


def test_report_confirms_authorization_boundary() -> None:
    report = REPORT.read_text(
        encoding="utf-8"
    )

    assert "New authorization ID:" in report
    assert "Remediated parser bound: `true`" in report
    assert "Consumed: `false`" in report
    assert "Old authorization reused: `false`" in report
    assert "Network recheck performed: `false`" in report
    assert "Production status: `NO_GO`" in report
