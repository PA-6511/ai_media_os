import json
from pathlib import Path

from phase18.reporting.phase18_report import write_phase18_report


def test_phase18_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase18_report.json"
    payload = {
        "approval_decision": "APPROVE",
        "execution_status": "PASS",
        "verify_status": "PASS",
        "can_promote_to_next": True,
    }

    result = write_phase18_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "18"
    assert data["mode"] == "DRY_RUN"
    assert data["apply_scope"] == "sandbox_only"
    assert data["human_approval_required"] is True
