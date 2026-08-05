import json
from pathlib import Path

from phase20.reporting.phase20_report import write_phase20_report


def test_phase20_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase20.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_apply": False,
        "next_step": "fix_phase20_findings",
        "validation_result": {"status": "PASS"},
        "policy_result": {"policy_status": "FAIL"},
    }

    result = write_phase20_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "20"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
