import json
from pathlib import Path

from phase49.reporting.phase49_report import write_phase49_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase49_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "release_planning_package": {"status": "RELEASE_PLANNING_PACKAGE_READY"},
        "release_planning_controls": {"status": "RELEASE_PLANNING_CONTROLS_READY"},
        "release_planning_stop_conditions": {"status": "RELEASE_PLANNING_STOP_CONDITIONS_READY"},
        "release_planning_evidence_requirements": {
            "status": "RELEASE_PLANNING_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_release_planning": {"status": "MANUAL_GATE_RELEASE_PLANNING_READY"},
        "selected_decision": "REJECT",
    }


def test_phase49_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase49.json"
    result = write_phase49_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase49_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase49.json"
    write_phase49_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "49"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
