"""Tests for validate_phase8_22_credential_ready_path_switch."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_22_credential_ready_path_switch import (  # noqa: E402
    validate_credential_ready_path_switch,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-22",
        "name": "credential_ready_path_switch_policy",
        "policy_status": "READY_PATH_SWITCH_VALIDATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "path_switch_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "required_evidence": ["exchange/logs/phase8_21_manual_credential_completion_checklist_result.json"],
        "required_phase8_21_status": "PASS_CHECKLIST_ONLY",
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
        "allowed_next_step": "Phase 8-23 pre-rerun immutable safety snapshot",
    }


def _write_evidence(tmp_path: Path, phase821_status: str = "PASS_CHECKLIST_ONLY") -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_21_manual_credential_completion_checklist_result.json").write_text(
        json.dumps({"status": phase821_status}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    env_vars: dict[str, str] | None = None,
    phase821_status: str = "PASS_CHECKLIST_ONLY",
    missing_evidence: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        _write_evidence(tmp_path, phase821_status)

    saved = {}
    target = env_vars or {}
    names = ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]
    for name in names:
        saved[name] = os.environ.get(name)
        if name in target:
            os.environ[name] = target[name]
        else:
            os.environ.pop(name, None)
    try:
        result = validate_credential_ready_path_switch(
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


def test_three_env_present_ready(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "u",
            "WORDPRESS_APP_PASSWORD": "p",
        },
    )
    assert result["status"] == "CREDENTIAL_READY_PATH_AVAILABLE_NO_SECRET_OUTPUT"


def test_one_env_missing_not_ready(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "u",
        },
    )
    assert result["status"] == "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS"


def test_all_env_missing_not_ready(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIAL_READY_PATH_NOT_AVAILABLE_MISSING_CREDENTIALS"


def test_values_not_in_result(tmp_path):
    result = run_case(
        tmp_path,
        env_vars={
            "WORDPRESS_BASE_URL": "https://example.com",
            "WORDPRESS_USERNAME": "alice",
            "WORDPRESS_APP_PASSWORD": "topsecret",
        },
    )
    dumped = json.dumps(result)
    assert "alice" not in dumped
    assert "topsecret" not in dumped


def test_lengths_not_in_result(tmp_path):
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


def test_phase821_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_phase821_wrong_status_abort(tmp_path):
    result = run_case(tmp_path, phase821_status="FAIL")
    assert result["status"] == "ABORT"
