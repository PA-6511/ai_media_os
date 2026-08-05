import json
from pathlib import Path

from phase26.reporting.phase26_report import write_phase26_report


def test_phase26_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase26.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase26_findings",
        "policy_result": {"policy_status": "FAIL"},
        "rehearsal_procedure": {"status": "REHEARSAL_PROCEDURE_READY"},
        "observation_points": {"status": "OBSERVATION_POINTS_READY"},
        "abort_conditions": {"status": "ABORT_CONDITIONS_READY"},
        "evidence_review": {"status": "EVIDENCE_REVIEW_READY"},
    }

    result = write_phase26_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "26"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
