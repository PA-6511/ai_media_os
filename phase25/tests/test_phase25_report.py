import json
from pathlib import Path

from phase25.reporting.phase25_report import write_phase25_report


def test_phase25_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase25.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase25_findings",
        "policy_result": {"policy_status": "FAIL"},
        "execution_plan": {"status": "DRY_RUN_EXECUTION_PLAN_READY"},
        "evidence_format": {"status": "EVIDENCE_FORMAT_READY"},
        "execution_checklist": {"status": "EXECUTION_CHECKLIST_READY"},
    }

    result = write_phase25_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "25"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
