import json
from pathlib import Path

from phase41.reporting.phase41_report import write_phase41_report


def test_phase41_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase41.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase41_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_certification_package": {
            "status": "MANUAL_DRY_RUN_EXECUTION_CERTIFICATION_PACKAGE_READY"
        },
        "certification_controls": {"status": "CERTIFICATION_CONTROLS_READY"},
        "certification_stop_conditions": {"status": "CERTIFICATION_STOP_CONDITIONS_READY"},
        "certification_evidence_requirements": {
            "status": "CERTIFICATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_certification": {"status": "MANUAL_GATE_CERTIFICATION_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase41_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "41"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
