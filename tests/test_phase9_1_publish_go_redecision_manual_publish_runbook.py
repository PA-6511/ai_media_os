import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN_SCRIPT = ROOT / "scripts" / "generate_phase9_1_publish_go_redecision_manual_publish_runbook.py"
VAL_SCRIPT = ROOT / "scripts" / "validate_phase9_1_publish_go_redecision_manual_publish_runbook.py"
RUNBOOK_JSON = ROOT / "exchange" / "logs" / "phase9_1_publish_go_redecision_manual_publish_runbook.json"
RUNBOOK_MD = ROOT / "exchange" / "logs" / "phase9_1_publish_go_redecision_manual_publish_runbook.md"
RESULT_JSON = (
    ROOT / "exchange" / "logs" / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"
)
VALIDATION_JSON = (
    ROOT / "exchange" / "logs" / "phase9_1_publish_go_redecision_manual_publish_runbook_validation_result.json"
)


def _run_generate() -> dict:
    result = subprocess.run(
        [sys.executable, str(GEN_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Generate failed: {result.stdout}\n{result.stderr}"
    return json.loads(RESULT_JSON.read_text(encoding="utf-8"))


def _run_validate() -> dict:
    result = subprocess.run(
        [sys.executable, str(VAL_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Validate failed: {result.stdout}\n{result.stderr}"
    return json.loads(VALIDATION_JSON.read_text(encoding="utf-8"))


def test_scripts_exist():
    assert GEN_SCRIPT.exists(), "Phase 9-1 generate script not found"
    assert VAL_SCRIPT.exists(), "Phase 9-1 validate script not found"


def test_generate_phase9_1_runbook_pass():
    d = _run_generate()
    assert d["status"] == "PASS"
    assert d["decision"] == "KEEP_NO_GO"
    assert d["target_draft_id"] == 110
    assert d["target_draft_status"] == "draft"


def test_runbook_files_created():
    _run_generate()
    assert RUNBOOK_JSON.exists()
    assert RUNBOOK_MD.exists()
    runbook = json.loads(RUNBOOK_JSON.read_text(encoding="utf-8"))
    assert runbook.get("status") == "PASS"
    assert runbook.get("manual_publish_executable_now") is False


def test_validate_phase9_1_runbook_pass():
    _run_generate()
    d = _run_validate()
    assert d["status"] == "PASS"
    assert d["all_checks_passed"] is True


def test_no_go_no_write_remains_false():
    _run_generate()
    runbook = json.loads(RUNBOOK_JSON.read_text(encoding="utf-8"))
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
        assert runbook.get(key) is False, f"{key} must be False"
    assert runbook.get("wordpress_publish_execution") == "NO_GO"
    assert runbook.get("wordpress_write_executed") is False


def test_validation_report_contains_key_checks():
    _run_generate()
    d = _run_validate()
    check_names = {c["check"] for c in d.get("checks", [])}
    assert "target_draft_id=110" in check_names
    assert "target_draft_status=draft" in check_names
    assert "fixed_manual_procedure_count>=10" in check_names
    assert "forbidden_in_phase9_1_count>=10" in check_names
