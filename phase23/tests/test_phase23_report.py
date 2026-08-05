import json
from pathlib import Path

from phase23.reporting.phase23_report import write_phase23_report


def test_phase23_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase23.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase23_findings",
        "policy_result": {"policy_status": "FAIL"},
        "execution_design": {"status": "CONTROLLED_EXECUTION_DESIGN_READY"},
        "final_manual_gate": {"status": "FINAL_MANUAL_GATE_READY"},
        "stop_condition_verify": {"status": "PASS"},
    }

    result = write_phase23_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "23"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
