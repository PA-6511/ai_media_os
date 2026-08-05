import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config/sfb_13_csv_import_diff_report_enhancement_policy.json"
SCRIPT_PATH = ROOT / "scripts/generate_sfb13_csv_import_diff_report.py"
JSON_REPORT = ROOT / "logs/sfb_13_csv_import_diff_report.json"
MD_REPORT = ROOT / "logs/sfb_13_csv_import_diff_report.md"


def test_sfb13_policy_and_script_exist():
    assert POLICY_PATH.exists()
    assert SCRIPT_PATH.exists()


def test_sfb13_script_generates_reports_and_keeps_no_go():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert JSON_REPORT.exists()
    assert MD_REPORT.exists()

    payload = json.loads(JSON_REPORT.read_text(encoding="utf-8"))

    assert payload["production_status"] == "NO_GO"
    assert payload["mode"] == "DRY_RUN"
    assert payload["external_api_called"] is False
    assert payload["wordpress_write_executed"] is False

    diff = payload["diff"]
    assert "added_candidates" in diff
    assert "removed_candidates" in diff
    assert "updated_candidates" in diff

    assert "count" in diff["added_candidates"]
    assert "count" in diff["removed_candidates"]
    assert "count" in diff["updated_candidates"]
