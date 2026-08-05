import json
from pathlib import Path

from phase37.reporting.phase37_report import write_phase37_report


def test_phase37_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase37.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase37_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_trigger_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_TRIGGER_PACKAGE_READY"
        },
        "trigger_controls": {"status": "TRIGGER_CONTROLS_READY"},
        "trigger_stop_conditions": {"status": "TRIGGER_STOP_CONDITIONS_READY"},
        "trigger_evidence_requirements": {
            "status": "TRIGGER_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_trigger": {"status": "MANUAL_GATE_TRIGGER_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase37_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "37"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
