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
    "new_release_wp_production_category_"
    "mapping_fixation_policy.json"
)
MAPPING_PATH = (
    ROOT
    / "config/"
    "new_release_wp_production_category_mapping.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_"
    "mapping_fixation_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_production_category_"
    "mapping_fixation_package.example.json"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_d_"
    "mapping_fixation_approval.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_d_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_d_"
    "mapping_fixation_report.md"
)
BUILDER_PATH = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_d.py"
)
BLOCKED_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_d_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_recovery_d_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def test_policy_fixes_exact_mapping() -> None:
    policy = load_json(POLICY_PATH)
    mapping = policy["mapping_contract"]

    assert (
        mapping["mapping_id"]
        == (
            "COMIC_NEW_RELEASE_LATEST_VOLUME_"
            "TO_WP_CATEGORY_10"
        )
    )
    assert mapping["production_category_id"] == 10
    assert mapping["production_category_name"] == "最新巻"
    assert mapping["mapping_fixed"] is True
    assert (
        mapping["automatic_mapping_performed"]
        is False
    )
    assert (
        mapping[
            "production_category_id_payload_injection_allowed"
        ]
        is False
    )


def test_approval_records_exact_mapping() -> None:
    approval = load_json(APPROVAL_PATH)
    mapping = approval["approved_mapping"]

    assert (
        approval["approval_label"]
        == (
            "PRODUCTION_CATEGORY_MAPPING_"
            "FIXATION_APPROVED"
        )
    )
    assert approval["human_explicit_approval"] is True
    assert approval["approved_by"] == "HUMAN_OPERATOR"
    assert approval["execution_allowed"] is False
    assert mapping["production_category_id"] == 10
    assert mapping["production_category_name"] == "最新巻"
    assert mapping["mapping_fixation_approved"] is True
    assert mapping["payload_binding_approved"] is False
    assert mapping["payload_injection_allowed"] is False


def test_request_has_no_external_access() -> None:
    request = load_json(REQUEST_PATH)

    assert request["mapping_fixation_requested"] is True
    assert request["credential_file_read_requested"] is False
    assert request["network_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["payload_binding_requested"] is False
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )
    assert request["execution_requested"] is False


def test_wrong_category_id_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request["mapping"]["production_category_id"] = 15

    try:
        builder.validate_request(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "category ID mismatch" in str(exc)
    else:
        raise AssertionError(
            "wrong category ID was accepted"
        )


def test_wrong_category_name_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request[
        "mapping"
    ]["production_category_name"] = "作品紹介"

    try:
        builder.validate_request(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "category name mismatch" in str(exc)
    else:
        raise AssertionError(
            "wrong category name was accepted"
        )


def test_automatic_mapping_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request[
        "automatic_category_mapping_requested"
    ] = True

    try:
        builder.validate_request(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "automatic mapping was accepted"
        )


def test_payload_binding_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request["payload_binding_requested"] = True

    try:
        builder.validate_request(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "payload binding was accepted"
        )


def test_mapping_artifact_is_fixed_and_safe() -> None:
    mapping = load_json(MAPPING_PATH)

    assert mapping["production_category_id"] == 10
    assert mapping["production_category_name"] == "最新巻"
    assert mapping["mapping_fixed"] is True
    assert mapping["human_mapping_fixation_approved"] is True
    assert (
        mapping[
            "automatic_category_mapping_performed"
        ]
        is False
    )
    assert mapping["payload_binding_complete"] is False
    assert (
        mapping[
            "production_category_id_payload_injection_allowed"
        ]
        is False
    )
    assert mapping["wordpress_write_allowed"] is False
    assert mapping["execution_allowed"] is False
    assert (
        isinstance(
            mapping["mapping_artifact_digest_sha256"],
            str,
        )
        and len(
            mapping["mapping_artifact_digest_sha256"]
        )
        == 64
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
            "BLOCKED_PAYLOAD_BINDING_AND_WORDPRESS_"
            "EXECUTION_NOT_AUTHORIZED"
        )
    )
    assert result["production_category_id"] == 10
    assert result["production_category_mapping_fixed"] is True
    assert result["payload_binding_complete"] is False
    assert result["wordpress_write_performed"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["execution_allowed"] is False


def test_package_records_fixation_only() -> None:
    package = load_json(OUTPUT_PATH)
    decision = package[
        "mapping_fixation_decision"
    ]
    activity = package[
        "current_phase_activity"
    ]

    assert decision["production_category_id"] == 10
    assert decision["production_category_name"] == "最新巻"
    assert decision["mapping_fixed"] is True
    assert decision["payload_binding_complete"] is False
    assert (
        decision[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert activity["http_request_performed"] is False
    assert activity["wordpress_write_performed"] is False
    assert activity["production_payload_modified"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        result["status"]
        == (
            "PASS_PRODUCTION_CATEGORY_MAPPING_FIXED_"
            "NO_NETWORK_NO_PAYLOAD_INJECTION"
        )
    )
    assert result["production_category_id"] == 10
    assert result["production_category_name"] == "最新巻"
    assert (
        result["production_category_mapping_fixed"]
        is True
    )
    assert result["payload_binding_complete"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["production_payload_modified"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_e"
        ]
        is True
    )
    assert result["ready_for_payload_binding_gate"] is True
    assert result["ready_for_payload_injection"] is False
    assert result["ready_for_execution"] is False

    assert "Production category ID: `10`" in report
    assert "Production category name: `最新巻`" in report
    assert "HTTP request performed: `false`" in report
    assert "Production category ID injected: `false`" in report
