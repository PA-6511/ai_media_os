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
    "new_release_wp_fresh_payload_binding_plan_policy.json"
)
PLAN_PATH = (
    ROOT
    / "config/"
    "new_release_wp_fresh_payload_binding_plan.json"
)
REQUEST_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_"
    "binding_plan_request.example.json"
)
OUTPUT_PATH = (
    ROOT
    / "exchange/examples/"
    "new_release_wp_fresh_payload_"
    "binding_plan_package.example.json"
)
APPROVAL_PATH = (
    ROOT
    / "exchange/approvals/"
    "ls_new_batch_4g_2e_recovery_e_"
    "fresh_payload_binding_plan_approval.json"
)
RESULT_PATH = (
    ROOT
    / "exchange/logs/"
    "ls_new_batch_4g_2e_recovery_e_result.json"
)
REPORT_PATH = (
    ROOT
    / "reports/"
    "ls_new_batch_4g_2e_recovery_e_"
    "fresh_payload_binding_plan_report.md"
)
BUILDER_PATH = (
    ROOT
    / "scripts/"
    "build_ls_new_batch_4g_2e_recovery_e.py"
)
BLOCKED_PATH = (
    ROOT
    / "scripts/"
    "execute_ls_new_batch_4g_2e_recovery_e_blocked.py"
)


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_recovery_e_test_module",
        BUILDER_PATH,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )
    spec.loader.exec_module(module)
    return module


def test_policy_records_plan_only() -> None:
    policy = load_json(POLICY_PATH)

    assert (
        policy["operation_mode"]
        == (
            "APPROVED_FRESH_PAYLOAD_BINDING_"
            "PLAN_RECORDING_ONLY"
        )
    )
    assert (
        policy["execution_boundary"][
            "fresh_payload_creation_allowed"
        ]
        is False
    )
    assert (
        policy["execution_boundary"][
            "payload_binding_allowed"
        ]
        is False
    )
    assert (
        policy["execution_boundary"][
            "wordpress_api_call_allowed"
        ]
        is False
    )


def test_approval_records_exact_plan() -> None:
    approval = load_json(APPROVAL_PATH)
    plan = approval["approved_plan"]

    assert (
        approval["approval_label"]
        == "FRESH_PAYLOAD_BINDING_PLAN_APPROVED"
    )
    assert approval["human_explicit_approval"] is True
    assert approval["execution_allowed"] is False
    assert plan["legacy_post185_lineage_excluded"] is True
    assert plan["production_category_id"] == 10
    assert (
        plan["binding_operation"]
        == "COPY_SOURCE_AND_SET_CATEGORIES_ONLY"
    )
    assert plan["payload_binding_approved"] is False
    assert plan["wordpress_write_approved"] is False


def test_legacy_sources_are_excluded() -> None:
    plan = load_json(PLAN_PATH)
    legacy = plan["legacy_exclusion"]

    assert legacy["legacy_post185_lineage_excluded"] is True
    assert legacy["legacy_wordpress_post_id"] == 185
    assert legacy["legacy_artifact_reuse_allowed"] is False
    assert legacy["legacy_artifact_modification_allowed"] is False
    assert (
        len(legacy["verified_inspection_evidence"])
        == 3
    )

    for item in legacy[
        "verified_inspection_evidence"
    ]:
        assert (
            item["independent_payload_path_found"]
            is False
        )
        assert item["payload_body_found"] is False
        assert item["categories_payload_found"] is False
        assert item["eligible_as_fresh_payload"] is False
        assert item["modification_allowed"] is False


def test_future_source_contract_is_strict() -> None:
    plan = load_json(PLAN_PATH)
    source = plan["future_source_contract"]

    assert source["required_status"] == "draft"
    assert source["source_must_remain_immutable"] is True
    assert source["source_must_not_be_result_log"] is True
    assert source["source_must_not_reference_post_185"] is True
    assert source["categories_allowed_before_binding"] == [
        "ABSENT",
        "EMPTY_LIST",
    ]


