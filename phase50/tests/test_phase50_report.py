import json
from pathlib import Path

from phase50.reporting.phase50_report import write_phase50_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase50_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "cutover_planning_package": {"status": "CUTOVER_PLANNING_PACKAGE_READY"},
        "cutover_planning_controls": {"status": "CUTOVER_PLANNING_CONTROLS_READY"},
        "cutover_planning_stop_conditions": {"status": "CUTOVER_PLANNING_STOP_CONDITIONS_READY"},
        "cutover_planning_evidence_requirements": {
            "status": "CUTOVER_PLANNING_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_cutover_planning": {"status": "MANUAL_GATE_CUTOVER_PLANNING_READY"},
        "selected_decision": "REJECT",
    }


def test_phase50_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase50.json"
    result = write_phase50_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase50_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase50.json"
    write_phase50_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "50"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
