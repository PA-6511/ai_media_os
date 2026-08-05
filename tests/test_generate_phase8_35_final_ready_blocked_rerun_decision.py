"""Tests for generate_phase8_35_final_ready_blocked_rerun_decision."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_35_final_ready_blocked_rerun_decision import (  # noqa: E402
    generate_final_ready_blocked_rerun_decision,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-35",
        "name": "final_ready_blocked_rerun_decision_policy",
        "policy_status": "FINAL_READY_BLOCKED_DECISION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "auto_post": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_31_secret_safe_credential_procedure_result.json",
            "exchange/logs/phase8_32_provisioned_declaration_overlay_result.json",
            "exchange/logs/phase8_33_post_provision_env_recheck_result.json",
            "exchange/logs/phase8_34_one_time_manual_rerun_lock.json",
        ],
        "ready_statuses": {
            "phase8_31": "PASS_PROCEDURE_ONLY",
            "phase8_32": "OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
            "phase8_33": "POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
            "phase8_34": "ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
        },
        "blocked_statuses": [
            "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
            "POST_PROVISION_ENV_MISSING_NO_SECRET_OUTPUT",
            "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION",
            "ONE_TIME_RERUN_LOCK_BLOCKED_CREDENTIALS_MISSING",
        ],
        "planned_manual_commands_if_ready": [
            "python3 scripts/validate_phase8_6_wordpress_credentials_readiness.py",
            "python3 scripts/validate_phase8_7_rerun_approval_review.py",
            "python3 scripts/validate_phase8_8_final_credentialed_live_preflight.py",
            "python3 scripts/run_phase8_9_first_one_item_wordpress_draft_create_rerun.py",
            "python3 scripts/generate_phase8_10_post_rerun_closure_report.py",
        ],
        "forbidden_command_patterns": [
            "curl -X POST",
            "curl -u",
            "requests.post(",
            "wp post create",
            "wp-json/wp/v2/posts",
            "export WORDPRESS_APP_PASSWORD=",
            "WORDPRESS_APP_PASSWORD=",
        ],
        "allowed_next_step_if_ready": "Human operator may manually rerun existing Phase 8-6 to Phase 8-10 commands exactly once",
        "allowed_next_step_if_blocked": "Keep NO_GO and do not rerun until credentials are ready",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    s31: str = "PASS_PROCEDURE_ONLY",
    s32: str = "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT",
    s33: str = "POST_PROVISION_ENV_NOT_READY_BY_DECLARATION",
    s34: str = "ONE_TIME_RERUN_LOCK_BLOCKED_CREDENTIALS_MISSING",
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
        payloads = {
            "phase8_31_secret_safe_credential_procedure_result.json": s31,
            "phase8_32_provisioned_declaration_overlay_result.json": s32,
            "phase8_33_post_provision_env_recheck_result.json": s33,
            "phase8_34_one_time_manual_rerun_lock.json": s34,
        }
        for name, status in payloads.items():
            (logs / name).write_text(
                json.dumps({"status": status, "secret_values_written": secret_values_written}), encoding="utf-8"
            )

    return generate_final_ready_blocked_rerun_decision(
        policy_path=pol,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_all_ready_status(tmp_path):
    result = run_case(
        tmp_path,
        s32="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        s33="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
        s34="ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
    )
    assert result["status"] == "READY_FOR_EXISTING_PHASE8_6_TO_8_10_MANUAL_RERUN_BUT_NOT_EXECUTED"


def test_credentials_missing_blocked(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "BLOCKED_CREDENTIALS_MISSING"


def test_evidence_missing_not_ready(tmp_path):
    result = run_case(tmp_path, include_evidence=False)
    assert result["status"] == "RERUN_DECISION_NOT_READY"


def test_evidence_abort_abort(tmp_path):
    result = run_case(tmp_path, s33="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_abort(tmp_path):
    result = run_case(tmp_path, secret_values_written=True)
    assert result["status"] == "ABORT"


def test_decision_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["decision_is_execution_permission"] = True
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


def test_auto_post_true_abort(tmp_path):
    p = base_policy()
    p["auto_post"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_planned_command_contains_curl_post_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["curl -X POST https://example.com"]
    result = run_case(
        tmp_path,
        policy=p,
        s32="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        s33="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
        s34="ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
    )
    assert result["status"] == "ABORT"


def test_planned_command_contains_password_assignment_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["WORDPRESS_APP_PASSWORD=abc python3 x.py"]
    result = run_case(
        tmp_path,
        policy=p,
        s32="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        s33="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
        s34="ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
    )
    assert result["status"] == "ABORT"


def test_planned_command_contains_wp_json_abort(tmp_path):
    p = base_policy()
    p["planned_manual_commands_if_ready"] = ["echo wp-json/wp/v2/posts"]
    result = run_case(
        tmp_path,
        policy=p,
        s32="OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT",
        s33="POST_PROVISION_ENV_READY_NO_SECRET_OUTPUT",
        s34="ONE_TIME_RERUN_LOCK_READY_BUT_NOT_EXECUTED",
    )
    assert result["status"] == "ABORT"
