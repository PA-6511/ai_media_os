import json
from pathlib import Path

from phase34.reporting.phase34_report import write_phase34_report


def test_phase34_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase34.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase34_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_execution_final_pre_execution_review": {
            "status": "FINAL_PRE_EXECUTION_REVIEW_READY"
        },
        "final_review_controls": {"status": "FINAL_REVIEW_CONTROLS_READY"},
        "final_review_stop_conditions": {
            "status": "FINAL_REVIEW_STOP_CONDITIONS_READY"
        },
        "final_review_evidence_requirements": {
            "status": "FINAL_REVIEW_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_pre_execution_review": {
            "status": "MANUAL_GATE_FINAL_PRE_EXECUTION_REVIEW_READY"
        },
        "selected_decision": "REJECT",
    }

    result = write_phase34_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "34"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
