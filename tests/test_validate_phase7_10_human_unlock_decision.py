import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_10_human_unlock_decision import validate_decision


def base_policy() -> dict:
    return {
        "phase": "Phase 7-10",
        "name": "human_unlock_decision_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "human_decision_is_execution_permission": False,
        "approve_draft_create_only_currently_allowed": False,
        "approve_draft_create_only_activation_allowed_in_this_phase": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "required_evidence": ["exchange/logs/phase7_9_pre_unlock_overall_report.json"],
        "required_phase7_9_status": "PRE_UNLOCK_READY_BUT_NO_GO",
        "allowed_decisions_in_phase7_10": [
            "ACKNOWLEDGE_UNLOCK_REVIEW_ONLY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "forbidden_decisions_in_phase7_10": [
            "APPROVE_DRAFT_CREATE_ONLY",
            "APPROVE_PUBLISH",
            "APPROVE_BULK_RUN",
            "APPROVE_UPDATE",
            "APPROVE_DELETE",
        ],
        "required_acknowledgements": [
            "acknowledged_no_go",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_single_item_only",
            "acknowledged_wordpress_write_not_allowed_in_phase7_10",
            "acknowledged_freeze_on_mismatch",
        ],
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_write_executed": False,
            "wordpress_api_call_allowed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def base_review() -> dict:
    return {
        "review_id": "phase7_10_human_unlock_review_001",
        "phase": "Phase 7-10",
        "operator": "human",
        "decision": "ACKNOWLEDGE_UNLOCK_REVIEW_ONLY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_no_go": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_single_item_only": True,
        "acknowledged_wordpress_write_not_allowed_in_phase7_10": True,
        "acknowledged_freeze_on_mismatch": True,
        "requested_token": "NONE",
        "approval_scope": {
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
    }


def run_case(tmp_path: Path, policy=None, review=None, evidence_status="PRE_UNLOCK_READY_BUT_NO_GO", missing_evidence=False) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(review or base_review())
    policy_path = tmp_path / "config/policy.json"
    review_path = tmp_path / "exchange/human_review/review.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    if not missing_evidence:
        e = tmp_path / p["required_evidence"][0]
        e.parent.mkdir(parents=True, exist_ok=True)
        e.write_text(json.dumps({"status": evidence_status}), encoding="utf-8")
    return validate_decision(policy_path, review_path, out_json, out_md)


def test_normal_pass_review_only(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "PASS_REVIEW_ONLY_NO_GO"


def test_request_fix_warn(tmp_path: Path):
    r = base_review()
    r["decision"] = "REQUEST_FIX"
    assert run_case(tmp_path, review=r)["status"] == "WARN"


def test_reject_fail(tmp_path: Path):
    r = base_review()
    r["decision"] = "REJECT"
    assert run_case(tmp_path, review=r)["status"] == "FAIL"


def test_abort_abort(tmp_path: Path):
    r = base_review()
    r["decision"] = "ABORT"
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_decision_approve_abort(tmp_path: Path):
    r = base_review()
    r["decision"] = "APPROVE_DRAFT_CREATE_ONLY"
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_requested_token_approve_abort(tmp_path: Path):
    r = base_review()
    r["requested_token"] = "APPROVE_DRAFT_CREATE_ONLY"
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    r = base_review()
    r["target_item_count"] = 2
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_ack_no_go_false_abort(tmp_path: Path):
    r = base_review()
    r["acknowledged_no_go"] = False
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_ack_wp_write_false_abort(tmp_path: Path):
    r = base_review()
    r["acknowledged_wordpress_write_not_allowed_in_phase7_10"] = False
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_scope_draft_true_abort(tmp_path: Path):
    r = base_review()
    r["approval_scope"]["draft_create_only"] = True
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_policy_approve_enabled_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_unlock_true_abort(tmp_path: Path):
    p = base_policy()
    p["unlock_in_this_phase"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_api_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_write_executed_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["publish_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_phase79_missing_abort(tmp_path: Path):
    assert run_case(tmp_path, missing_evidence=True)["status"] == "ABORT"


def test_phase79_wrong_status_abort(tmp_path: Path):
    assert run_case(tmp_path, evidence_status="PRE_UNLOCK_NOT_READY")["status"] == "ABORT"
