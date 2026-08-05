"""Tests for generate_phase8_34_one_time_manual_rerun_lock."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_34_one_time_manual_rerun_lock import (  # noqa: E402
    generate_one_time_manual_rerun_lock,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-34",
        "name": "one_time_manual_rerun_lock_policy",
        "policy_status": "LOCK_PACKAGE_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "lock_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "max_manual_rerun_count": 1,
        "required_evidence": ["exchange/logs/phase8_33_post_provision_env_recheck_result.json"],
        "ready_env_status": "POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
        "not_ready_statuses": [
            "POST_PROVISION_ENV_MISSING_NO_SECRET_OUTPUT",
            "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION",
        ],
        "non_secret_lock_fields": [
            "phase",
            "target_item_count",
            "max_manual_rerun_count",
            "commands_executed_in_this_phase",
            "phase8_6_to_8_10_executed",
        ],
        "forbidden_lock_fields": [
            "WORDPRESS_BASE_URL",
            "WORDPRESS_USERNAME",
            "WORDPRESS_APP_PASSWORD",
            "authorization",
            "password",
            "secret",
        ],
        "allowed_next_step": "Phase 8-35 final READY/BLOCKED decision before manually rerunning existing Phase 8-6 to Phase 8-10",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    env_status: str = "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION",
    include_evidence: bool = True,
    secret_values_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    pol = cfg / "policy.json"
    pol.write_text(json.dumps(p), encoding="utf-8")

    if include_evidence:
        logs = tmp_path / "exchange" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "phase8_33_post_provision_env_recheck_result.json").write_text(
            json.dumps({"status": env_status, "secret_values_written": secret_values_written}), encoding="utf-8"
        )

    return generate_one_time_manual_rerun_lock(
        policy_path=pol,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_env_ready_status(tmp_path):
    result = run_case(tmp_path, env_status="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED"


def test_env_missing_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "ONE_TIME_RERUN_LOCK_BLOCKED_CREDENTIALS_MISSING"


def test_evidence_missing_status(tmp_path):
    result = run_case(tmp_path, include_evidence=False)
    assert result["status"] == "ONE_TIME_RERUN_LOCK_NOT_READY"


def test_evidence_abort_status(tmp_path):
    result = run_case(tmp_path, env_status="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_in_evidence_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_lock_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["lock_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    p = base_policy()
    p["commands_executed_in_this_phase"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_phase8_6_to_8_10_executed_true_abort(tmp_path):
    p = base_policy()
    p["phase8_6_to_8_10_executed"] = True
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


def test_target_item_count_two_abort(tmp_path):
    p = base_policy()
    p["target_item_count"] = 2
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_max_manual_rerun_count_two_abort(tmp_path):
    p = base_policy()
    p["max_manual_rerun_count"] = 2
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_lock_contains_password_field_abort(tmp_path):
    p = base_policy()
    p["non_secret_lock_fields"] = p["non_secret_lock_fields"] + ["WORDPRESS_APP_PASSWORD"]
    result = run_case(tmp_path, policy=p, env_status="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "ABORT"
