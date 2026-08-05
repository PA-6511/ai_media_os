"""Tests for validate_phase8_14_rerun_authorization_renewal."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_14_rerun_authorization_renewal import (  # noqa: E402
    validate_rerun_authorization_renewal,
)

EXAMPLE_REVIEW = ROOT / "exchange/human_review/phase8_14_rerun_authorization_renewal.example.json"


def base_policy() -> dict:
    return {
        "phase": "Phase 8-14",
        "name": "rerun_authorization_renewal_policy",
        "policy_status": "AUTHORIZATION_RENEWAL_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "authorization_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": [
            "exchange/logs/phase8_13_post_credential_readiness_recheck_result.json"
        ],
        "required_credential_ready_status": "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
        "allowed_if_not_ready_status": "POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
        "allowed_decisions": [
            "ACKNOWLEDGE_RERUN_AUTHORIZATION_RENEWAL_ONLY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "forbidden_decisions": [
            "APPROVE_PUBLISH",
            "APPROVE_UPDATE",
            "APPROVE_DELETE",
            "APPROVE_BULK_RUN",
            "APPROVE_EXPORT",
        ],
        "required_acknowledgements": [
            "acknowledged_credentials_checked_without_secret_output",
            "acknowledged_single_item_only",
            "acknowledged_draft_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
            "acknowledged_no_auto_cleanup",
            "acknowledged_manual_review_after_creation",
        ],
        "approval_scope_required": {
            "rerun_handoff_only": True,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "allowed_next_step": "Phase 8-15 rerun handoff report for Phase 8-6 to Phase 8-10 re-execution",
    }


def base_review() -> dict:
    return {
        "review_id": "phase8_14_rerun_authorization_renewal_001",
        "phase": "Phase 8-14",
        "operator": "human",
        "decision": "ACKNOWLEDGE_RERUN_AUTHORIZATION_RENEWAL_ONLY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "acknowledged_credentials_checked_without_secret_output": True,
        "acknowledged_single_item_only": True,
        "acknowledged_draft_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "acknowledged_no_auto_cleanup": True,
        "acknowledged_manual_review_after_creation": True,
        "approval_scope": {
            "rerun_handoff_only": True,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "note": "Rerun authorization renewal only. This is not direct execution permission.",
    }


def _write_evidence(tmp_path: Path, status: str = "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT") -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_13_post_credential_readiness_recheck_result.json").write_text(
        json.dumps({"status": status}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    review: dict | None = None,
    phase813_status: str = "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT",
    missing_evidence: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    rv = copy.deepcopy(review) if review is not None else base_review()

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "phase8_14_rerun_authorization_renewal.json"

    if not missing_evidence:
        _write_evidence(tmp_path, phase813_status)

    p["required_evidence"] = [
        "exchange/logs/phase8_13_post_credential_readiness_recheck_result.json"
    ]
    pol_path.write_text(json.dumps(p), encoding="utf-8")
    review_path.write_text(json.dumps(rv), encoding="utf-8")

    return validate_rerun_authorization_renewal(
        policy_path=pol_path,
        human_review_path=review_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_credentials_ready_acknowledge_renewed(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY"


def test_credentials_not_ready_not_ready_status(tmp_path):
    result = run_case(tmp_path, phase813_status="POST_CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "RERUN_AUTHORIZATION_NOT_READY_CREDENTIALS_MISSING"


def test_evidence_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_forbidden_decision_approve_publish_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "APPROVE_PUBLISH"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_forbidden_decision_approve_update_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "APPROVE_UPDATE"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_forbidden_decision_approve_delete_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "APPROVE_DELETE"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_forbidden_decision_approve_bulk_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "APPROVE_BULK_RUN"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_decision_reject_fail(tmp_path):
    rv = base_review()
    rv["decision"] = "REJECT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"


def test_decision_request_fix_warn(tmp_path):
    rv = base_review()
    rv["decision"] = "REQUEST_FIX"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "WARN"


def test_decision_abort_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "ABORT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_missing_acknowledgement_fail(tmp_path):
    rv = base_review()
    rv["acknowledged_no_publish"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"
    assert any("acknowledged_no_publish" in e for e in result["errors"])


def test_wrong_approval_scope_fail(tmp_path):
    rv = base_review()
    rv["approval_scope"]["publish"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"


def test_authorization_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["authorization_is_execution_permission"] = True
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


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["authorization_is_execution_permission"] is False
    assert result["secret_values_written"] is False


def test_real_example_review(tmp_path):
    """Test with the real example human review file from the repo."""
    _write_evidence(tmp_path, "POST_CREDENTIALS_READY_NO_SECRET_OUTPUT")
    ev_rel = "exchange/logs/phase8_13_post_credential_readiness_recheck_result.json"
    p = base_policy()
    p["required_evidence"] = [ev_rel]

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    result = validate_rerun_authorization_renewal(
        policy_path=pol_path,
        human_review_path=EXAMPLE_REVIEW,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )
    assert result["status"] == "RERUN_AUTHORIZATION_RENEWED_FOR_HANDOFF_ONLY"
