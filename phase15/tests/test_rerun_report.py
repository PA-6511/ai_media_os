import json
from pathlib import Path

from phase15.pipeline.rerun import build_rerun_report
from phase15.reporting.report_writer import write_report


def test_report_writer_creates_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase15.json"
    payload = {"phase": "15", "ok": True}

    result = write_report(payload, str(output))

    assert result["status"] == "OK"
    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "15"


def test_rerun_report_contains_phase_15() -> None:
    verify_result = {"returncode": 0}
    triage_result = {"category": "PASS"}

    report = build_rerun_report(verify_result, triage_result)

    assert report["phase"] == "15"
    assert report["pipeline_status"] == "PASS"
