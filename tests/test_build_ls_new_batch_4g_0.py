from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY_PATH = (
    ROOT
    / "config/"
    "new_release_wp_read_only_category_lookup_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_design_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4g_0_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_0_read_only_category_lookup_design_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4g_0.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4g_0_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4g_0_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_is_get_only_and_design_only() -> None:
    policy = load_json(POLICY_PATH)
    http = policy["http_contract"]
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4G-0"
    assert http["allowed_method"] == "GET"
    assert (
        http["allowed_rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert http["request_body_allowed"] is False
    assert http["redirect_follow_allowed"] is False
    assert http["tls_verification_required"] is True
    assert boundary["network_connection_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_allowed"] is False


def test_request_does_not_request_access() -> None:
    request = load_json(REQUEST_PATH)

    assert request["http_plan"]["method"] == "GET"
    assert request["http_plan"]["request_body"] is None
    assert request["credential_file_read_requested"] is False
    assert request["dns_resolution_requested"] is False
    assert request["tls_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_response_read_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["credential_value_output_requested"] is False


def test_lookup_plan_is_exact_and_non_executed() -> None:
    package = load_json(OUTPUT_PATH)
    plan = package["lookup_plans"][0]

    assert package["lookup_plan_count"] == 1
    assert plan["category_slug"] == "comic-new-release"
    assert plan["category_name"] == "コミック新刊"
    assert plan["method"] == "GET"
    assert plan["base_url"] is None
    assert (
        plan["rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert plan["request_body"] is None
    assert plan["authorization_header_constructed"] is False
    assert plan["credential_values_loaded"] is False
    assert plan["http_request_performed"] is False
    assert plan["response_read"] is False
    assert (
        plan["future_matching_requirements"][
            "automatic_payload_injection_allowed"
        ]
        is False
    )


def test_post_method_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["http_plan"]["method"] = "POST"

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "HTTP method must be GET" in str(exc)
    else:
        raise AssertionError("POST method was accepted")


def test_access_request_true_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["http_request_requested"] = True

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "HTTP access request was accepted"
        )


def test_target_category_mismatch_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["target_categories"][0][
        "category_name"
    ] = "別カテゴリ"

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "target categories mismatch" in str(exc)
    else:
        raise AssertionError(
            "target category mismatch was accepted"
        )


def test_design_digest_is_deterministic() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    policy = load_json(POLICY_PATH)

    first = builder.build_package(
        request=copy.deepcopy(request),
        policy=policy,
    )
    second = builder.build_package(
        request=copy.deepcopy(request),
        policy=policy,
    )

    assert len(first["design_package_digest_sha256"]) == 64
    assert (
        first["design_package_digest_sha256"]
        == second["design_package_digest_sha256"]
    )
    assert (
        first["lookup_plans"][0][
            "lookup_plan_digest_sha256"
        ]
        == second["lookup_plans"][0][
            "lookup_plan_digest_sha256"
        ]
    )


def test_execution_runner_remains_blocked() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(BLOCKED_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 3

    result = json.loads(completed.stderr)

    assert result["status"] == "BLOCKED_LOOKUP_DESIGN_ONLY"
    assert result["credential_preflight_passed"] is True
    assert result["credential_values_loaded"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_response_read"] is False
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_READ_ONLY_CATEGORY_LOOKUP_"
        "DESIGN_NO_NETWORK"
    )
    assert (
        result["decision"]
        == "GET_ONLY_CATEGORY_LOOKUP_CONTRACT_READY"
    )
    assert result["http_method"] == "GET"
    assert (
        result["rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert result["credential_preflight_passed"] is True
    assert result["credential_values_loaded"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_response_read"] is False
    assert result["wordpress_write_performed"] is False
    assert result["ready_for_ls_new_batch_4g_1"] is True
    assert result["ready_for_actual_read_only_lookup"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Method: `GET`" in report
    assert "Credential values loaded: `false`" in report
    assert "HTTP request performed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
