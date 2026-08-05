"""Tests for validate_phase8_17_env_credential_presence_smoke_check."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_17_env_credential_presence_smoke_check import (  # noqa: E402
    validate_env_credential_presence_smoke_check,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-17",
        "name": "env_credential_presence_smoke_check_policy",
        "policy_status": "ENV_EXISTENCE_CHECK_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "env_check_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "required_evidence": [
            "exchange/logs/phase8_16_credential_operator_confirmation_result.json"
        ],
        "allowed_phase8_16_statuses": [
            "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT",
            "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT",
        ],
        "secret_output_policy": {
            "print_values": False,
            "write_values_to_logs": False,
            "print_lengths": False,
            "print_prefix_suffix": False,
            "hash_values": False,
            "mask_values": False,
            "allowed_output": "exists_boolean_only",
        },
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
        "allowed_next_step": "Phase 8-18 post-credential rerun readiness transition report",
    }


def _write_evidence(tmp_path: Path, phase816_status: str = "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT") -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_16_credential_operator_confirmation_result.json").write_text(
        json.dumps({"status": phase816_status}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    env_vars: dict[str, str] | None = None,
    phase816_status: str = "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT",
    missing_evidence: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        _write_evidence(tmp_path, phase816_status)

    saved: dict[str, str | None] = {}
    target = env_vars or {}
    names = ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]
    for name in names:
        saved[name] = os.environ.get(name)
        if name in target:
            os.environ[name] = target[name]
        else:
            os.environ.pop(name, None)
    try:
        result = validate_env_credential_presence_smoke_check(
            policy_path=pol_path,
            output_json_path=tmp_path / "out.json",
            output_md_path=tmp_path / "out.md",
        )
    finally:
        for name in names:
            old = saved[name]
            if old is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old
    return result


def test_all_env_present_status_present(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "u",
            "WORDPRESS_APP_PASSWORD": "p",
        },
    )
    assert result["status"] == "ENV_CREDENTIALS_PRESENT_NO_SECRET_OUTPUT"


def test_one_env_missing_status_missing(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "u",
        },
    )
    assert result["status"] == "ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT"


def test_all_env_missing_status_missing(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "ENV_CREDENTIALS_MISSING_NO_SECRET_OUTPUT"


def test_values_not_in_result_json(tmp_path):
    secret = "topsecret"
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "alice",
            "WORDPRESS_APP_PASSWORD": secret,
        },
    )
    dumped = json.dumps(result)
    assert secret not in dumped
    assert "alice" not in dumped


def test_lengths_not_in_result_json(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "abc",
            "WORDPRESS_APP_PASSWORD": "12345",
        },
    )
    dumped = json.dumps(result)
    assert "length" not in dumped
    assert "len" not in dumped


def test_print_values_true_abort(tmp_path):
    p = base_policy()
    p["secret_output_policy"]["print_values"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_mask_values_true_abort(tmp_path):
    p = base_policy()
    p["secret_output_policy"]["mask_values"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_api_call_allowed_true_abort(tmp_path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_abort(tmp_path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_phase816_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_phase816_wrong_status_abort(tmp_path):
    result = run_case(tmp_path, phase816_status="FAIL")
    assert result["status"] == "ABORT"
