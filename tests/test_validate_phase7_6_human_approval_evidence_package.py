import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_6_human_approval_evidence_package import validate_package


def base_policy() -> dict:
    return {
        "phase": "Phase 7-6",
        "name": "human_approval_evidence_package_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "approval_is_execution_permission": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "required_human_approval_fields": [
            "review_id",
            "phase",
            "operator",
            "decision",
            "target_item_count",
            "candidate_id",
            "acknowledged_no_go",
            "acknowledged_no_publish",
            "acknowledged_single_item_only",
            "acknowledged_freeze_on_mismatch",
            "approval_scope",
        ],
        "forbidden_decisions_in_phase7_6": [
            "APPROVE_DRAFT_CREATE_ONLY",
            "APPROVE_PUBLISH",
            "APPROVE_BULK_RUN",
        ],
        "approval_scope_required": {
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
    }


def base_review() -> dict:
    return {
        "review_id": "phase7_6_human_approval_package_sample_001",
        "phase": "Phase 7-6",
        "operator": "human",
        "decision": "ACKNOWLEDGE_PRE_UNLOCK_REVIEW_ONLY",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_no_go": True,
        "acknowledged_no_publish": True,
        "acknowledged_single_item_only": True,
        "acknowledged_freeze_on_mismatch": True,
        "approval_scope": {
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
    }


def run_case(tmp_path: Path, policy: dict | None = None, review: dict | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(review or base_review())
    policy_path = tmp_path / "policy.json"
    review_path = tmp_path / "review.json"
    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    return validate_package(policy_path, review_path, out_json, out_md)


def test_normal_pass_design_only(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "PASS_DESIGN_ONLY"


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


def test_forbidden_decision_abort(tmp_path: Path):
    r = base_review()
    r["decision"] = "APPROVE_DRAFT_CREATE_ONLY"
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_target_item_count_two_abort(tmp_path: Path):
    r = base_review()
    r["target_item_count"] = 2
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_ack_no_go_false_abort(tmp_path: Path):
    r = base_review()
    r["acknowledged_no_go"] = False
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_ack_no_publish_false_abort(tmp_path: Path):
    r = base_review()
    r["acknowledged_no_publish"] = False
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_scope_draft_true_abort(tmp_path: Path):
    r = base_review()
    r["approval_scope"]["draft_create_only"] = True
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_scope_publish_true_abort(tmp_path: Path):
    r = base_review()
    r["approval_scope"]["publish"] = True
    assert run_case(tmp_path, review=r)["status"] == "ABORT"


def test_policy_approve_flag_true_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_policy_wordpress_write_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"
