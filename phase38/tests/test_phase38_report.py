import json
from pathlib import Path

from phase38.reporting.phase38_report import write_phase38_report


def test_phase38_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase38.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase38_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_confirmation_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_CONFIRMATION_PACKAGE_READY"
        },
        "confirmation_controls": {"status": "CONFIRMATION_CONTROLS_READY"},
        "confirmation_stop_conditions": {"status": "CONFIRMATION_STOP_CONDITIONS_READY"},
        "confirmation_evidence_requirements": {
            "status": "CONFIRMATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_confirmation": {"status": "MANUAL_GATE_CONFIRMATION_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase38_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "38"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
