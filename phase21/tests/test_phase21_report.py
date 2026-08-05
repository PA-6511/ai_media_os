import json
from pathlib import Path

from phase21.reporting.phase21_report import write_phase21_report


def test_phase21_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase21.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase21_findings",
        "validation_result": {"status": "FAIL"},
        "policy_result": {"policy_status": "FAIL"},
        "manual_approval_requirements": {"approval_required": True},
    }

    result = write_phase21_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "21"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
