import json
from pathlib import Path

from phase57.reporting.phase57_report import write_phase57_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase57_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "final_check_package": {"status": "FINAL_CHECK_PACKAGE_READY"},
        "final_check_controls": {"status": "FINAL_CHECK_CONTROLS_READY"},
        "final_check_stop_conditions": {"status": "FINAL_CHECK_STOP_CONDITIONS_READY"},
        "final_check_evidence_requirements": {
            "status": "FINAL_CHECK_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_check": {"status": "MANUAL_GATE_FINAL_CHECK_READY"},
        "selected_decision": "REJECT",
    }


def test_phase57_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase57.json"
    result = write_phase57_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase57_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase57.json"
    write_phase57_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "57"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
