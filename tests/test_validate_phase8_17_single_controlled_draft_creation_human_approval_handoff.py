"""Tests for Phase 8-17 single controlled draft creation human approval handoff."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_17_single_controlled_draft_creation_human_approval_handoff_report import (  # noqa: E402
    generate_phase8_17_single_controlled_draft_creation_human_approval_handoff_report,
)
from validate_phase8_17_single_controlled_draft_creation_human_approval_handoff import (  # noqa: E402
    validate_phase8_17_single_controlled_draft_creation_human_approval_handoff,
)


def base_policy() -> dict:
    return {
        "phase": "8-17",
        "phase_name": "Single controlled draft creation human approval handoff",
        "phase_status": "DESIGN_HANDOFF_ONLY",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "required_previous_evidence": [
            "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_result.json",
            "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.json",
            "exchange/logs/phase8_16_credential_readiness_no_secret_leak_final_gate_report.md",
        ],
        "accepted_phase8_16_statuses": [
            "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
            "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
        ],
        "execution_allowed_in_phase8_17": False,
        "required_false_flags": [
            "wordpress_api_call_allowed",
            "wordpress_api_call_attempted",
            "wordpress_write_allowed",
            "wordpress_write_executed",
            "wordpress_draft_created",
            "publish_allowed",
            "update_allowed",
            "delete_allowed",
            "bulk_action_allowed",
            "export_allowed",
            "auto_post",
            "auto_update",
            "auto_delete",
            "auto_export",
            "approve_draft_create_only_currently_allowed",
            "unlock_in_this_phase",
            "executor_action_allowed",
            "secret_values_output",
            "secret_values_written",
            "secret_values_logged",
        ],
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_action_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "executor_action_allowed": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "no_secret_leak_detection": {
            "forbidden_markers": [
                "authorization:",
                "bearer ",
                "basic ",
                "cookie:",
                "password=",
                "token=",
                "webhook=",
                "api_key=",
                "client_secret=",
            ]
        },
    }


def base_request() -> dict:
    return {
        "mode": "SINGLE_CONTROLLED_DRAFT_CREATION_HUMAN_APPROVAL_HANDOFF",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "target_item_count": 1,
        "credential_check_only": False,
        "handoff_only": True,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_draft_creation_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "no_secret_leak_required": True,
        "previous_phase": "8-16",
        "required_previous_final_status": [
            "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
            "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
        ],
        "current_expected_previous_final_status": "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
        "next_step_if_credentials_not_ready": "manual_credential_provisioning_then_repeat_credential_readiness_gate",
        "next_step_if_credentials_ready_and_human_approved": "phase8_18_single_controlled_wordpress_draft_creation_execution",
        "next_step_if_human_rejected": "stop_without_execution",
        "next_step_if_policy_violation": "abort_without_execution",
    }


def base_human() -> dict:
    return {
        "phase": "8-17",
        "approval_scope": "HANDOFF_ONLY_NO_EXECUTION",
        "decision": "APPROVE_HANDOFF_ONLY",
        "allowed_decisions": ["APPROVE_HANDOFF_ONLY", "REQUEST_FIX", "REJECT", "ABORT"],
        "target_item_count": 1,
        "human_approval_required": True,
        "human_approved": True,
        "approved_for_wordpress_api_call": False,
        "approved_for_wordpress_write": False,
        "approved_for_draft_creation": False,
        "approved_for_publish": False,
        "approved_for_update": False,
        "approved_for_delete": False,
        "approved_for_export": False,
        "approved_for_unlock": False,
        "secret_values_included": False,
        "operator_note": "handoff only",
    }


def _write_phase816_evidence(base: Path, final_status: str, no_secret_ok: bool = True, extra: dict | None = None) -> None:
    logs = base / "exchange" / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    payload = {
        "phase": "8-16",
        "final_status": final_status,
        "credentials_ready": final_status == "CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
        "no_secret_leak_passed": no_secret_ok,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "secret_leak_findings": [],
    }
    if extra:
        payload.update(extra)

    (logs / "phase8_16_credential_readiness_no_secret_leak_final_gate_result.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    (logs / "phase8_16_credential_readiness_no_secret_leak_final_gate_report.json").write_text(
        json.dumps({"final_status": final_status}), encoding="utf-8"
    )
    (logs / "phase8_16_credential_readiness_no_secret_leak_final_gate_report.md").write_text(
        "# phase8-16 report\n", encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    previous_status: str = "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    policy_overrides: dict | None = None,
    request_overrides: dict | None = None,
    human_overrides: dict | None = None,
    missing_evidence: bool = False,
    no_secret_ok: bool = True,
    extra_previous_payload: dict | None = None,
):
    policy = copy.deepcopy(base_policy())
    request = copy.deepcopy(base_request())
    human = copy.deepcopy(base_human())

    if policy_overrides:
        policy.update(policy_overrides)
    if request_overrides:
        request.update(request_overrides)
    if human_overrides:
        human.update(human_overrides)

    policy_path = tmp_path / "config" / "policy.json"
    request_path = tmp_path / "exchange" / "examples" / "request.json"
    human_path = tmp_path / "exchange" / "examples" / "human.json"
    result_path = tmp_path / "exchange" / "logs" / "result.json"
    report_json_path = tmp_path / "exchange" / "logs" / "report.json"
    report_md_path = tmp_path / "exchange" / "logs" / "report.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    human_path.parent.mkdir(parents=True, exist_ok=True)

    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")
    human_path.write_text(json.dumps(human), encoding="utf-8")

    if not missing_evidence:
        _write_phase816_evidence(tmp_path, previous_status, no_secret_ok=no_secret_ok, extra=extra_previous_payload)

    result = validate_phase8_17_single_controlled_draft_creation_human_approval_handoff(
        policy_path=policy_path,
        request_path=request_path,
        human_approval_path=human_path,
        output_json_path=result_path,
    )
    report = generate_phase8_17_single_controlled_draft_creation_human_approval_handoff_report(
        result_json_path=result_path,
        output_json_path=report_json_path,
        output_md_path=report_md_path,
    )
    return result, report, result_path, report_json_path, report_md_path


def test_not_ready_approve_handoff_only(tmp_path):
    result, _, _, _, _ = run_case(tmp_path)
    assert result["final_status"] == "PASS_HANDOFF_ONLY_CREDENTIALS_NOT_READY"
    assert result["execution_allowed"] is False
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_draft_created"] is False


def test_ready_approve_handoff_only(tmp_path):
    result, _, _, _, _ = run_case(
        tmp_path,
        previous_status="CREDENTIALS_READY_NO_SECRET_LEAK_PASS",
    )
    assert result["final_status"] == "PASS_HANDOFF_ONLY_CREDENTIALS_READY"
    assert result["execution_allowed"] is False
    assert result["next_step"] == "phase8_18_single_controlled_wordpress_draft_creation_execution"
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_draft_created"] is False


def test_missing_phase816_evidence(tmp_path):
    result, _, _, _, _ = run_case(tmp_path, missing_evidence=True)
    assert result["final_status"] == "ABORT_MISSING_PHASE8_16_EVIDENCE"
    assert result["execution_allowed"] is False


def test_required_false_flag_true_aborts_policy_violation(tmp_path):
    result, _, _, _, _ = run_case(
        tmp_path,
        policy_overrides={"wordpress_api_call_allowed": True},
    )
    assert result["final_status"] == "ABORT_POLICY_VIOLATION"
    assert result["execution_allowed"] is False


def test_request_fix_decision(tmp_path):
    result, _, _, _, _ = run_case(tmp_path, human_overrides={"decision": "REQUEST_FIX"})
    assert result["final_status"] == "WARN_REQUEST_FIX_NO_EXECUTION"
    assert result["execution_allowed"] is False


def test_reject_decision(tmp_path):
    result, _, _, _, _ = run_case(tmp_path, human_overrides={"decision": "REJECT"})
    assert result["final_status"] == "FAIL_REJECTED_BY_HUMAN_NO_EXECUTION"
    assert result["execution_allowed"] is False


def test_abort_decision(tmp_path):
    result, _, _, _, _ = run_case(tmp_path, human_overrides={"decision": "ABORT"})
    assert result["final_status"] == "ABORT_BY_HUMAN_NO_EXECUTION"
    assert result["execution_allowed"] is False


def test_unknown_decision(tmp_path):
    result, _, _, _, _ = run_case(
        tmp_path,
        human_overrides={"decision": "UNKNOWN_DECISION"},
    )
    assert result["final_status"] == "ABORT_UNKNOWN_DECISION_NO_EXECUTION"
    assert result["execution_allowed"] is False


def test_target_item_count_must_be_one(tmp_path):
    result, _, _, _, _ = run_case(tmp_path, request_overrides={"target_item_count": 2})
    assert result["final_status"] == "ABORT_POLICY_VIOLATION"
    assert result["execution_allowed"] is False


def test_secret_like_value_not_in_result_or_report(tmp_path):
    dummy_secret = "Authorization: Basic NEVER_OUTPUT_THIS token=ABC"
    result, report, result_path, report_json_path, report_md_path = run_case(
        tmp_path,
        extra_previous_payload={"debug_note": dummy_secret},
    )

    texts = [
        json.dumps(result, ensure_ascii=False),
        json.dumps(report, ensure_ascii=False),
        result_path.read_text(encoding="utf-8"),
        report_json_path.read_text(encoding="utf-8"),
        report_md_path.read_text(encoding="utf-8"),
    ]
    for text in texts:
        assert dummy_secret not in text


def test_report_generator_outputs_expected_fields(tmp_path):
    result, report, _, _, report_md_path = run_case(tmp_path)
    md = report_md_path.read_text(encoding="utf-8")
    assert "final_status" in report
    assert result["final_status"] in md
    assert "WordPress API call not executed" in md
    assert "wordpress" in md.lower()
