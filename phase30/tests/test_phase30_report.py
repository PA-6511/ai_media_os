import json
from pathlib import Path

from phase30.reporting.phase30_report import write_phase30_report


def test_phase30_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase30.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase30_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "limited_dry_run_design": {"status": "LIMITED_DRY_RUN_DESIGN_READY"},
        "sandbox_execution_constraints": {"status": "SANDBOX_EXECUTION_CONSTRAINTS_READY"},
        "manual_approval_gate": {"status": "MANUAL_APPROVAL_GATE_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase30_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "30"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
