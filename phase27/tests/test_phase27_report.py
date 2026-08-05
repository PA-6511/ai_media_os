import json
from pathlib import Path

from phase27.reporting.phase27_report import write_phase27_report


def test_phase27_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase27.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase27_findings_or_no_go",
        "policy_result": {"policy_status": "FAIL"},
        "go_nogo_input": {"status": "GO_NOGO_INPUT_READY"},
        "go_nogo_criteria": {"status": "GO_NOGO_CRITERIA_READY"},
        "selected_decision": "NO_GO",
    }

    result = write_phase27_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "27"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
