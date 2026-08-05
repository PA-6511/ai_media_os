import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/generate_sfb15b_dashboard_operations_baseline_lock_report.py"
POLICY = ROOT / "config/sfb_15b_dashboard_operations_baseline_lock_policy.json"
REPORT_JSON = ROOT / "logs/sfb_15b_dashboard_operations_baseline_lock_report.json"
REPORT_MD = ROOT / "logs/sfb_15b_dashboard_operations_baseline_lock_report.md"


def test_sfb15b_files_exist():
    assert SCRIPT.exists()
    assert POLICY.exists()


def test_sfb15b_generates_pass_baseline_lock():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert REPORT_JSON.exists()
    assert REPORT_MD.exists()

    payload = json.loads(REPORT_JSON.read_text(encoding="utf-8"))

    assert payload["phase"] == "SFB-15B"
    assert payload["status"] == "PASS"
    assert payload["baseline_locked"] is True
    assert payload["hold_state"] == "HOLD"

    assert payload["production_status"] == "NO_GO"
    assert payload["mode"] == "DRY_RUN"
    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["approval_token_consumed"] is False

    checks = payload["checks"]
    assert checks["required_json_reports_present"] is True
    assert checks["expected_statuses_ok"] is True
    assert checks["required_test_files_present"] is True
    assert checks["phase_mapping_lock_ok"] is True
    assert checks["undefined_mapping_guard_configured"] is True
    assert checks["no_go_invariants_ok"] is True
