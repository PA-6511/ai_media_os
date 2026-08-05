import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_phase8_10_keep_no_go_redecision_completion_report.py"
OUT_JSON = ROOT / "exchange" / "logs" / "phase8_10_keep_no_go_redecision_completion_report.json"
OUT_MD = ROOT / "exchange" / "logs" / "phase8_10_keep_no_go_redecision_completion_report.md"


def _run() -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))


def test_script_exists():
    assert SCRIPT.exists(), "Phase 8-10 script not found"


def test_report_generates_successfully():
    d = _run()
    assert d["status"] == "PASS"


def test_keep_no_go_core_values():
    d = _run()
    assert d.get("phase8_9_decision") == "KEEP_NO_GO"
    assert d.get("publish_candidate_unlocked_for_operator") is False
    assert d.get("wordpress_publish_execution") == "NO_GO"
    assert d.get("wordpress_write_executed") is False
    assert d.get("target_draft_id") == 110


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
    ]:
        assert d.get(key) is False, f"{key} must be False"


def test_next_step_matches_expectation():
    d = _run()
    assert d.get("next_step") == "maintain_no_go_or_manual_publish_redecision"


def test_md_report_generated():
    _run()
    assert OUT_MD.exists()
    content = OUT_MD.read_text(encoding="utf-8")
    assert "Phase 8-10" in content
    assert "KEEP_NO_GO" in content
