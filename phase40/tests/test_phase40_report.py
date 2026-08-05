import json
from pathlib import Path

from phase40.reporting.phase40_report import write_phase40_report


def test_phase40_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase40.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase40_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_validation_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_VALIDATION_PACKAGE_READY"
        },
        "validation_controls": {"status": "VALIDATION_CONTROLS_READY"},
        "validation_stop_conditions": {"status": "VALIDATION_STOP_CONDITIONS_READY"},
        "validation_evidence_requirements": {
            "status": "VALIDATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_validation": {"status": "MANUAL_GATE_VALIDATION_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase40_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "40"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
