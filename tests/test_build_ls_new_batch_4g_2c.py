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
    "new_release_wp_category_candidate_search_authorization_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_candidate_search_authorization_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_candidate_search_authorization_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2c_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2c_category_candidate_search_authorization_report.md"
)
BUILDER_PATH = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2c.py"
)
BLOCKED_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2c_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4g_2c_test",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def test_policy_fixes_candidate_search_scope() -> None:
    policy = load_json(POLICY_PATH)
    scope = policy["planned_http_scope"]

    assert scope["maximum_http_requests"] == 1
    assert scope["maximum_attempts"] == 1
    assert scope["retry_allowed"] is False
    assert scope["method"] == "GET"
    assert (
        scope["rest_path"]
        == "/wp-json/wp/v2/categories"
    )
    assert (
        scope["query_parameters"]["search"]
        == "コミック新刊"
    )
    assert scope["request_body_allowed"] is False
    assert scope["redirect_follow_allowed"] is False
    assert scope["proxy_use_allowed"] is False


def test_previous_one_shot_remains_consumed() -> None:
    package = load_json(OUTPUT_PATH)
    previous = package[
        "previous_attempt_state"
    ]

    assert previous["approval_consumed"] is True
    assert previous["approval_reusable"] is False
    assert (
        previous["one_shot_lock_state"]
        == "CONSUMED_COMPLETED_BLOCKED"
    )
    assert previous["lock_deletion_allowed"] is False
    assert previous["lock_reuse_allowed"] is False


def test_new_approval_is_not_issued() -> None:
    package = load_json(OUTPUT_PATH)
    gate = package["approval_gate"]

    assert (
        gate["state"]
        == "AWAITING_EXPLICIT_APPROVAL"
    )
    assert gate["approval_label_issued"] is False
    assert gate["approval_label_consumed"] is False
    assert gate["actual_go_decision_issued"] is False
    assert gate["approval_token"] is None
    assert gate["execution_allowed"] is False


def test_request_has_no_access() -> None:
    request = load_json(REQUEST_PATH)

    assert request["credential_file_read_requested"] is False
    assert request["network_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_response_read_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["automatic_candidate_selection_requested"] is False
    assert request["automatic_category_mapping_requested"] is False
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )


def test_post_method_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)
    request["requested_approval_scope"][
        "method"
    ] = "POST"

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "method must be GET" in str(exc)
    else:
        raise AssertionError("POST was accepted")


def test_wrong_search_term_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)
    request["requested_approval_scope"][
        "query_parameters"
    ]["search"] = "別カテゴリ"

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "query parameters mismatch" in str(exc)
    else:
        raise AssertionError(
            "wrong search term was accepted"
        )


def test_multiple_requests_are_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)
    request["requested_approval_scope"][
        "maximum_http_requests"
    ] = 2

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "request-count mismatch" in str(exc)
    else:
        raise AssertionError(
            "multiple requests were accepted"
        )


def test_network_request_is_rejected() -> None:
    builder = load_builder()
    request = load_json(REQUEST_PATH)
    request["http_request_requested"] = True

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "network request was accepted"
        )


def test_blocked_runner_returns_three() -> None:
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
        == (
            "BLOCKED_AWAITING_EXPLICIT_"
            "CATEGORY_CANDIDATE_SEARCH_APPROVAL"
        )
    )
    assert result["previous_approval_consumed"] is True
    assert result["previous_approval_reusable"] is False
    assert result["approval_label_issued"] is False
    assert result["http_request_performed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        result["status"]
        == (
            "PASS_CATEGORY_CANDIDATE_SEARCH_"
            "AUTHORIZATION_GATE_READY_NO_NETWORK"
        )
    )
    assert (
        result["decision"]
        == (
            "AWAITING_EXPLICIT_APPROVAL_FOR_"
            "ONE_SHOT_CATEGORY_SEARCH_GET"
        )
    )
    assert result["approval_label_issued"] is False
    assert result["http_request_performed"] is False
    assert result["candidate_selected"] is False
    assert result["category_mapping_fixed"] is False
    assert result["production_payload_modified"] is False
    assert (
        result[
            "ready_for_explicit_candidate_search_approval"
        ]
        is True
    )
    assert result["ready_for_ls_new_batch_4g_2d"] is False
    assert result["ready_for_execution"] is False

    assert "Previous approval consumed: `true`" in report
    assert "HTTP request performed: `false`" in report
    assert "Execution allowed: `false`" in report
