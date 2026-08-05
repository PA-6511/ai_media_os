import json
from pathlib import Path

from phase33.reporting.phase33_report import write_phase33_report


def test_phase33_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase33.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase33_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_approval_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_APPROVAL_PACKAGE_READY"
        },
        "final_approval_controls": {"status": "FINAL_APPROVAL_CONTROLS_READY"},
        "final_approval_stop_conditions": {
            "status": "FINAL_APPROVAL_STOP_CONDITIONS_READY"
        },
        "final_approval_evidence_requirements": {
            "status": "FINAL_APPROVAL_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_approval": {"status": "MANUAL_GATE_FINAL_APPROVAL_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase33_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "33"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
