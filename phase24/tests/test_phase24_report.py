import json
from pathlib import Path

from phase24.reporting.phase24_report import write_phase24_report


def test_phase24_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase24.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase24_findings_or_no_go",
        "validation_result": {"status": "PASS"},
        "policy_result": {"policy_status": "FAIL"},
        "decision_design": {"status": "GO_NOGO_DECISION_READY"},
        "selected_decision": "NO_GO",
    }

    result = write_phase24_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "24"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
