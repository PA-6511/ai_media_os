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
    "new_release_wp_read_only_category_lookup_implementation_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_mock_request.example.json"
)
FIXTURE_PATH = (
    ROOT
    / "exchange/fixtures/wordpress_api/"
    "categories.comic-new-release.valid.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_read_only_category_lookup_mock_result.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4g_1_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_1_read_only_category_lookup_implementation_report.md"
)
LOOKUP_PATH = (
    ROOT / "scripts/wordpress_readonly_category_lookup.py"
)
BUILDER_PATH = ROOT / "scripts/build_ls_new_batch_4g_1.py"
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4g_1_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_is_mock_only_and_no_network() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4G-1"
    assert policy["operation_mode"] == "LOCAL_WORDPRESS_API_MOCK_ONLY"
    assert boundary["local_mock_read_allowed"] is True
    assert boundary["credential_file_content_read_allowed"] is False
    assert boundary["dns_resolution_allowed"] is False
    assert boundary["network_connection_allowed"] is False
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["wordpress_write_allowed"] is False
    assert boundary["execution_allowed"] is False


def test_request_does_not_request_external_access() -> None:
    request = load_json(REQUEST_PATH)

    assert request["credential_file_read_requested"] is False
    assert request["dns_resolution_requested"] is False
    assert request["network_connection_requested"] is False
    assert request["tls_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_response_read_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["automatic_payload_injection_requested"] is False


def test_valid_fixture_contract() -> None:
    fixture = load_json(FIXTURE_PATH)
    request = fixture["request"]
    response = fixture["response"]

    assert fixture["source_type"] == "LOCAL_WORDPRESS_API_MOCK"
    assert request["method"] == "GET"
    assert request["rest_path"] == "/wp-json/wp/v2/categories"
    assert request["request_body"] is None
    assert request["authorization_header_present"] is False
    assert response["http_status"] == 200
    assert response["content_type"] == "application/json"
    assert 980000 <= response["body"][0]["id"] <= 989999
    assert fixture["production_usable"] is False
    assert fixture["payload_injection_allowed"] is False


def test_mock_lookup_matches_exact_category() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "wordpress_readonly_category_lookup_test",
    )

    result = lookup.execute_local_mock_lookup(
        fixture=load_json(FIXTURE_PATH),
        targets=[
            {
                "category_slug": "comic-new-release",
                "category_name": "コミック新刊",
            }
        ],
        policy=load_json(POLICY_PATH),
    )

    mapping = result["mappings"][0]

    assert result["mapping_count"] == 1
    assert mapping["category_slug"] == "comic-new-release"
    assert mapping["category_name"] == "コミック新刊"
    assert mapping["candidate_fixture_category_id"] == 980001
    assert mapping["match_state"] == "MATCHED_LOCAL_MOCK_ONLY"
    assert mapping["production_usable"] is False
    assert mapping["payload_injection_allowed"] is False
    assert result["http_request_performed"] is False


def test_missing_category_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_missing_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["response"]["body"] = []

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "category not found" in str(exc)
    else:
        raise AssertionError("missing category was accepted")


def test_duplicate_category_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_duplicate_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["response"]["body"].append(
        copy.deepcopy(fixture["response"]["body"][0])
    )

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "duplicate category result" in str(exc)
    else:
        raise AssertionError("duplicate category was accepted")


def test_name_mismatch_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_name_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["response"]["body"][0]["name"] = "別カテゴリ"

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "category name mismatch" in str(exc)
    else:
        raise AssertionError("name mismatch was accepted")


def test_invalid_fixture_id_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_id_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["response"]["body"][0]["id"] = 42

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "outside reserved fixture range" in str(exc)
    else:
        raise AssertionError("non-reserved fixture ID was accepted")


def test_post_method_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_method_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["request"]["method"] = "POST"

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "method mismatch" in str(exc)
    else:
        raise AssertionError("POST method was accepted")


def test_query_mismatch_is_rejected() -> None:
    lookup = load_module(
        LOOKUP_PATH,
        "lookup_query_test",
    )
    fixture = load_json(FIXTURE_PATH)
    fixture["request"]["query_parameters"]["slug"] = "wrong-slug"

    try:
        lookup.execute_local_mock_lookup(
            fixture=fixture,
            targets=[
                {
                    "category_slug": "comic-new-release",
                    "category_name": "コミック新刊",
                }
            ],
            policy=load_json(POLICY_PATH),
        )
    except lookup.LookupValidationError as exc:
        assert "query does not match" in str(exc)
    else:
        raise AssertionError("query mismatch was accepted")


def test_package_digest_is_deterministic() -> None:
    builder = load_module(
        BUILDER_PATH,
        "build_ls_new_batch_4g_1_test",
    )

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
        first["implementation_package_digest_sha256"]
    ) == 64
    assert (
        first["implementation_package_digest_sha256"]
        == second["implementation_package_digest_sha256"]
    )
    assert (
        first["lookup_result"]["mappings"][0][
            "matched_mapping_digest_sha256"
        ]
        == second["lookup_result"]["mappings"][0][
            "matched_mapping_digest_sha256"
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

    assert result["status"] == "BLOCKED_LOCAL_MOCK_ONLY"
    assert result["implementation_verified"] is True
    assert result["fixture_category_ids_present"] is True
    assert result["fixture_category_ids_applied_to_payload"] is False
    assert result["production_category_ids_present"] is False
    assert result["http_request_performed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_READ_ONLY_CATEGORY_LOOKUP_"
        "IMPLEMENTATION_MOCK_ONLY"
    )
    assert result["transport"] == "LOCAL_JSON_MOCK"
    assert result["http_method"] == "GET"
    assert result["mapping_count"] == 1
    assert result["fixture_category_ids_present"] is True
    assert result["fixture_category_ids_applied_to_payload"] is False
    assert result["production_category_ids_present"] is False
    assert result["credential_file_read"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["ready_for_ls_new_batch_4g_2"] is True
    assert result["ready_for_actual_read_only_lookup"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Transport: `LOCAL_JSON_MOCK`" in report
    assert "HTTP request performed: `false`" in report
    assert "Production category IDs present: `false`" in report
    assert "WordPress write allowed: `false`" in report
    assert "Execution allowed: `false`" in report
