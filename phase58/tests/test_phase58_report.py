import json
from pathlib import Path

from phase58.reporting.phase58_report import write_phase58_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase58_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "execution_plan_package": {"status": "EXECUTION_PLAN_PACKAGE_READY"},
        "execution_plan_controls": {"status": "EXECUTION_PLAN_CONTROLS_READY"},
        "execution_plan_stop_conditions": {"status": "EXECUTION_PLAN_STOP_CONDITIONS_READY"},
        "execution_plan_evidence_requirements": {
            "status": "EXECUTION_PLAN_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_execution_plan": {"status": "MANUAL_GATE_EXECUTION_PLAN_READY"},
        "selected_decision": "REJECT",
    }


def test_phase58_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase58.json"
    result = write_phase58_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase58_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase58.json"
    write_phase58_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "58"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
