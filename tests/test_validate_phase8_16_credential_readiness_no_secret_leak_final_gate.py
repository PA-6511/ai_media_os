"""Tests for Phase 8-16 credential readiness / no-secret-leak final gate."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_16_credential_readiness_no_secret_leak_final_gate_report import (  # noqa: E402
    generate_phase8_16_credential_readiness_no_secret_leak_final_gate_report,
)
from validate_phase8_16_credential_readiness_no_secret_leak_final_gate import (  # noqa: E402
    validate_phase8_16_credential_readiness_no_secret_leak_final_gate,
)


def base_policy() -> dict:
    return {
        "phase": "8-16",
        "phase_name": "Credential readiness / no-secret-leak final gate",
        "phase_status": "FINAL_GATE_DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "mode": "CREDENTIAL_READINESS_FINAL_GATE",
        "human_approval_required": True,
        "required_env": [
            "WORDPRESS_BASE_URL",
            "WORDPRESS_USERNAME",
            "WORDPRESS_APP_PASSWORD",
        ],
        "required_false_flags": [
            "wordpress_api_call_allowed",
            "wordpress_api_call_attempted",
            "wordpress_write_executed",
            "wordpress_draft_created",
            "publish_allowed",
            "update_allowed",
            "delete_allowed",
            "bulk_action_allowed",
            "export_allowed",
            "auto_post",
            "auto_update",
            "auto_delete",
            "auto_export",
            "approve_draft_create_only_currently_allowed",
            "unlock_in_this_phase",
            "secret_values_output",
            "secret_values_written",
            "secret_values_logged",
            "executor_action_allowed",
        ],
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "bulk_action_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "secret_values_output": False,
        "secret_values_written": False,
        "secret_values_logged": False,
        "executor_action_allowed": False,
        "no_secret_leak_detection": {
            "forbidden_terms": [
                "password",
                "app_password",
                "application_password",
                "token",
                "secret",
                "webhook",
                "authorization",
                "cookie",
                "basic",
                "bearer",
                "api_key",
                "client_secret",
            ],
            "allowed_key_names": ["credential_key", "required_env", "missing_credential_keys"],
        },
        "allowed_next_step_if_ready": "phase8_17_or_manual_human_approval_before_single_draft_creation",
        "allowed_next_step_if_not_ready": "manual_credential_provisioning_or_env_fix_without_secret_output",
    }


def base_request() -> dict:
    return {
        "mode": "CREDENTIAL_READINESS_FINAL_GATE",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "target_item_count": 1,
        "credential_check_only": True,
        "no_secret_leak_required": True,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "secret_values_must_not_be_output": True,
        "next_step_if_pass": "phase8_17_or_manual_human_approval_before_single_draft_creation",
        "next_step_if_not_ready": "manual_credential_provisioning_or_env_fix_without_secret_output",
    }


def run_case(
    tmp_path: Path,
    monkeypatch,
    env_overrides: dict[str, str | None] | None = None,
    policy_overrides: dict | None = None,
    request_overrides: dict | None = None,
) -> tuple[dict, Path, Path, Path, Path]:
    policy = copy.deepcopy(base_policy())
    request = copy.deepcopy(base_request())

    if policy_overrides:
        policy.update(policy_overrides)
    if request_overrides:
        request.update(request_overrides)

    policy_path = tmp_path / "config" / "policy.json"
    request_path = tmp_path / "exchange" / "examples" / "request.json"
    result_path = tmp_path / "exchange" / "logs" / "result.json"
    report_json_path = tmp_path / "exchange" / "logs" / "report.json"
    report_md_path = tmp_path / "exchange" / "logs" / "report.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    request_path.write_text(json.dumps(request), encoding="utf-8")

    env_map = env_overrides or {}
    target_env = ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]
    saved = {key: os.environ.get(key) for key in target_env}

    for key in target_env:
        if key in env_map and env_map[key] is not None:
            monkeypatch.setenv(key, str(env_map[key]))
        else:
            monkeypatch.delenv(key, raising=False)

    try:
        result = validate_phase8_16_credential_readiness_no_secret_leak_final_gate(
            policy_path=policy_path,
            request_path=request_path,
            output_json_path=result_path,
        )
        report = generate_phase8_16_credential_readiness_no_secret_leak_final_gate_report(
            result_json_path=result_path,
            output_json_path=report_json_path,
            output_md_path=report_md_path,
        )
    finally:
        for key, val in saved.items():
            if val is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, val)

    return result, result_path, report, report_json_path, report_md_path


def test_required_env_all_present_non_empty_ready(tmp_path, monkeypatch):
    result, _, _, _, _ = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": "safe-value",
        },
    )
    assert result["final_status"] == "CREDENTIALS_READY_NO_SECRET_LEAK_PASS"
    assert result["secret_values_output"] is False
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_executed"] is False


def test_env_missing_outputs_only_missing_key_names(tmp_path, monkeypatch):
    result, _, _, _, _ = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": None,
        },
    )
    assert result["final_status"] == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
    assert result["missing_credential_keys"] == ["WORDPRESS_APP_PASSWORD"]
    dumped = json.dumps(result)
    assert "publisher" not in dumped


def test_env_empty_marks_empty_and_not_ready(tmp_path, monkeypatch):
    result, _, _, _, _ = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": "   ",
        },
    )
    status_map = {item["credential_key"]: item["status"] for item in result["credentials"]}
    assert status_map["WORDPRESS_APP_PASSWORD"] == "EMPTY"
    assert result["final_status"] != "CREDENTIALS_READY_NO_SECRET_LEAK_PASS"


def test_policy_dangerous_flag_true_aborts_policy_violation(tmp_path, monkeypatch):
    result, _, _, _, _ = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": "safe-value",
        },
        policy_overrides={"wordpress_api_call_allowed": True},
    )
    assert result["final_status"] == "ABORT_POLICY_VIOLATION"


def test_secret_dummy_value_not_in_result_report_or_stdout_equivalent(tmp_path, monkeypatch):
    dummy_secret = "DUMMY_SECRET_SHOULD_NEVER_APPEAR_12345"
    result, result_path, report, report_json_path, report_md_path = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": dummy_secret,
        },
    )

    texts = [
        json.dumps(result, ensure_ascii=False),
        result_path.read_text(encoding="utf-8"),
        json.dumps(report, ensure_ascii=False),
        report_json_path.read_text(encoding="utf-8"),
        report_md_path.read_text(encoding="utf-8"),
    ]
    for text in texts:
        assert dummy_secret not in text


def test_authorization_bearer_basic_password_token_webhook_values_not_output(tmp_path, monkeypatch):
    dangerous = "Authorization: Basic NEVER_OUTPUT_THIS token=ABC webhook=https://x.example bearer SECRET"
    result, result_path, report, report_json_path, report_md_path = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": dangerous,
        },
    )

    forbidden_fragments = [
        "NEVER_OUTPUT_THIS",
        "token=ABC",
        "Authorization: Basic",
        "webhook=https://x.example",
        "bearer SECRET",
    ]
    text_targets = [
        json.dumps(result, ensure_ascii=False),
        result_path.read_text(encoding="utf-8"),
        json.dumps(report, ensure_ascii=False),
        report_json_path.read_text(encoding="utf-8"),
        report_md_path.read_text(encoding="utf-8"),
    ]
    for fragment in forbidden_fragments:
        for text in text_targets:
            assert fragment not in text


def test_report_generator_outputs_markdown_json_without_secret_values(tmp_path, monkeypatch):
    secret = "TOP_SECRET_VALUE_DO_NOT_PRINT"
    _, _, report, report_json_path, report_md_path = run_case(
        tmp_path,
        monkeypatch,
        env_overrides={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "publisher",
            "WORDPRESS_APP_PASSWORD": secret,
        },
    )

    report_json = report_json_path.read_text(encoding="utf-8")
    report_md = report_md_path.read_text(encoding="utf-8")

    assert "final_status" in report
    assert secret not in report_json
    assert secret not in report_md
    assert "WordPress API call not executed" in report_md
    assert "draft creation not executed" in report_md
