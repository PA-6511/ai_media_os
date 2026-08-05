import json
from pathlib import Path

from phase48.reporting.phase48_report import write_phase48_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase48_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "staging_package": {"status": "STAGING_PACKAGE_READY"},
        "staging_controls": {"status": "STAGING_CONTROLS_READY"},
        "staging_stop_conditions": {"status": "STAGING_STOP_CONDITIONS_READY"},
        "staging_evidence_requirements": {"status": "STAGING_EVIDENCE_REQUIREMENTS_READY"},
        "manual_gate_staging": {"status": "MANUAL_GATE_STAGING_READY"},
        "selected_decision": "REJECT",
    }


def test_phase48_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase48.json"
    result = write_phase48_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase48_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase48.json"
    write_phase48_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "48"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
