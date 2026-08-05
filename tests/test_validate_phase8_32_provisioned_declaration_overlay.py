"""Tests for validate_phase8_32_provisioned_declaration_overlay."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_32_provisioned_declaration_overlay import (  # noqa: E402
    validate_provisioned_declaration_overlay,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-32",
        "name": "provisioned_declaration_overlay_policy",
        "policy_status": "OVERLAY_REVIEW_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "overlay_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_31_secret_safe_credential_procedure_result.json",
            "exchange/logs/phase8_30_final_operator_rerun_handoff_report.json",
        ],
        "required_phase8_31_status": "PASS_PROCEDURE_ONLY",
        "allowed_phase8_30_statuses": [
            "OPERATOR_HANDOFF_BLOCKED_CREDENTIALS_MISSING",
            "OPERATOR_HANDOFF_READY_FOR_PHASE8_6_TO_8_10_RERUN_BUT_NOT_EXECUTED",
        ],
        "allowed_decisions": [
            "OVERLAY_DECLARE_CREDENTIALS_PROVISIONED_OUTSIDE_REPO",
            "OVERLAY_DECLARE_CREDENTIALS_STILL_NOT_READY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "required_acknowledgements": [
            "acknowledged_overlay_does_not_modify_prior_evidence",
            "acknowledged_no_secret_values_in_repo",
            "acknowledged_no_env_file_edit",
            "acknowledged_no_log_secret_output",
            "acknowledged_manual_secret_management_only",
            "acknowledged_no_wordpress_api_call_in_phase8_32",
            "acknowledged_no_phase8_6_to_8_10_execution_in_phase8_32",
            "acknowledged_single_item_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
        ],
        "approval_scope_required": {
            "provisioned_declaration_overlay_only": True,
            "manual_rerun_handoff": False,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "allowed_next_step": "Phase 8-33 post-provision environment recheck without secret output",
    }


def base_review() -> dict:
    return {
        "review_id": "phase8_32_provisioned_declaration_overlay_001",
        "phase": "Phase 8-32",
        "operator": "human",
        "decision": "OVERLAY_DECLARE_CREDENTIALS_STILL_NOT_READY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_overlay_does_not_modify_prior_evidence": True,
        "acknowledged_no_secret_values_in_repo": True,
        "acknowledged_no_env_file_edit": True,
        "acknowledged_no_log_secret_output": True,
        "acknowledged_manual_secret_management_only": True,
        "acknowledged_no_wordpress_api_call_in_phase8_32": True,
        "acknowledged_no_phase8_6_to_8_10_execution_in_phase8_32": True,
        "acknowledged_single_item_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "secret_values_included": False,
        "approval_scope": {
            "provisioned_declaration_overlay_only": True,
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
    include_phase831: bool = True,
    include_phase830: bool = True,
    phase831_status: str = "PASS_PROCEDURE_ONLY",
    phase830_status: str = "OPERATOR_HANDOFF_BLOCKED_CREDENTIALS_MISSING",
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    rv = copy.deepcopy(review) if review is not None else base_review()

    cfg = tmp_path / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    pol = cfg / "policy.json"
    pol.write_text(json.dumps(p), encoding="utf-8")

    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "review.json"
    review_path.write_text(json.dumps(rv), encoding="utf-8")

    logs = tmp_path / "exchange" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    if include_phase831:
        (logs / "phase8_31_secret_safe_credential_procedure_result.json").write_text(
            json.dumps({"status": phase831_status, "secret_values_written": False}), encoding="utf-8"
        )
    if include_phase830:
        (logs / "phase8_30_final_operator_rerun_handoff_report.json").write_text(
            json.dumps({"status": phase830_status, "secret_values_written": False}), encoding="utf-8"
        )

    return validate_provisioned_declaration_overlay(
        policy_path=pol,
        review_path=review_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_overlay_provisioned_status(tmp_path):
    rv = base_review()
    rv["decision"] = "OVERLAY_DECLARE_CREDENTIALS_PROVISIONED_OUTSIDE_REPO"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "OVERLAY_CREDENTIALS_DECLARED_PROVISIONED_NO_SECRET_OUTPUT"


def test_overlay_not_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "OVERLAY_CREDENTIALS_DECLARED_NOT_READY_NO_SECRET_OUTPUT"


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


def test_overlay_immutability_ack_false_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_overlay_does_not_modify_prior_evidence"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_no_phase8_6_to_8_10_ack_false_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_phase8_6_to_8_10_execution_in_phase8_32"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_overlay_only_false_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["provisioned_declaration_overlay_only"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_manual_rerun_handoff_true_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["manual_rerun_handoff"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_overlay_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["overlay_is_execution_permission"] = True
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


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_phase8_31_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, include_phase831=False)
    assert result["status"] == "ABORT"
