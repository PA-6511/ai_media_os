import json
from pathlib import Path

from phase60.reporting.phase60_report import write_phase60_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase60_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "runbook_package": {"status": "RUNBOOK_PACKAGE_READY"},
        "runbook_controls": {"status": "RUNBOOK_CONTROLS_READY"},
        "runbook_stop_conditions": {"status": "RUNBOOK_STOP_CONDITIONS_READY"},
        "runbook_evidence_requirements": {
            "status": "RUNBOOK_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_runbook": {"status": "MANUAL_GATE_RUNBOOK_READY"},
        "selected_decision": "REJECT",
    }


def test_phase60_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase60.json"
    result = write_phase60_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase60_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase60.json"
    write_phase60_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "60"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
