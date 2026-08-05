"""Tests for validate_phase8_7_rerun_approval_review."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_7_rerun_approval_review import validate_rerun_approval_review  # noqa: E402


PHASE81_REL = "exchange/logs/phase8_1_explicit_human_approval_result.json"
PHASE85_REL = "exchange/logs/phase8_5_first_controlled_draft_completion_report.json"
PHASE86_REL = "exchange/logs/phase8_6_wordpress_credentials_readiness_result.json"


def base_policy():
    return {
        "phase": "Phase 8-7",
        "name": "rerun_approval_review_policy",
        "production_status": "NO_GO",
        "rerun_review_is_execution_permission": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_evidence": [PHASE81_REL, PHASE85_REL, PHASE86_REL],
        "required_statuses": {
            "phase8_1": "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY",
            "phase8_5": "FIRST_DRAFT_NOT_EXECUTED",
        },
        "allowed_credential_statuses": [
            "CREDENTIALS_READY_NO_SECRET_OUTPUT",
            "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
        ],
        "allowed_decisions": ["ACKNOWLEDGE_RERUN_REVIEW_ONLY", "REQUEST_FIX", "REJECT", "ABORT"],
        "forbidden_decisions": ["APPROVE_PUBLISH", "APPROVE_UPDATE", "APPROVE_DELETE", "APPROVE_BULK_RUN", "APPROVE_EXPORT"],
        "required_acknowledgements": [
            "acknowledged_previous_not_executed",
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
            "rerun_preflight_only": True,
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
        },
        "allowed_next_step": "Phase 8-8 final credentialed live-preflight",
    }


def base_review():
    return {
        "decision": "ACKNOWLEDGE_RERUN_REVIEW_ONLY",
        "target_item_count": 1,
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "acknowledged_previous_not_executed": True,
        "acknowledged_single_item_only": True,
        "acknowledged_draft_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "acknowledged_no_auto_cleanup": True,
        "acknowledged_manual_review_after_creation": True,
        "approval_scope": {
            "rerun_preflight_only": True,
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
    phase81_status: str = "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY",
    phase85_status: str = "FIRST_DRAFT_NOT_EXECUTED",
    phase86_status: str = "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT",
    missing_evidence: bool = False,
):
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    r = copy.deepcopy(review) if review is not None else base_review()

    policy_file = tmp_path / "policy.json"
    review_file = tmp_path / "review.json"
    policy_file.write_text(json.dumps(p), encoding="utf-8")
    review_file.write_text(json.dumps(r), encoding="utf-8")

    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    if not missing_evidence:
        (ev_dir / "phase8_1_explicit_human_approval_result.json").write_text(
            json.dumps({"status": phase81_status}), encoding="utf-8"
        )
        (ev_dir / "phase8_5_first_controlled_draft_completion_report.json").write_text(
            json.dumps({"status": phase85_status}), encoding="utf-8"
        )
        (ev_dir / "phase8_6_wordpress_credentials_readiness_result.json").write_text(
            json.dumps({"status": phase86_status}), encoding="utf-8"
        )
        p["required_evidence"] = [
            str(ev_dir / "phase8_1_explicit_human_approval_result.json"),
            str(ev_dir / "phase8_5_first_controlled_draft_completion_report.json"),
            str(ev_dir / "phase8_6_wordpress_credentials_readiness_result.json"),
        ]
        policy_file.write_text(json.dumps(p), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    return validate_rerun_approval_review(policy_file, review_file, out_json, out_md)


def test_normal_pass(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_RERUN_REVIEW_ONLY"


def test_request_fix_warn(tmp_path):
    r = base_review()
    r["decision"] = "REQUEST_FIX"
    result = run_case(tmp_path, review=r)
    assert result["status"] == "WARN"


def test_reject_fail(tmp_path):
    r = base_review()
    r["decision"] = "REJECT"
    result = run_case(tmp_path, review=r)
    assert result["status"] == "FAIL"


def test_abort_decision(tmp_path):
    r = base_review()
    r["decision"] = "ABORT"
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_forbidden_decision_publish(tmp_path):
    r = base_review()
    r["decision"] = "APPROVE_PUBLISH"
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_draft_create_only_scope_true(tmp_path):
    r = base_review()
    r["approval_scope"]["draft_create_only"] = True
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_rerun_preflight_only_false(tmp_path):
    r = base_review()
    r["approval_scope"]["rerun_preflight_only"] = False
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_wrong_approval_token(tmp_path):
    r = base_review()
    r["approval_token"] = "WRONG_TOKEN"
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_target_item_count_not_1(tmp_path):
    r = base_review()
    r["target_item_count"] = 2
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_missing_acknowledgement(tmp_path):
    r = base_review()
    r["acknowledged_no_bulk"] = False
    result = run_case(tmp_path, review=r)
    assert result["status"] == "ABORT"


def test_abort_phase86_invalid_credential_status(tmp_path):
    result = run_case(tmp_path, phase86_status="INVALID_STATUS")
    assert result["status"] == "ABORT"


def test_pass_credentials_ready(tmp_path):
    result = run_case(tmp_path, phase86_status="CREDENTIALS_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "PASS_RERUN_REVIEW_ONLY"


def test_pass_credentials_not_ready(tmp_path):
    result = run_case(tmp_path, phase86_status="CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT")
    assert result["status"] == "PASS_RERUN_REVIEW_ONLY"


def test_abort_phase81_wrong_status(tmp_path):
    result = run_case(tmp_path, phase81_status="WRONG_STATUS")
    assert result["status"] == "ABORT"


def test_abort_phase85_wrong_status(tmp_path):
    result = run_case(tmp_path, phase85_status="WRONG_STATUS")
    assert result["status"] == "ABORT"


def test_abort_evidence_missing(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"


def test_abort_api_call_allowed_true(tmp_path):
    pol = base_policy()
    pol["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["rerun_review_is_execution_permission"] is False
