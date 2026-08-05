import json
from pathlib import Path

from phase46.reporting.phase46_report import write_phase46_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase46_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "transition_package": {"status": "TRANSITION_PACKAGE_READY"},
        "transition_controls": {"status": "TRANSITION_CONTROLS_READY"},
        "transition_stop_conditions": {"status": "TRANSITION_STOP_CONDITIONS_READY"},
        "transition_evidence_requirements": {"status": "TRANSITION_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_transition": {"status": "MANUAL_GATE_TRANSITION_READY"},
        "selected_decision": "REJECT",
    }


def test_phase46_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase46.json"
    result = write_phase46_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase46_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase46.json"
    write_phase46_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "46"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
