import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_sfb_dashboard_operations_readiness.py"
POLICY_PATH = ROOT / "config/sfb_15_dashboard_operations_runbook_lock_policy.json"
READINESS_JSON = ROOT / "logs/sfb_15_dashboard_operations_readiness.json"


def test_sfb15_policy_and_script_exist():
    assert POLICY_PATH.exists()
    assert SCRIPT_PATH.exists()


def test_sfb15_readiness_is_ready_and_safe():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert READINESS_JSON.exists()

    payload = json.loads(READINESS_JSON.read_text(encoding="utf-8"))

    assert payload["status"] == "SFB15_DASHBOARD_OPERATIONS_RUNBOOK_LOCK_READY"
    assert payload["production_status"] == "NO_GO"
    assert payload["mode"] == "DRY_RUN"
    assert payload["external_api_called"] is False
    assert payload["external_network_called"] is False
    assert payload["wordpress_write_executed"] is False
    assert payload["approval_token_consumed"] is False

    assert payload["missing_runbook_section_count"] == 0
    assert payload["missing_checklist_token_count"] == 0