def test_offline_binding_contract_is_copy_only() -> None:
    plan = load_json(PLAN_PATH)
    binding = plan["offline_binding_contract"]

    assert (
        binding["operation"]
        == "COPY_SOURCE_AND_SET_CATEGORIES_ONLY"
    )
    assert binding["source_overwrite_allowed"] is False
    assert (
        binding["only_mutable_json_pointer"]
        == "/categories"
    )
    assert binding["categories_after_binding"] == [10]
    assert (
        binding["semantic_diff_must_be_categories_only"]
        is True
    )
    assert binding["wordpress_submission_allowed"] is False


def test_request_has_no_execution_activity() -> None:
    request = load_json(REQUEST_PATH)

    assert request["plan_recording_requested"] is True
    assert (
        request["legacy_post185_exclusion_requested"]
        is True
    )
    assert request["fresh_payload_creation_requested"] is False
    assert request["fresh_payload_read_requested"] is False
    assert request["fresh_payload_copy_requested"] is False
    assert request["payload_binding_requested"] is False
    assert (
        request[
            "production_category_id_payload_injection_requested"
        ]
        is False
    )
    assert request["network_connection_requested"] is False
    assert request["wordpress_write_requested"] is False
    assert request["execution_requested"] is False


def test_payload_binding_request_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request["payload_binding_requested"] = True

    try:
        builder.validate_request_and_sources(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "payload binding was accepted"
        )


def test_category_injection_request_is_rejected() -> None:
    builder = load_builder()
    request = copy.deepcopy(
        load_json(REQUEST_PATH)
    )
    request[
        "production_category_id_payload_injection_requested"
    ] = True

    try:
        builder.validate_request_and_sources(
            request,
            load_json(POLICY_PATH),
        )
    except builder.ValidationError as exc:
        assert "must remain false" in str(exc)
    else:
        raise AssertionError(
            "category injection was accepted"
        )


def test_plan_artifact_is_fixed_and_safe() -> None:
    plan = load_json(PLAN_PATH)

    assert (
        plan["plan_id"]
        == (
            "FRESH_NEW_RELEASE_PAYLOAD_OFFLINE_"
            "CATEGORY_BINDING_PLAN_V1"
        )
    )
    assert plan["mapping"]["production_category_id"] == 10
    assert plan["mapping"]["mapping_fixed"] is True
    assert (
        plan["current_state"]["fresh_payload_exists"]
        is False
    )
    assert (
        plan["current_state"]["payload_binding_complete"]
        is False
    )
    assert (
        plan["current_state"]["category_id_injected"]
        is False
    )
    assert (
        plan["current_state"]["execution_allowed"]
        is False
    )
    assert (
        isinstance(
            plan["plan_artifact_digest_sha256"],
            str,
        )
        and len(plan["plan_artifact_digest_sha256"])
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
            "BLOCKED_FRESH_PAYLOAD_CREATION_BINDING_"
            "AND_WORDPRESS_EXECUTION_NOT_AUTHORIZED"
        )
    )
    assert result["fresh_payload_created"] is False
    assert result["payload_binding_complete"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["wordpress_write_performed"] is False
    assert result["execution_allowed"] is False


def test_result_and_report_are_complete() -> None:
    result = load_json(RESULT_PATH)
    report = REPORT_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        result["status"]
        == (
            "PASS_FRESH_PAYLOAD_BINDING_PLAN_FIXED_"
            "NO_PAYLOAD_NO_NETWORK"
        )
    )
    assert result["legacy_post185_lineage_excluded"] is True
    assert result["production_category_id"] == 10
    assert result["fresh_payload_created"] is False
    assert result["fresh_payload_read"] is False
    assert result["fresh_payload_copied"] is False
    assert result["payload_binding_complete"] is False
    assert result["payload_modified"] is False
    assert (
        result[
            "production_category_id_payload_injected"
        ]
        is False
    )
    assert result["network_connection_performed"] is False
    assert result["wordpress_write_performed"] is False
    assert (
        result[
            "ready_for_ls_new_batch_4g_2e_recovery_f"
        ]
        is True
    )
    assert (
        result[
            "ready_for_fresh_payload_generation"
        ]
        is False
    )
    assert result["ready_for_execution"] is False

    assert "Legacy post185 lineage excluded: `true`" in report
    assert "Fresh payload created: `false`" in report
    assert "Category ID injected: `false`" in report
    assert "WordPress write performed: `false`" in report
