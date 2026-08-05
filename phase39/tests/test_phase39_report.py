import json
from pathlib import Path

from phase39.reporting.phase39_report import write_phase39_report


def test_phase39_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase39.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase39_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_authorization_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_AUTHORIZATION_PACKAGE_READY"
        },
        "authorization_controls": {"status": "AUTHORIZATION_CONTROLS_READY"},
        "authorization_stop_conditions": {"status": "AUTHORIZATION_STOP_CONDITIONS_READY"},
        "authorization_evidence_requirements": {
            "status": "AUTHORIZATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_authorization": {"status": "MANUAL_GATE_AUTHORIZATION_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase39_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "39"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
