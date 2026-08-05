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
    "new_release_wp_credential_isolated_read_only_preflight_policy.json"
)
SOURCE_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_discovery_result.example.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_lookup_preflight_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_lookup_preflight_package.example.json"
)
RESULT_PATH = ROOT / "exchange/logs/ls_new_batch_4e_result.json"
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4e_credential_isolated_read_only_preflight_report.md"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4e.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4e_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4e_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_identity_and_closed_boundary() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4E"
    assert boundary["credential_read_allowed"] is False
    assert boundary["environment_variable_read_allowed"] is False
    assert boundary["dns_resolution_allowed"] is False
    assert boundary["network_connection_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_allowed"] is False
    assert boundary["production_status"] == "NO_GO"


def test_request_contains_no_credentials_or_network_request() -> None:
    request = load_json(REQUEST_PATH)

    assert request["endpoint_plan"]["base_url"] is None
    assert request["endpoint_plan"]["http_method"] == "GET"
    assert request["endpoint_plan"]["request_body"] is None
    assert request["endpoint_plan"]["custom_headers"] is None

    credential = request["credential_plan"]
    network = request["network_plan"]

    assert credential["credential_values_present"] is False
    assert credential["credential_file_content_read_requested"] is False
    assert credential["environment_variable_read_requested"] is False
    assert network["dns_resolution_requested"] is False
    assert network["http_request_requested"] is False


def test_output_contains_read_only_query_plan() -> None:
    package = load_json(OUTPUT_PATH)
    plan = package["query_plans"][0]

    assert package["query_plan_count"] == 1
    assert plan["http_method"] == "GET"
    assert plan["base_url"] is None
    assert plan["rest_path"] == "/wp-json/wp/v2/categories"
    assert plan["query_parameters"] == {
        "slug": "comic-new-release",
        "per_page": 100,
        "_fields": "id,slug,name,count"
    }
    assert plan["request_body"] is None
    assert plan["authorization_header"] is None
    assert plan["http_request_performed"] is False
    assert plan["automatic_payload_injection_allowed"] is False


def test_non_get_method_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["endpoint_plan"]["http_method"] = "POST"

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "HTTP method must be GET" in str(exc)
    else:
        raise AssertionError("POST method was accepted")


def test_non_null_base_url_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["endpoint_plan"][
        "base_url"
    ] = "https://example.invalid"

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "base_url must remain null" in str(exc)
    else:
        raise AssertionError("non-null base URL was accepted")


def test_secret_like_request_key_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request["credential_plan"]["authorization"] = "secret"

    try:
        builder.build_package(
            source=load_json(SOURCE_PATH),
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "forbidden credential-like key" in str(exc)
    else:
        raise AssertionError(
            "secret-like request key was accepted"
        )


def test_tampered_source_is_rejected() -> None:
    builder = load_builder()

    source = load_json(SOURCE_PATH)
    source["discovery_results"][0][
        "category_name"
    ] = "改変カテゴリ"

    try:
        builder.build_package(
            source=source,
            request=load_json(REQUEST_PATH),
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "discovery package digest" in str(exc)
    else:
        raise AssertionError("tampered source was accepted")


def test_package_and_query_digests_are_deterministic() -> None:
    builder = load_builder()

    source = load_json(SOURCE_PATH)
    request = load_json(REQUEST_PATH)
    policy = load_json(POLICY_PATH)

    first = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )
    second = builder.build_package(
        source=copy.deepcopy(source),
        request=copy.deepcopy(request),
        policy=policy,
    )

    assert len(first["preflight_package_digest_sha256"]) == 64
    assert (
        first["preflight_package_digest_sha256"]
        == second["preflight_package_digest_sha256"]
    )
    assert (
        first["query_plans"][0][
            "query_plan_digest_sha256"
        ]
        == second["query_plans"][0][
            "query_plan_digest_sha256"
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

    assert (
        result["status"]
        == "BLOCKED_NO_SITE_URL_NO_CREDENTIAL_"
        "PREFLIGHT_NO_NETWORK_AUTHORITY"
    )
    assert result["base_url_present"] is False
    assert result["credential_file_touched"] is False
    assert result["http_request_performed"] is False
    assert result["execution_approval_issued"] is False
    assert result["approval_token_present"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_CREDENTIAL_ISOLATED_READ_ONLY_"
        "PREFLIGHT_DESIGN_NO_ACCESS"
    )
    assert result["http_method"] == "GET"
    assert result["base_url_present"] is False
    assert result["credential_file_touched"] is False
    assert result["credential_values_loaded"] is False
    assert result["environment_variables_read"] is False
    assert result["dns_resolution_performed"] is False
    assert result["http_request_performed"] is False
    assert result["ready_for_ls_new_batch_4f"] is True
    assert result["ready_for_production_read_only_lookup"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Credential read allowed: `false`" in report
    assert "DNS resolution allowed: `false`" in report
    assert "WordPress API call allowed: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
