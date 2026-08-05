"""Tests for validate_phase8_13_post_credential_readiness_recheck."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_13_post_credential_readiness_recheck import (  # noqa: E402
    validate_post_credential_readiness_recheck,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-13",
        "name": "post_credential_readiness_recheck_policy",
        "policy_status": "CREDENTIAL_RECHECK_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "recheck_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "required_evidence": [
            "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json",
            "exchange/logs/phase8_12_no_secret_leak_audit_result.json",
        ],
        "required_statuses": {
            "phase8_11": "PASS_RUNBOOK_ONLY",
            "phase8_12": "NO_SECRET_LEAK_AUDIT_PASS",
        },
        "secret_output_policy": {
            "print_values": False,
            "write_values_to_logs": False,
            "print_lengths": False,
            "print_prefix_suffix": False,
            "hash_values": False,
            "allowed_output": "exists_boolean_only",
        },
        "allowed_next_step": "Phase 8-14 explicit rerun authorization renewal after credentials ready",
    }


def _write_evidences(tmp_path: Path, phase811_status: str = "PASS_RUNBOOK_ONLY", phase812_status: str = "NO_SECRET_LEAK_AUDIT_PASS") -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_11_credentials_manual_runbook_validation_result.json").write_text(
        json.dumps({"status": phase811_status}), encoding="utf-8"
    )
    (ev_dir / "phase8_12_no_secret_leak_audit_result.json").write_text(
        json.dumps({"status": phase812_status}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    phase811_status: str = "PASS_RUNBOOK_ONLY",
    phase812_status: str = "NO_SECRET_LEAK_AUDIT_PASS",
    missing_evidence: bool = False,
    env_vars: dict[str, str] | None = None,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"

    if not missing_evidence:
        _write_evidences(tmp_path, phase811_status, phase812_status)

    p["required_evidence"] = [
        "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json",
        "exchange/logs/phase8_12_no_secret_leak_audit_result.json",
    ]
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    # Set / unset env vars
    saved: dict[str, str | None] = {}
    target_vars = env_vars or {}
    all_vars = ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]
    for var in all_vars:
        saved[var] = os.environ.get(var)
        if var in target_vars:
            os.environ[var] = target_vars[var]
        else:
            os.environ.pop(var, None)
    try:
        result = validate_post_credential_readiness_recheck(
            policy_path=pol_path,
            output_json_path=tmp_path / "out.json",
            output_md_path=tmp_path / "out.md",
        )
    finally:
        for var in all_vars:
            old = saved[var]
            if old is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = old
    return result


def test_all_present_ready(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "user",
            "WORDPRESS_APP_PASSWORD": "pass",
        },
    )
    assert result["status"] == "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT"


def test_missing_credentials_not_ready(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"


def test_partial_missing_not_ready(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "user",
        },
    )
    assert result["status"] == "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"


def test_credentials_output_exists_only(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "user",
            "WORDPRESS_APP_PASSWORD": "pass",
        },
    )
    credentials = result.get("credentials", {})
    for var, info in credentials.items():
        assert set(info.keys()) == {"exists"}, f"unexpected keys in credentials[{var}]: {info}"
        assert isinstance(info["exists"], bool)


def test_secret_values_written_false(tmp_path):
    result = run_case(tmp_path)
    assert result["secret_values_written"] is False


def test_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_phase811_wrong_status_abort(tmp_path):
    result = run_case(tmp_path, phase811_status="FAIL")
    assert result["status"] == "ABORT"


def test_phase812_wrong_status_abort(tmp_path):
    result = run_case(tmp_path, phase812_status="FAIL")
    assert result["status"] == "ABORT"


def test_print_values_true_abort(tmp_path):
    p = base_policy()
    p["secret_output_policy"]["print_values"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_write_values_to_logs_true_abort(tmp_path):
    p = base_policy()
    p["secret_output_policy"]["write_values_to_logs"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_hash_values_true_abort(tmp_path):
    p = base_policy()
    p["secret_output_policy"]["hash_values"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_recheck_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["recheck_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["recheck_is_execution_permission"] is False
