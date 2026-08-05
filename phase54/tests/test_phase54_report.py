import json
from pathlib import Path

from phase54.reporting.phase54_report import write_phase54_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase54_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "final_authorization_package": {"status": "FINAL_AUTHORIZATION_PACKAGE_READY"},
        "final_authorization_controls": {"status": "FINAL_AUTHORIZATION_CONTROLS_READY"},
        "final_authorization_stop_conditions": {"status": "FINAL_AUTHORIZATION_STOP_CONDITIONS_READY"},
        "final_authorization_evidence_requirements": {
            "status": "FINAL_AUTHORIZATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_authorization": {"status": "MANUAL_GATE_FINAL_AUTHORIZATION_READY"},
        "selected_decision": "REJECT",
    }


def test_phase54_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase54.json"
    result = write_phase54_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase54_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase54.json"
    write_phase54_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "54"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
