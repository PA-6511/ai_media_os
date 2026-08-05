"""Tests for validate_phase8_11_credentials_manual_runbook."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_11_credentials_manual_runbook import (  # noqa: E402
    REQUIRED_SECTIONS,
    REQUIRED_FIXED_STATEMENTS,
    validate_credentials_manual_runbook,
)

RUNBOOK_PATH = ROOT / "docs/runbooks/phase8_11_wordpress_credentials_manual_provisioning_runbook.md"


def run_case(tmp_path: Path, content: str | None = None) -> dict:
    if content is None:
        rb_path = RUNBOOK_PATH
    else:
        rb_path = tmp_path / "runbook.md"
        rb_path.write_text(content, encoding="utf-8")
    return validate_credentials_manual_runbook(
        runbook_path=rb_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def _good_runbook() -> str:
    """Return a minimal runbook that passes all checks."""
    sections = "\n".join(s + "\ncontent\n" for s in REQUIRED_SECTIONS)
    fixed = "\n".join(REQUIRED_FIXED_STATEMENTS)
    return (
        "# Phase 8-11 WordPress Credentials Manual Provisioning Runbook\n\n"
        + sections
        + "\n"
        + fixed
        + "\nDo not create or edit .env automatically.\n"
        + "DRY_RUN_PLACEHOLDER_ONLY: credentials must be provisioned manually outside this repository.\n"
    )


def test_normal_pass(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_RUNBOOK_ONLY"


def test_normal_pass_from_real_runbook(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_RUNBOOK_ONLY"
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["secret_values_written"] is False
    assert result["runbook_is_execution_permission"] is False


def test_missing_section_fail(tmp_path):
    content = _good_runbook().replace("## 5. Required Environment Variables\n", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"
    assert any("Required Environment Variables" in e for e in result["errors"])


def test_missing_fixed_statement_fail(tmp_path):
    content = _good_runbook().replace("RERUN_NOT_EXECUTED_CONFIRMED", "")
    result = run_case(tmp_path, content)
    assert result["status"] == "FAIL"


def test_abort_wordpress_app_password_equals(tmp_path):
    content = _good_runbook() + "\nWORDPRESS_APP_PASSWORD=secret123\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_export_wordpress_app_password(tmp_path):
    content = _good_runbook() + "\nexport WORDPRESS_APP_PASSWORD=abc123\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_example_password(tmp_path):
    content = _good_runbook() + "\nexample_password\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_authorization_basic(tmp_path):
    content = _good_runbook() + "\nAuthorization: Basic dXNlcjpwYXNz\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_curl_x_post(tmp_path):
    content = _good_runbook() + "\ncurl -X POST https://example.com/wp-json/wp/v2/posts\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_requests_post(tmp_path):
    content = _good_runbook() + "\nrequests.post(\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_abort_wp_json_posts(tmp_path):
    content = _good_runbook() + "\nwp-json/wp/v2/posts\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "ABORT"


def test_allowed_env_prohibition_text(tmp_path):
    """Runbook text that mentions .env in a prohibition context must not trigger ABORT."""
    content = _good_runbook() + "\nDo not create or edit .env automatically.\n"
    result = run_case(tmp_path, content)
    assert result["status"] == "PASS_RUNBOOK_ONLY"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["secret_values_written"] is False


def test_runbook_not_found_fail(tmp_path):
    result = validate_credentials_manual_runbook(
        runbook_path=tmp_path / "nonexistent.md",
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )
    assert result["status"] == "FAIL"
