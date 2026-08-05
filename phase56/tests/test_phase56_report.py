import json
from pathlib import Path

from phase56.reporting.phase56_report import write_phase56_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase56_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "final_preflight_package": {"status": "FINAL_PREFLIGHT_PACKAGE_READY"},
        "final_preflight_controls": {"status": "FINAL_PREFLIGHT_CONTROLS_READY"},
        "final_preflight_stop_conditions": {"status": "FINAL_PREFLIGHT_STOP_CONDITIONS_READY"},
        "final_preflight_evidence_requirements": {
            "status": "FINAL_PREFLIGHT_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_preflight": {"status": "MANUAL_GATE_FINAL_PREFLIGHT_READY"},
        "selected_decision": "REJECT",
    }


def test_phase56_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase56.json"
    result = write_phase56_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase56_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase56.json"
    write_phase56_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "56"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
