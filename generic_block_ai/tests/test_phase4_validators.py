import json
from pathlib import Path

from generic_block_ai.app.connection_test_result_validator import validate_connection_test_result
from generic_block_ai.app.handoff_payload_validator import validate_handoff_payload
from generic_block_ai.app.phase4_validator_runner import run_phase4_validators


def _valid_handoff() -> dict:
    return {
        "handoff_contract": {
            "connection_test_mode": True,
            "connection_scope": "decision_package_handoff_only",
            "operation_mode": "OBSERVE",
            "execution": "dry_run",
            "requires_human_approval": True,
            "auto_execute_allowed": False,
            "transport": "none",
            "external_api_call": False,
        },
        "source": {
            "artifact_type": "decision_package",
            "artifact_path": "reports/phase35_decision_package.json",
        },
        "target": {
            "mode": "observation_only",
            "execution_permission": "none",
            "write_permission": "none",
        },
        "payload": {
            "decision_package_ref": "reports/phase35_decision_package.json",
            "blocked_actions": [
                "external_api_call",
                "wordpress_operation",
                "cron_registration",
                "auto_execute",
                "auto_post",
                "auto_update",
                "auto_delete",
                "auto_export",
                "production_execution",
            ],
            "required_review_state": "HUMAN_REVIEW_REQUIRED",
            "expected_core_ai_behavior": "observe_and_return_assessment_only",
        },
        "validation_expectations": {
            "must_not_trigger_execution": True,
            "must_not_create_external_request": True,
            "must_not_change_runtime_mode": True,
            "must_preserve_no_go_status": True,
        },
        "result": "PASS_DRY_RUN_ONLY",
    }


def _valid_connection_report() -> dict:
    return {
        "scope": {
            "connection_test_mode": True,
            "connection_scope": "decision_package_handoff_only",
            "operation_mode": "OBSERVE",
            "execution": "dry_run",
        },
        "verified_items": ["payload shape checked"],
        "unverified_items": ["real transport not tested"],
        "blocked_actions": [
            "external_api_call",
            "wordpress_operation",
            "cron_registration",
            "auto_execute",
            "auto_post",
            "auto_update",
            "auto_delete",
            "auto_export",
            "production_execution",
        ],
        "judgment": {
            "connection_test_status": "PASS_DRY_RUN_ONLY",
            "production_status": "NO_GO",
            "allowed_state": ["OBSERVE", "DRY_RUN", "HUMAN_REVIEW_REQUIRED"],
            "dangerous_operations_detected": False,
            "external_communication": False,
            "auto_execution": False,
        },
        "referenced_artifacts": [
            "reports/phase4_1_connection_policy_diff_plan.json",
            "reports/phase4_2_decision_package_handoff_payload.json",
        ],
    }


def test_valid_handoff_payload_passes():
    result = validate_handoff_payload(_valid_handoff())
    assert result.result == "PASS"


def test_handoff_payload_rejects_non_observe_mode():
    data = _valid_handoff()
    data["handoff_contract"]["operation_mode"] = "EXECUTE"
    result = validate_handoff_payload(data)
    assert result.result == "FAIL"
    assert any("operation_mode" in item for item in result.failed_checks)


def test_handoff_payload_rejects_missing_blocked_actions():
    data = _valid_handoff()
    data["payload"]["blocked_actions"] = ["external_api_call"]
    result = validate_handoff_payload(data)
    assert result.result == "FAIL"


def test_handoff_payload_warns_for_non_pass_dry_run_only_result():
    data = _valid_handoff()
    data["result"] = "PASS"
    result = validate_handoff_payload(data)
    assert result.result == "WARN"


def test_valid_connection_test_report_passes():
    result = validate_connection_test_result(_valid_connection_report())
    assert result.result == "PASS"


def test_connection_test_report_rejects_non_no_go():
    data = _valid_connection_report()
    data["judgment"]["production_status"] = "GO"
    result = validate_connection_test_result(data)
    assert result.result == "FAIL"
    assert any("production_status" in item for item in result.failed_checks)


def test_connection_test_report_rejects_missing_allowed_state():
    data = _valid_connection_report()
    data["judgment"]["allowed_state"] = ["OBSERVE"]
    result = validate_connection_test_result(data)
    assert result.result == "FAIL"


def test_connection_test_report_warns_when_unverified_items_missing():
    data = _valid_connection_report()
    data["unverified_items"] = []
    result = validate_connection_test_result(data)
    assert result.result == "WARN"


def test_phase4_runner_passes_against_repo_templates():
    report = run_phase4_validators(Path("generic_block_ai"))
    assert report["overall_result"] == "PASS"
    assert len(report["validations"]) == 2


def test_repo_phase4_json_files_are_valid_json():
    paths = [
        Path("generic_block_ai/reports/phase4_1_connection_policy_diff_plan.json"),
        Path("generic_block_ai/reports/phase4_2_decision_package_handoff_payload.json"),
        Path("generic_block_ai/reports/phase4_3_limited_connection_test_report.json"),
    ]
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            json.load(handle)
