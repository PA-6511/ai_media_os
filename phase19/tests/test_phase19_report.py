import json
from pathlib import Path

from phase19.reporting.phase19_report import write_phase19_report


def test_phase19_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase19.json"
    payload = {
        "promotion_status": "NOT_READY",
        "can_promote": False,
        "next_step": "fix_phase18_or_review_findings",
        "quality_result": {"quality_status": "WARN"},
        "safety_result": {"safety_status": "PASS"},
        "rollback_result": {"rollback_status": "PASS"},
    }

    result = write_phase19_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "19"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
