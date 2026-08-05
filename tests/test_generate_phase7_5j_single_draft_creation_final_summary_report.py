import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase7_5j_single_draft_creation_final_summary_report.py"
OUT_JSON = ROOT / "exchange" / "logs" / "phase7_5j_single_draft_creation_final_summary_report.json"
OUT_MD = ROOT / "exchange" / "logs" / "phase7_5j_single_draft_creation_final_summary_report.md"


def _run() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists(), "Phase 7-5J script not found"


def test_report_generates_successfully():
    d = _run()
    assert d["status"] == "PASS"


def test_final_key_values_are_expected():
    d = _run()
    assert d.get("wordpress_draft_id") == 110
    assert d.get("created_post_status") == "draft"
    assert d.get("decision") == "KEEP"
    assert d.get("wordpress_write_executed") is True
    assert d.get("relocked_after_execution") is True


def test_phase_statuses_all_pass():
    d = _run()
    for _, v in d.get("phase_statuses", {}).items():
        assert v == "PASS"


def test_no_go_flags_false():
    d = _run()
    for key in [
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "github_actions_triggered",
        "slack_notification_executed",
        "vps_self_builder_executed",
        "env_or_secrets_modified",
    ]:
        assert d.get(key) is False, f"{key} must be False"


def test_md_report_generated():
    _run()
    assert OUT_MD.exists()
    content = OUT_MD.read_text(encoding="utf-8")
    assert "Phase 7-5J" in content
    assert "NO-GO" in content
