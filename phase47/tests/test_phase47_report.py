import json
from pathlib import Path

from phase47.reporting.phase47_report import write_phase47_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase47_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "integration_package": {"status": "INTEGRATION_PACKAGE_READY"},
        "integration_controls": {"status": "INTEGRATION_CONTROLS_READY"},
        "integration_stop_conditions": {"status": "INTEGRATION_STOP_CONDITIONS_READY"},
        "integration_evidence_requirements": {"status": "INTEGRATION_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_integration": {"status": "MANUAL_GATE_INTEGRATION_READY"},
        "selected_decision": "REJECT",
    }


def test_phase47_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase47.json"
    result = write_phase47_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase47_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase47.json"
    write_phase47_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "47"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
