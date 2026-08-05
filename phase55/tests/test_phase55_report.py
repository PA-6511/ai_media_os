import json
from pathlib import Path

from phase55.reporting.phase55_report import write_phase55_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase55_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "final_readiness_package": {"status": "FINAL_READINESS_PACKAGE_READY"},
        "final_readiness_controls": {"status": "FINAL_READINESS_CONTROLS_READY"},
        "final_readiness_stop_conditions": {"status": "FINAL_READINESS_STOP_CONDITIONS_READY"},
        "final_readiness_evidence_requirements": {
            "status": "FINAL_READINESS_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_readiness": {"status": "MANUAL_GATE_FINAL_READINESS_READY"},
        "selected_decision": "REJECT",
    }


def test_phase55_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase55.json"
    result = write_phase55_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase55_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase55.json"
    write_phase55_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "55"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
