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
    "new_release_wp_category_index_human_review_policy.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_human_review_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_category_index_human_review_package.example.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_c_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_c_human_review_report.md"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_c_human_review_approval.json"
)
BUILDER_PATH = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_c.py"
)
BLOCKED_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_c_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_recovery_c_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def test_policy_fixes_human_selection() -> None:
    policy = load_json(POLICY_PATH)
    review = policy[
        "human_review_contract"
    ]

    assert (
        review["required_approval_label"]
        == "CATEGORY_INDEX_HUMAN_REVIEW_APPROVED"
    )
    assert review["selected_category_id"] == 10
    assert (
        review["selected_category_name"]
        == "最新巻"
    )
    assert review["human_selection_required"] is True
    assert review["automatic_selection_allowed"] is False


def test_approval_records_exact_selection() -> None:
    approval = load_json(APPROVAL_PATH)
    selection = approval["selection"]

    assert approval["human_explicit_approval"] is True
    assert approval["approved_by"] == "HUMAN_OPERATOR"
    assert approval["approval_reuse_allowed"] is False
    assert approval["execution_allowed"] is False
    assert selection["category_id"] == 10
    assert selection["category_name"] == "最新巻"
    assert selection["human_selected"] is True
    assert (
        selection["automatic_selection_performed"]
        is False
    )
    assert selection["category_mapping_fixed"] is False
    assert selection["payload_injection_allowed"] is False


def test_request_has_no_access_or_injection() -> None:
    request = load_json(REQUEST_PATH)

    assert request["human_selection_recording_requested"] is True
    assert request["credential_file_read_requested"] is False
    assert request["network_connection_requested"] is False
    assert request["http_request_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert (
        request[
            "automatic_category_selection_requested"
        ]
        is False
    )
    assert (
        request[
            "category_mapping_fixation_requested"
        ]
        is False
    )
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )


def test_wrong_category_id_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request["selected_category"]["id"] = 15

    try:
        builder.build_package(
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
        "selected_category"
    ]["name"] = "作品紹介"

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "category name mismatch" in str(exc)
    else:
        raise AssertionError(
            "wrong category name was accepted"
        )


def test_automatic_selection_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request[
        "automatic_category_selection_requested"
    ] = True

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "automatic selection was accepted"
        )


def test_payload_injection_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request[
        "production_category_id_payload_injection_requested"
    ] = True

    try:
        builder.build_package(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "payload injection was accepted"
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
            "BLOCKED_CATEGORY_MAPPING_FIXATION_"
            "NOT_AUTHORIZED_IN_HUMAN_REVIEW_PHASE"
        )
    )
    assert result["selected_category_id"] == 10
    assert result["human_selection_recorded"] is True
    assert result["category_mapping_fixed"] is False
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_package_records_human_selection_only() -> None:
    package = load_json(OUTPUT_PATH)
    decision = package[
        "human_selection_decision"
    ]
    activity = package[
        "current_phase_activity"
    ]

    assert decision["category_id"] == 10
    assert decision["category_name"] == "最新巻"
    assert decision["human_selected"] is True
    assert (
        decision["automatic_selection_performed"]
        is False
    )
    assert decision["category_mapping_fixed"] is False
    assert decision["payload_injection_allowed"] is False
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
            "PASS_CATEGORY_INDEX_HUMAN_REVIEW_"
            "RECORDED_NO_NETWORK"
        )
    )
    assert result["selected_category_id"] == 10
    assert result["selected_category_name"] == "最新巻"
    assert result["human_selection_recorded"] is True
    assert (
        result[
            "automatic_category_selection_performed"
        ]
        is False
    )
    assert result["category_mapping_fixed"] is False
    assert result["http_request_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_d"
        ]
        is True
    )
    assert result["ready_for_payload_injection"] is False
    assert result["ready_for_execution"] is False

    assert "Category ID: `10`" in report
    assert "Category name: `最新巻`" in report
    assert "HTTP request performed: `false`" in report
    assert "WordPress write performed: `false`" in report
