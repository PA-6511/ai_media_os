import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/generate_sfb14_dashboard_aggregation.py"
JSON_REPORT = ROOT / "logs/sfb_14_dashboard_aggregation.json"
MD_REPORT = ROOT / "logs/sfb_14_dashboard_aggregation.md"


def test_sfb14_script_generates_dashboard_reports():
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

    assert payload["phase"] == "SFB-14"
    assert payload["production_status"] == "NO_GO"
    assert payload["mode"] == "DRY_RUN"
    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["approval_token_consumed"] is False
    assert payload["undefined_phase_mapping_count"] == 0

    artifact_ids = {item["id"] for item in payload["artifacts"]}
    expected = {
        "sfb_10b_baseline",
        "sfb_11_import",
        "sfb_11b_dry_run_evidence",
        "sfb_11c_import_baseline_lock",
        "sfb_12_operating_readiness",
        "sfb_13_diff_report",
    }
    assert expected.issubset(artifact_ids)

    artifact_map = {item["id"]: item for item in payload["artifacts"]}
    sfb_10b = artifact_map["sfb_10b_baseline"]
    assert sfb_10b["phase"] == "SFB-10B"
    assert "phase_raw" in sfb_10b
    assert sfb_10b["mapping_defined"] is True
