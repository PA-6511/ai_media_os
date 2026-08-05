import json
from pathlib import Path

from phase44.reporting.phase44_report import write_phase44_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase44_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "closure_package": {"status": "CLOSURE_PACKAGE_READY"},
        "closure_controls": {"status": "CLOSURE_CONTROLS_READY"},
        "closure_stop_conditions": {"status": "CLOSURE_STOP_CONDITIONS_READY"},
        "closure_evidence_requirements": {"status": "CLOSURE_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_closure": {"status": "MANUAL_GATE_CLOSURE_READY"},
        "selected_decision": "REJECT",
    }


def test_phase44_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase44.json"
    result = write_phase44_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase44_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase44.json"
    write_phase44_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "44"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
