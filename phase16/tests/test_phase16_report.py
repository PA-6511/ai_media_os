import json
from pathlib import Path

from phase16.reporting.phase16_report import write_phase16_report


def test_phase16_report_json_has_required_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "reports" / "phase16_report.json"
    comparison_result = {
        "selected_candidate_id": "safe_small",
        "pipeline_status": "PASS_DRY_RUN_ONLY",
        "candidates_report": [],
    }

    result = write_phase16_report(comparison_result, str(output_path))

    assert result["status"] == "OK"
    assert output_path.exists()

    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["phase"] == "16"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
    assert data["selected_candidate_id"] == "safe_small"
