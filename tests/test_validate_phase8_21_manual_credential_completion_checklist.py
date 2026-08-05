"""Tests for validate_phase8_21_manual_credential_completion_checklist."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_21_manual_credential_completion_checklist import (  # noqa: E402
    validate_manual_credential_completion_checklist,
)


def good_content() -> str:
    return (ROOT / "docs/runbooks/phase8_21_manual_credential_provisioning_completion_checklist.md").read_text(
        encoding="utf-8"
    )


def run_case(tmp_path: Path, content: str) -> dict:
    checklist = tmp_path / "checklist.md"
    checklist.write_text(content, encoding="utf-8")
    return validate_manual_credential_completion_checklist(
        checklist_path=checklist,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_happy_path_pass(tmp_path):
    result = run_case(tmp_path, good_content())
    assert result["status"] == "PASS_CHECKLIST_ONLY"


def test_missing_required_section_fail(tmp_path):
    content = good_content().replace("## 14. Final Judgment\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_missing_fixed_line_fail(tmp_path):
    content = good_content().replace("- Do not print credential lengths.\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_wordpress_app_password_assignment_abort(tmp_path):
    content = good_content() + "\nWORDPRESS_APP_PASSWORD=abc\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_export_wordpress_app_password_abort(tmp_path):
    content = good_content() + "\nexport WORDPRESS_APP_PASSWORD=abc\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_example_password_abort(tmp_path):
    content = good_content() + "\nexample_password\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_authorization_basic_abort(tmp_path):
    content = good_content() + "\nAuthorization: Basic xxxx\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_curl_post_abort(tmp_path):
    content = good_content() + "\ncurl -X POST https://example.com\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_requests_post_abort(tmp_path):
    content = good_content() + "\nrequests.post(\"https://example.com\")\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_wp_json_posts_abort(tmp_path):
    content = good_content() + "\n/wp-json/wp/v2/posts\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_env_auto_edit_abort(tmp_path):
    content = good_content() + "\ncreate .env automatically\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    content = good_content() + "\ncommands_executed_in_this_phase=true\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_result_fields_fixed_false(tmp_path):
    result = run_case(tmp_path, good_content())
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["commands_executed_in_this_phase"] is False
    assert result["secret_values_written"] is False
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["status"] == "PASS_CHECKLIST_ONLY"
