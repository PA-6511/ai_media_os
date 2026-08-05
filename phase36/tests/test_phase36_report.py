import json
from pathlib import Path

from phase36.reporting.phase36_report import write_phase36_report


def test_phase36_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase36.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase36_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_launch_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_LAUNCH_PACKAGE_READY"
        },
        "launch_controls": {"status": "LAUNCH_CONTROLS_READY"},
        "launch_stop_conditions": {"status": "LAUNCH_STOP_CONDITIONS_READY"},
        "launch_evidence_requirements": {
            "status": "LAUNCH_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_launch": {"status": "MANUAL_GATE_LAUNCH_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase36_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "36"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
