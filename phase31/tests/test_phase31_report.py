import json
from pathlib import Path

from phase31.reporting.phase31_report import write_phase31_report


def test_phase31_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase31.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase31_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "pre_execution_control_design": {
            "status": "PRE_EXECUTION_CONTROL_DESIGN_READY"
        },
        "stop_conditions": {"status": "STOP_CONDITIONS_READY"},
        "evidence_requirements": {"status": "EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_final_check": {"status": "MANUAL_GATE_FINAL_CHECK_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase31_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "31"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
