"""
tests/test_generate_phase7_5g_post_draft_creation_verification_report.py
Phase 7-5G: 実下書き作成後 手動確認・証跡保存レポート テスト
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "generate_phase7_5g_post_draft_creation_verification_report.py"
LOG_DIR = ROOT / "exchange" / "logs"
OUT_JSON = LOG_DIR / "phase7_5g_post_draft_creation_verification_report.json"
OUT_MD = LOG_DIR / "phase7_5g_post_draft_creation_verification_report.md"
SRC_7_5C = LOG_DIR / "phase7_5c_single_draft_create_live_result.json"


def _run() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists(), "Phase 7-5G スクリプトが存在しない"


def test_report_generates_successfully():
    d = _run()
    assert d["status"] == "PASS"


def test_wordpress_draft_id_recorded():
    d = _run()
    assert d.get("wordpress_draft_id") is not None
    assert isinstance(d["wordpress_draft_id"], int)


def test_created_post_status_is_draft():
    d = _run()
    assert d.get("created_post_status") == "draft"


def test_safety_flags_all_false():
    d = _run()
    for key in ["publish_allowed", "update_allowed", "delete_allowed",
                "export_allowed", "auto_post", "auto_update", "auto_delete",
                "auto_export", "github_actions_triggered",
                "slack_notification_executed", "vps_self_builder_executed",
                "env_or_secrets_modified"]:
        assert d.get(key) is False, f"{key} が False でない"


def test_md_report_generated():
    _run()
    assert OUT_MD.exists()
    content = OUT_MD.read_text(encoding="utf-8")
    assert "Phase 7-5G" in content
    assert "NO-GO" in content
