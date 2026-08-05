"""Tests for validate_phase8_16_credential_operator_confirmation."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_16_credential_operator_confirmation import (  # noqa: E402
    validate_credential_operator_confirmation,
)


def base_policy() -> dict:
    return {
        "phase": "Phase 8-16",
        "name": "credential_operator_confirmation_policy",
        "policy_status": "OPERATOR_CONFIRMATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "confirmation_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_11_credentials_manual_runbook_validation_result.json",
            "exchange/logs/phase8_12_no_secret_leak_audit_result.json",
            "exchange/logs/phase8_15_rerun_handoff_report.json",
        ],
        "required_statuses": {
            "phase8_11": "PASS_RUNBOOK_ONLY",
            "phase8_12": "NO_SECRET_LEAK_AUDIT_PASS",
        },
        "allowed_phase8_15_statuses": [
            "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING",
            "READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED",
        ],
        "allowed_decisions": [
            "CONFIRM_CREDENTIALS_PROVISIONED_OUTSIDE_REPO",
            "CONFIRM_CREDENTIALS_NOT_READY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "required_acknowledgements": [
            "acknowledged_no_secret_values_in_repo",
            "acknowledged_no_env_file_edit",
            "acknowledged_no_log_secret_output",
            "acknowledged_manual_secret_management_only",
            "acknowledged_no_wordpress_api_call_in_phase8_16",
            "acknowledged_single_item_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
        ],
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
        "allowed_next_step": "Phase 8-17 environment-only credential presence smoke check",
    }


def base_review() -> dict:
    return {
        "review_id": "phase8_16_credential_operator_confirmation_001",
        "phase": "Phase 8-16",
        "operator": "human",
        "decision": "CONFIRM_CREDENTIALS_NOT_READY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_no_secret_values_in_repo": True,
        "acknowledged_no_env_file_edit": True,
        "acknowledged_no_log_secret_output": True,
        "acknowledged_manual_secret_management_only": True,
        "acknowledged_no_wordpress_api_call_in_phase8_16": True,
        "acknowledged_single_item_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "secret_values_included": False,
        "approval_scope": {
            "credential_confirmation_only": True,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "note": "Operator confirmation only. No secret values are included. This is not execution permission.",
    }


def _write_evidence(
    tmp_path: Path,
    p811: str = "PASS_RUNBOOK_ONLY",
    p812: str = "NO_SECRET_LEAK_AUDIT_PASS",
    p815: str = "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING",
) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_11_credentials_manual_runbook_validation_result.json").write_text(
        json.dumps({"status": p811}), encoding="utf-8"
    )
    (ev_dir / "phase8_12_no_secret_leak_audit_result.json").write_text(
        json.dumps({"status": p812}), encoding="utf-8"
    )
    (ev_dir / "phase8_15_rerun_handoff_report.json").write_text(
        json.dumps({"status": p815}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    review: dict | None = None,
    p811: str = "PASS_RUNBOOK_ONLY",
    p812: str = "NO_SECRET_LEAK_AUDIT_PASS",
    p815: str = "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING",
    missing_phase815: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    rv = copy.deepcopy(review) if review is not None else base_review()
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "phase8_16_credential_operator_confirmation.json"

    _write_evidence(tmp_path, p811, p812, p815)
    if missing_phase815:
        (tmp_path / "exchange" / "logs" / "phase8_15_rerun_handoff_report.json").unlink()

    pol_path.write_text(json.dumps(p), encoding="utf-8")
    review_path.write_text(json.dumps(rv), encoding="utf-8")

    return validate_credential_operator_confirmation(
        policy_path=pol_path,
        human_review_path=review_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_decision_provisioned_status(tmp_path):
    rv = base_review()
    rv["decision"] = "CONFIRM_CREDENTIALS_PROVISIONED_OUTSIDE_REPO"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "CREDENTIAL_OPERATOR_CONFIRMED_PROVISIONED_NO_SECRET_OUTPUT"


def test_decision_not_ready_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "CREDENTIAL_OPERATOR_CONFIRMED_NOT_READY_NO_SECRET_OUTPUT"


def test_decision_request_fix_warn(tmp_path):
    rv = base_review()
    rv["decision"] = "REQUEST_FIX"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "WARN"


def test_decision_reject_fail(tmp_path):
    rv = base_review()
    rv["decision"] = "REJECT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"


def test_decision_abort_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "ABORT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_secret_values_included_true_abort(tmp_path):
    rv = base_review()
    rv["secret_values_included"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_target_item_count_two_abort(tmp_path):
    rv = base_review()
    rv["target_item_count"] = 2
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_ack_false_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_secret_values_in_repo"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_ack_no_api_false_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_wordpress_api_call_in_phase8_16"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_approval_scope_confirmation_false_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["credential_confirmation_only"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_approval_scope_draft_true_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["draft_create_only"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_confirmation_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["confirmation_is_execution_permission"] = True
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


def test_phase815_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_phase815=True)
    assert result["status"] == "ABORT"
