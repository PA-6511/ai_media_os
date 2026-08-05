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
    "new_release_wp_actual_read_only_lookup_authorization_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_actual_read_only_lookup_authorization_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_actual_read_only_lookup_authorization_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2a_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2a_actual_read_only_lookup_authorization_report.md"
)
BUILDER_PATH = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2a.py"
)
BLOCKED_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2a_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4g_2a_test_module",
        BUILDER_PATH,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)

    return module


def test_policy_fixes_exact_one_shot_scope() -> None:
    policy = load_json(POLICY_PATH)
    scope = policy["one_shot_http_scope"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4G-2A"
    assert scope["maximum_http_requests"] == 1
    assert scope["maximum_attempts"] == 1
    assert scope["retry_allowed"] is False
    assert scope["allowed_method"] == "GET"
    assert (
        scope["allowed_rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert scope["request_body_allowed"] is False
    assert scope["redirect_follow_allowed"] is False
    assert scope["proxy_use_allowed"] is False
    assert scope["tls_verification_required"] is True
    assert scope["https_required"] is True


def test_policy_keeps_approval_unissued() -> None:
    approval = load_json(POLICY_PATH)[
        "requested_approval"
    ]

    assert approval["approval_label_issued"] is False
    assert approval["approval_label_consumed"] is False
    assert approval["actual_go_decision_issued"] is False
    assert (
        approval["approval_token_generation_allowed"]
        is False
    )
    assert approval["approval_token_present"] is False
    assert (
        approval["human_explicit_approval_required"]
        is True
    )


def test_request_does_not_request_execution() -> None:
    request = load_json(REQUEST_PATH)

    assert request["credential_file_read_requested"] is False
    assert request["authorization_header_construction_requested"] is False
    assert request["dns_resolution_requested"] is False
    assert request["network_connection_requested"] is False
    assert request["tls_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_response_read_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["approval_label_issued"] is False
    assert request["actual_go_decision_issued"] is False
    assert request["approval_token"] is None
    assert request["execution_requested"] is False


def test_fixture_category_id_is_not_authorized() -> None:
    package = load_json(OUTPUT_PATH)
    fixture = package[
        "source_mock_mapping_summary"
    ]
    scope = package[
        "authorization_scope"
    ]

    assert fixture["fixture_category_id"] == 980001
    assert fixture["fixture_id_authorized"] is False
    assert fixture["fixture_id_production_usable"] is False
    assert fixture["fixture_id_payload_injection_allowed"] is False
    assert fixture["fixture_id_discard_required"] is True
    assert scope["fixture_category_id_authorized"] is False
    assert scope["fixture_category_id_discard_required"] is True


def test_post_method_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)

    request["requested_approval_scope"][
        "method"
    ] = "POST"

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "method must be GET" in str(exc)
    else:
        raise AssertionError(
            "POST method was accepted"
        )


def test_more_than_one_request_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)

    request["requested_approval_scope"][
        "maximum_http_requests"
    ] = 2

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert (
            "maximum HTTP requests mismatch"
            in str(exc)
        )
    else:
        raise AssertionError(
            "multiple HTTP requests were accepted"
        )


def test_retry_true_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)

    request["requested_approval_scope"][
        "retry_allowed"
    ] = True

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "retry must remain false" in str(exc)
    else:
        raise AssertionError(
            "retry=true was accepted"
        )


def test_premature_approval_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)

    request["approval_label_issued"] = True

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "premature approval was accepted"
        )


def test_network_request_is_rejected() -> None:
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
            "HTTP request was accepted in 2A"
        )


def test_package_digest_is_deterministic() -> None:
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

    assert len(
        first[
            "authorization_package_digest_sha256"
        ]
    ) == 64
    assert (
        first[
            "authorization_package_digest_sha256"
        ]
        == second[
            "authorization_package_digest_sha256"
        ]
    )
    assert (
        first["authorization_scope"][
            "authorization_scope_digest_sha256"
        ]
        == second["authorization_scope"][
            "authorization_scope_digest_sha256"
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

    result = json.loads(
        completed.stderr
    )

    assert (
        result["status"]
        == "BLOCKED_AWAITING_EXPLICIT_APPROVAL"
    )
    assert result["approval_label_issued"] is False
    assert result["actual_go_decision_issued"] is False
    assert result["approval_token_present"] is False
    assert result["maximum_http_requests"] == 1
    assert result["http_request_performed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        result["status"]
        == (
            "PASS_ONE_SHOT_READ_ONLY_LOOKUP_"
            "AUTHORIZATION_GATE_READY_NO_NETWORK"
        )
    )
    assert (
        result["decision"]
        == (
            "AWAITING_EXPLICIT_APPROVAL_"
            "FOR_ONE_SHOT_GET"
        )
    )
    assert (
        result["approval_gate_state"]
        == "AWAITING_EXPLICIT_APPROVAL"
    )
    assert result["approval_label_issued"] is False
    assert result["actual_go_decision_issued"] is False
    assert result["maximum_http_requests"] == 1
    assert result["retry_allowed"] is False
    assert result["fixture_category_id_authorized"] is False
    assert result["credential_file_read"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert (
        result[
            "ready_for_explicit_actual_lookup_approval"
        ]
        is True
    )
    assert result["ready_for_ls_new_batch_4g_2b"] is False
    assert result["ready_for_execution"] is False

    assert (
        "Approval label issued: `false`"
        in report
    )
    assert (
        "Maximum HTTP requests: `1`"
        in report
    )
    assert (
        "HTTP request performed: `false`"
        in report
    )
    assert (
        "WordPress write allowed: `false`"
        in report
    )
    assert (
        "Execution allowed: `false`"
        in report
    )
