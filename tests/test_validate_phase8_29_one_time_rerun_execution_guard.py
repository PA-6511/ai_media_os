"""Tests for validate_phase8_29_one_time_rerun_execution_guard."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_29_one_time_rerun_execution_guard import (  # noqa: E402
    validate_one_time_rerun_execution_guard,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-29",
        "name": "one_time_rerun_execution_guard_policy",
        "policy_status": "GUARD_VALIDATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "guard_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "auto_post": False,
        "target_item_count": 1,
        "max_manual_rerun_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_27_credential_ready_reevaluation_sequence.json",
            "exchange/logs/phase8_28_manual_rerun_dry_command_checklist_result.json",
        ],
        "ready_statuses": {
            "phase8_27": "REEVALUATION_SEQUENCE_READY_BUT_NOT_EXECUTED",
            "phase8_28": "PASS_DRY_COMMAND_CHECKLIST_ONLY",
        },
        "not_ready_statuses": [
            "REEVALUATION_SEQUENCE_NOT_READY_CREDENTIALS_MISSING",
            "REEVALUATION_SEQUENCE_NOT_READY",
        ],
        "guard_required_flags": {
            "target_item_count": 1,
            "max_manual_rerun_count": 1,
            "publish_allowed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "commands_executed_in_this_phase": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
        },
        "allowed_next_step": "Phase 8-30 final operator handoff for existing Phase 8-6 to Phase 8-10 rerun",
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    s27: str = "REEVALUATION_SEQUENCE_NOT_READY_CREDENTIALS_MISSING",
    s28: str = "PASS_DRY_COMMAND_CHECKLIST_ONLY",
    missing_evidence: bool = False,
    evidence_secret_written: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    pol = cfg / "policy.json"
    pol.write_text(json.dumps(p), encoding="utf-8")

    if not missing_evidence:
        logs = tmp_path / "exchange" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "phase8_27_credential_ready_reevaluation_sequence.json").write_text(
            json.dumps({"status": s27, "secret_values_written": evidence_secret_written}), encoding="utf-8"
        )
        (logs / "phase8_28_manual_rerun_dry_command_checklist_result.json").write_text(
            json.dumps({"status": s28, "secret_values_written": evidence_secret_written}), encoding="utf-8"
        )

    return validate_one_time_rerun_execution_guard(
        policy_path=pol,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_ready_status(tmp_path):
    result = run_case(tmp_path, s27="REEVALUATION_SEQUENCE_READY_BUT_NOT_EXECUTED")
    assert result["status"] == "ONE_TIME_RERUN_GUARD_READY_BUT_NOT_EXECUTED"


def test_not_ready_credentials_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "ONE_TIME_RERUN_GUARD_BLOCKED_CREDENTIALS_MISSING"


def test_evidence_missing_status(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ONE_TIME_RERUN_GUARD_NOT_READY"


def test_evidence_abort_status(tmp_path):
    result = run_case(tmp_path, s27="ABORT")
    assert result["status"] == "ABORT"


def test_secret_values_written_abort(tmp_path):
    result = run_case(tmp_path, evidence_secret_written=True)
    assert result["status"] == "ABORT"


def test_guard_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["guard_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    p = base_policy()
    p["commands_executed_in_this_phase"] = True
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


def test_auto_post_true_abort(tmp_path):
    p = base_policy()
    p["auto_post"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"
