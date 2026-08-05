import json
from pathlib import Path

from phase22.reporting.phase22_report import write_phase22_report


def test_phase22_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase22.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase22_findings",
        "policy_result": {"policy_status": "FAIL"},
        "approval_format": {"status": "APPROVAL_FORMAT_READY"},
        "checklist": {"status": "CHECKLIST_READY"},
        "stop_conditions": {"status": "STOP_CONDITIONS_READY"},
    }

    result = write_phase22_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "22"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
