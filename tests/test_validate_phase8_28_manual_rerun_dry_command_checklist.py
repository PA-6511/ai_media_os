"""Tests for validate_phase8_28_manual_rerun_dry_command_checklist."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_28_manual_rerun_dry_command_checklist import (  # noqa: E402
    validate_manual_rerun_dry_command_checklist,
)


def good_content() -> str:
    return (ROOT / "docs/runbooks/phase8_28_manual_rerun_dry_command_checklist.md").read_text(encoding="utf-8")


def run_case(tmp_path: Path, content: str) -> dict:
    checklist = tmp_path / "checklist.md"
    checklist.write_text(content, encoding="utf-8")
    return validate_manual_rerun_dry_command_checklist(
        checklist_path=checklist,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_normal_pass(tmp_path):
    result = run_case(tmp_path, good_content())
    assert result["status"] == "PASS_DRY_COMMAND_CHECKLIST_ONLY"


def test_missing_section_fail(tmp_path):
    content = good_content().replace("## 13. Final Judgment\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_missing_fixed_line_fail(tmp_path):
    content = good_content().replace("- commands_executed_in_this_phase=false\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_curl_post_abort(tmp_path):
    content = good_content() + "\n- curl -X POST https://example.com\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_requests_post_abort(tmp_path):
    content = good_content() + "\n- requests.post(\"https://example.com\")\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_wp_json_abort(tmp_path):
    content = good_content() + "\n- /wp-json/wp/v2/posts\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_password_assignment_abort(tmp_path):
    content = good_content() + "\nWORDPRESS_APP_PASSWORD=abc\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_python_command_not_allowed_abort(tmp_path):
    content = good_content() + "\n- python3 scripts/not_allowed.py\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    content = good_content().replace("commands_executed_in_this_phase=false", "commands_executed_in_this_phase=true")
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_result_file_written(tmp_path):
    result = run_case(tmp_path, good_content())
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["status"] == result["status"]
