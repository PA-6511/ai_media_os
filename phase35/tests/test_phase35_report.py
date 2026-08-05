import json
from pathlib import Path

from phase35.reporting.phase35_report import write_phase35_report


def test_phase35_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase35.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase35_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_readiness_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_READINESS_PACKAGE_READY"
        },
        "readiness_controls": {"status": "READINESS_CONTROLS_READY"},
        "readiness_stop_conditions": {"status": "READINESS_STOP_CONDITIONS_READY"},
        "readiness_evidence_requirements": {
            "status": "READINESS_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_readiness": {"status": "MANUAL_GATE_READINESS_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase35_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "35"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
