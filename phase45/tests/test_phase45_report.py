import json
from pathlib import Path

from phase45.reporting.phase45_report import write_phase45_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase45_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "handoff_package": {"status": "HANDOFF_PACKAGE_READY"},
        "handoff_controls": {"status": "HANDOFF_CONTROLS_READY"},
        "handoff_stop_conditions": {"status": "HANDOFF_STOP_CONDITIONS_READY"},
        "handoff_evidence_requirements": {"status": "HANDOFF_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_handoff": {"status": "MANUAL_GATE_HANDOFF_READY"},
        "selected_decision": "REJECT",
    }


def test_phase45_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase45.json"
    result = write_phase45_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase45_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase45.json"
    write_phase45_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "45"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
