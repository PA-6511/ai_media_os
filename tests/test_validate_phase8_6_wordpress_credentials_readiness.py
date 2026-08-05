"""Tests for validate_phase8_6_wordpress_credentials_readiness."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_6_wordpress_credentials_readiness import validate_credentials_readiness  # noqa: E402

PHASE8_5_REL = "exchange/logs/phase8_5_first_controlled_draft_completion_report.json"


def base_policy():
    return {
        "phase": "Phase 8-6",
        "name": "wordpress_credentials_readiness_policy",
        "policy_status": "CREDENTIAL_EXISTENCE_CHECK_ONLY",
        "production_status": "NO_GO",
        "credential_check_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_env": [
            "WORDPRESS_BASE_URL",
            "WORDPRESS_USERNAME",
            "WORDPRESS_APP_PASSWORD",
        ],
        "secret_output_policy": {
            "print_values": False,
            "write_values_to_logs": False,
            "print_lengths": False,
            "print_prefix_suffix": False,
            "hash_values": False,
        },
        "required_evidence": [PHASE8_5_REL],
        "required_phase8_5_status": "FIRST_DRAFT_NOT_EXECUTED",
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "allowed_next_step": "Phase 8-7 rerun approval preservation review",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    phase85_status: str = "FIRST_DRAFT_NOT_EXECUTED",
    missing_evidence: bool = False,
    monkeypatch=None,
    env_overrides: dict | None = None,
):
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps(p), encoding="utf-8")

    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    if not missing_evidence:
        (ev_dir / "phase8_5_first_controlled_draft_completion_report.json").write_text(
            json.dumps({"status": phase85_status}),
            encoding="utf-8",
        )

    p["required_evidence"] = [str(ev_dir / "phase8_5_first_controlled_draft_completion_report.json")]
    policy_file.write_text(json.dumps(p), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"

    if monkeypatch is not None and env_overrides is not None:
        for k, v in env_overrides.items():
            if v is None:
                monkeypatch.delenv(k, raising=False)
            else:
                monkeypatch.setenv(k, v)

    return validate_credentials_readiness(policy_file, out_json, out_md)


def test_all_credentials_present_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "abcd efgh ijkl mnop")
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIALS_READY_NO_SECRET_OUTPUT"
    creds = result["credentials"]
    assert creds["WORDPRESS_BASE_URL"]["exists"] is True
    assert creds["WORDPRESS_USERNAME"]["exists"] is True
    assert creds["WORDPRESS_APP_PASSWORD"]["exists"] is True


def test_one_credential_missing_not_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
    monkeypatch.delenv("WORDPRESS_APP_PASSWORD", raising=False)
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
    assert result["credentials"]["WORDPRESS_APP_PASSWORD"]["exists"] is False


def test_all_credentials_missing_not_ready(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("WORDPRESS_APP_PASSWORD", raising=False)
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"
    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        assert result["credentials"][key]["exists"] is False


def test_secret_values_not_written(tmp_path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "secretuser")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "supersecret password")
    result = run_case(tmp_path)
    assert result["secret_values_written"] is False
    result_str = json.dumps(result)
    assert "secretuser" not in result_str
    assert "supersecret" not in result_str


def test_credential_lengths_not_in_json(tmp_path, monkeypatch):
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "abcd efgh ijkl mnop")
    result = run_case(tmp_path)
    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        cred = result["credentials"][key]
        assert "length" not in cred
        assert "prefix" not in cred
        assert "suffix" not in cred
        assert "hash" not in cred


def test_abort_secret_output_policy_print_values_true(tmp_path, monkeypatch):
    pol = base_policy()
    pol["secret_output_policy"]["print_values"] = True
    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.com")
    monkeypatch.setenv("WORDPRESS_USERNAME", "ai_publisher")
    monkeypatch.setenv("WORDPRESS_APP_PASSWORD", "pass")
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_secret_output_policy_write_values_to_logs_true(tmp_path, monkeypatch):
    pol = base_policy()
    pol["secret_output_policy"]["write_values_to_logs"] = True
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_wordpress_api_call_allowed_true(tmp_path, monkeypatch):
    pol = base_policy()
    pol["wordpress_api_call_allowed"] = True
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_wordpress_write_executed_true(tmp_path, monkeypatch):
    pol = base_policy()
    pol["wordpress_write_executed"] = True
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_publish_allowed_true(tmp_path, monkeypatch):
    pol = base_policy()
    pol["publish_allowed"] = True
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_abort_phase85_evidence_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_abort_phase85_wrong_status(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    result = run_case(tmp_path, phase85_status="FIRST_DRAFT_COMPLETED")
    assert result["status"] == "ABORT"


def test_fixed_safety_flags_in_result(tmp_path, monkeypatch):
    monkeypatch.delenv("WORDPRESS_BASE_URL", raising=False)
    monkeypatch.delenv("WORDPRESS_USERNAME", raising=False)
    monkeypatch.delenv("WORDPRESS_APP_PASSWORD", raising=False)
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["credential_check_is_execution_permission"] is False
