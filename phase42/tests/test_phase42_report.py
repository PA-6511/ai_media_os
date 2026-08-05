import json
from pathlib import Path

from phase42.reporting.phase42_report import write_phase42_report


def test_phase42_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase42.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase42_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_finalization_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_FINALIZATION_PACKAGE_READY"
        },
        "finalization_controls": {"status": "FINALIZATION_CONTROLS_READY"},
        "finalization_stop_conditions": {"status": "FINALIZATION_STOP_CONDITIONS_READY"},
        "finalization_evidence_requirements": {
            "status": "FINALIZATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_finalization": {"status": "MANUAL_GATE_FINALIZATION_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase42_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "42"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
