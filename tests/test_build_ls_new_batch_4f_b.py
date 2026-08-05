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
    "new_release_wp_production_credential_validator_design_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_validator_design_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_credential_validator_design_package.example.json"
)
RESULT_PATH = (
    ROOT / "exchange/logs/ls_new_batch_4f_b_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4f_b_production_credential_validator_design_report.md"
)
BUILDER_PATH = (
    ROOT / "scripts/build_ls_new_batch_4f_b.py"
)
BLOCKED_PATH = (
    ROOT / "scripts/execute_ls_new_batch_4f_b_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_ls_new_batch_4f_b_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_policy_is_design_only() -> None:
    policy = load_json(POLICY_PATH)
    boundary = policy["execution_boundary"]

    assert policy["phase_id"] == "LS-NEW-BATCH-4F-B"
    assert (
        boundary[
            "production_credential_exists_check_allowed"
        ]
        is False
    )
    assert boundary["production_credential_lstat_allowed"] is False
    assert boundary["production_credential_stat_allowed"] is False
    assert (
        boundary[
            "production_credential_metadata_read_allowed"
        ]
        is False
    )
    assert (
        boundary[
            "production_credential_content_read_allowed"
        ]
        is False
    )
    assert boundary["wordpress_api_call_allowed"] is False
    assert boundary["execution_allowed"] is False


def test_request_does_not_request_file_access() -> None:
    request = load_json(REQUEST_PATH)

    assert (
        request["design_mode"]
        == "PRODUCTION_CREDENTIAL_VALIDATOR_DESIGN_ONLY"
    )
    assert (
        request["production_file_exists_check_requested"]
        is False
    )
    assert request["production_file_lstat_requested"] is False
    assert request["production_file_stat_requested"] is False
    assert (
        request["production_file_metadata_read_requested"]
        is False
    )
    assert (
        request["production_file_content_open_requested"]
        is False
    )
    assert (
        request["production_file_content_read_requested"]
        is False
    )
    assert request["production_key_name_parse_requested"] is False
    assert request["secret_output_requested"] is False


def test_design_package_records_no_production_access() -> None:
    package = load_json(OUTPUT_PATH)

    assert package["production_credential_path_touched"] is False
    assert package["production_file_exists_checked"] is False
    assert package["production_file_lstat_performed"] is False
    assert package["production_file_stat_performed"] is False
    assert package["production_file_metadata_read"] is False
    assert package["production_file_content_opened"] is False
    assert package["production_file_content_read"] is False
    assert package["production_key_names_parsed"] is False
    assert package["production_empty_values_checked"] is False


def test_validator_plan_has_expected_contract() -> None:
    package = load_json(OUTPUT_PATH)
    plan = package["validator_plan"]

    assert (
        plan["target_path"]
        == "/etc/ai-media-os/"
        "wordpress-readonly-category.env"
    )
    assert plan["expected_owner"] == "deploy"
    assert plan["expected_group"] == "deploy"
    assert plan["required_mode_octal"] == "0600"
    assert plan["required_keys"] == [
        "WORDPRESS_BASE_URL",
        "WORDPRESS_READONLY_USERNAME",
        "WORDPRESS_READONLY_APP_PASSWORD"
    ]
    assert plan["credential_values_may_be_output"] is False
    assert plan["network_operations_allowed"] is False
    assert plan["wordpress_operations_allowed"] is False


def test_future_failure_behavior_is_fail_closed() -> None:
    package = load_json(OUTPUT_PATH)
    behavior = package[
        "validator_plan"
    ]["future_failure_behavior"]

    assert behavior
    assert set(behavior.values()) == {"BLOCK"}


def test_output_schema_contains_no_secret_value_field() -> None:
    package = load_json(OUTPUT_PATH)
    schema = package[
        "validator_plan"
    ]["future_output_schema"]

    assert "credential_values" not in schema
    assert "password" not in schema
    assert "username_value" not in schema
    assert schema["credential_values_output"] == "constant_false"
    assert schema["value_lengths_output"] == "constant_false"
    assert schema["value_hashes_output"] == "constant_false"


def test_non_false_access_request_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request[
        "production_file_exists_check_requested"
    ] = True

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "production exists check request was accepted"
        )


def test_wrong_production_path_is_rejected() -> None:
    builder = load_builder()

    request = load_json(REQUEST_PATH)
    request[
        "production_credential_path"
    ] = "/tmp/wrong.env"

    try:
        builder.build_package(
            request=request,
            policy=load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "production credential path mismatch" in str(exc)
    else:
        raise AssertionError(
            "wrong production path was accepted"
        )


def test_digests_are_deterministic() -> None:
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
        first["validator_plan"][
            "validator_plan_digest_sha256"
        ]
        == second["validator_plan"][
            "validator_plan_digest_sha256"
        ]
    )


def test_execution_runner_is_blocked() -> None:
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

    assert result["status"] == "BLOCKED_VALIDATOR_DESIGN_ONLY"
    assert result["validator_design_complete"] is True
    assert result["production_credential_path_touched"] is False
    assert result["production_file_exists_checked"] is False
    assert result["production_file_stat_performed"] is False
    assert result["production_file_content_read"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert (
        result["status"]
        == "PASS_PRODUCTION_CREDENTIAL_VALIDATOR_"
        "DESIGN_BLOCKED"
    )
    assert (
        result["decision"]
        == "NON_SECRET_VALIDATOR_PLAN_FIXED_"
        "PRODUCTION_FILE_UNTOUCHED"
    )
    assert result["validator_design_complete"] is True
    assert result["production_credential_path_touched"] is False
    assert result["production_file_exists_checked"] is False
    assert result["production_file_metadata_read"] is False
    assert result["production_file_content_read"] is False
    assert result["production_credential_presence_verified"] is False
    assert result["ready_for_ls_new_batch_4f_c"] is True
    assert result["ready_for_actual_non_secret_presence_check"] is False
    assert result["ready_for_execution"] is False
    assert result["next_phase_execution_allowed"] is False

    assert "Production path touched: `false`" in report
    assert "Exists check performed: `false`" in report
    assert "Content read: `false`" in report
    assert "WordPress API call allowed: `false`" in report
    assert "Execution allowed: `false`" in report
