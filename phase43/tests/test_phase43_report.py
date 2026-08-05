import json
from pathlib import Path

from phase43.reporting.phase43_report import write_phase43_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase43_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "completion_package": {"status": "COMPLETION_PACKAGE_READY"},
        "completion_controls": {"status": "COMPLETION_CONTROLS_READY"},
        "completion_stop_conditions": {"status": "COMPLETION_STOP_CONDITIONS_READY"},
        "completion_evidence_requirements": {"status": "COMPLETION_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_completion": {"status": "MANUAL_GATE_COMPLETION_READY"},
        "selected_decision": "REJECT",
    }


def test_phase43_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase43.json"
    result = write_phase43_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase43_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase43.json"
    write_phase43_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "43"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
