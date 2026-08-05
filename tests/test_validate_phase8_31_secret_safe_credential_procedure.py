"""Tests for validate_phase8_31_secret_safe_credential_procedure."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_31_secret_safe_credential_procedure import (  # noqa: E402
    validate_secret_safe_credential_procedure,
)


def good_content() -> str:
    return (ROOT / "docs/runbooks/phase8_31_secret_safe_credential_provisioning_operator_procedure.md").read_text(
        encoding="utf-8"
    )


def run_case(tmp_path: Path, content: str) -> dict:
    runbook = tmp_path / "runbook.md"
    runbook.write_text(content, encoding="utf-8")
    return validate_secret_safe_credential_procedure(
        runbook_path=runbook,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_normal_pass(tmp_path):
    result = run_case(tmp_path, good_content())
    assert result["status"] == "PASS_PROCEDURE_ONLY"


def test_missing_section_fail(tmp_path):
    content = good_content().replace("## 14. Next Step\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_missing_fixed_line_fail(tmp_path):
    content = good_content().replace("- commands_executed_in_this_phase=false\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_password_assignment_abort(tmp_path):
    content = good_content() + "\nWORDPRESS_APP_PASSWORD=abc\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_export_password_assignment_abort(tmp_path):
    content = good_content() + "\nexport WORDPRESS_APP_PASSWORD=abc\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_example_password_abort(tmp_path):
    content = good_content() + "\nexample_password\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_authorization_basic_abort(tmp_path):
    content = good_content() + "\nAuthorization: Basic abc\n"
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


def test_wp_json_abort(tmp_path):
    content = good_content() + "\n/wp-json/wp/v2/posts\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_phase8_6_to_8_10_command_abort(tmp_path):
    content = good_content() + "\npython3 scripts/validate_phase8_6_wordpress_credentials_readiness.py\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_env_auto_edit_abort(tmp_path):
    content = good_content() + "\ncreate .env automatically\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    content = good_content().replace("commands_executed_in_this_phase=false", "commands_executed_in_this_phase=true")
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_result_written(tmp_path):
    result = run_case(tmp_path, good_content())
    assert json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))["status"] == result["status"]
