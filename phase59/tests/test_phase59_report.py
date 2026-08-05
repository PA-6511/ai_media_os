import json
from pathlib import Path

from phase59.reporting.phase59_report import write_phase59_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase59_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "operation_plan_package": {"status": "OPERATION_PLAN_PACKAGE_READY"},
        "operation_plan_controls": {"status": "OPERATION_PLAN_CONTROLS_READY"},
        "operation_plan_stop_conditions": {"status": "OPERATION_PLAN_STOP_CONDITIONS_READY"},
        "operation_plan_evidence_requirements": {
            "status": "OPERATION_PLAN_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_operation_plan": {"status": "MANUAL_GATE_OPERATION_PLAN_READY"},
        "selected_decision": "REJECT",
    }


def test_phase59_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase59.json"
    result = write_phase59_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase59_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase59.json"
    write_phase59_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "59"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
