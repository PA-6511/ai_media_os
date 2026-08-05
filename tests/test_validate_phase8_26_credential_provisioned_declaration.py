"""Tests for validate_phase8_26_credential_provisioned_declaration."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_26_credential_provisioned_declaration import (  # noqa: E402
    validate_credential_provisioned_declaration,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-26",
        "name": "credential_provisioned_declaration_policy",
        "policy_status": "OPERATOR_DECLARATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "declaration_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": ["exchange/logs/phase8_25_final_manual_rerun_handoff_package.json"],
        "allowed_phase8_25_statuses": [
            "HANDOFF_BLOCKED_CREDENTIALS_MISSING",
            "READY_FOR_OPERATOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED",
        ],
        "required_env": ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"],
        "allowed_decisions": [
            "DECLARE_CREDENTIALS_PROVISIONED_OUTSIDE_REPO",
            "DECLARE_CREDENTIALS_STILL_NOT_READY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "required_acknowledgements": [
            "acknowledged_no_secret_values_in_repo",
            "acknowledged_no_env_file_edit",
            "acknowledged_no_log_secret_output",
            "acknowledged_manual_secret_management_only",
            "acknowledged_no_wordpress_api_call_in_phase8_26",
            "acknowledged_no_phase8_6_to_8_10_execution_in_phase8_26",
            "acknowledged_single_item_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
        ],
        "approval_scope_required": {
            "credential_declaration_only": True,
            "manual_rerun_handoff": False,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
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
            "commands_executed_in_this_phase": False,
        },
        "allowed_next_step": "Phase 8-27 credential-ready re-evaluation sequence planner",
    }


def base_review() -> dict:
    return {
        "review_id": "phase8_26_credential_provisioned_declaration_001",
        "phase": "Phase 8-26",
        "operator": "human",
        "decision": "DECLARE_CREDENTIALS_STILL_NOT_READY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_no_secret_values_in_repo": True,
        "acknowledged_no_env_file_edit": True,
        "acknowledged_no_log_secret_output": True,
        "acknowledged_manual_secret_management_only": True,
        "acknowledged_no_wordpress_api_call_in_phase8_26": True,
        "acknowledged_no_phase8_6_to_8_10_execution_in_phase8_26": True,
        "acknowledged_single_item_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "secret_values_included": False,
        "approval_scope": {
            "credential_declaration_only": True,
            "manual_rerun_handoff": False,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
    }


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    review: dict | None = None,
    phase825_status: str = "HANDOFF_BLOCKED_CREDENTIALS_MISSING",
    include_evidence: bool = True,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    rv = copy.deepcopy(review) if review is not None else base_review()

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "review.json"
    review_path.write_text(json.dumps(rv), encoding="utf-8")

    if include_evidence:
        logs = tmp_path / "exchange" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "phase8_25_final_manual_rerun_handoff_package.json").write_text(
            json.dumps({"status": phase825_status, "secret_values_written": False}), encoding="utf-8"
        )

    return validate_credential_provisioned_declaration(
        policy_path=pol_path,
        review_path=review_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_provisioned_status(tmp_path):
    rv = base_review()
    rv["decision"] = "DECLARE_CREDENTIALS_PROVISIONED_OUTSIDE_REPO"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT"


def test_not_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT"


def test_request_fix_warn(tmp_path):
    rv = base_review()
    rv["decision"] = "REQUEST_FIX"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "WARN"


def test_reject_fail(tmp_path):
    rv = base_review()
    rv["decision"] = "REJECT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"


def test_abort_decision_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "ABORT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_secret_values_included_abort(tmp_path):
    rv = base_review()
    rv["secret_values_included"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_target_item_count_two_abort(tmp_path):
    rv = base_review()
    rv["target_item_count"] = 2
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_missing_ack_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_secret_values_in_repo"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_missing_phase8_6_to_8_10_ack_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_phase8_6_to_8_10_execution_in_phase8_26"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_credential_declaration_only_false_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["credential_declaration_only"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_manual_rerun_handoff_true_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["manual_rerun_handoff"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_declaration_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["declaration_is_execution_permission"] = True
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


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_phase8_25_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, include_evidence=False)
    assert result["status"] == "ABORT"
