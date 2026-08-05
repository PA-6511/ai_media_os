import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase8_5_first_controlled_draft_completion_report import generate_completion_report


def base_policy() -> dict:
    return {
        "phase": "Phase 8-5",
        "name": "first_controlled_draft_completion_report_policy",
        "policy_status": "REPORT_ONLY",
        "human_approval_required": True,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "required_evidence": [
            "exchange/logs/phase8_1_explicit_human_approval_result.json",
            "exchange/logs/phase8_2_final_live_preflight_result.json",
            "exchange/logs/phase8_3_first_one_item_wordpress_draft_create_result.json",
            "exchange/logs/phase8_4_post_execution_verification_result.json",
        ],
        "decision_rules": {
            "verified_pending_human_review": "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
            "not_executed": "FIRST_DRAFT_NOT_EXECUTED",
            "freeze_required": "FIRST_DRAFT_FREEZE_REQUIRED",
            "abort": "ABORT",
        },
        "allowed_next_step_on_success": "Phase 8-6 manual inspection of created WordPress draft",
        "allowed_next_step_on_not_executed": "Provide credentials or keep NO_GO, then rerun Phase 8-3 only after approval",
        "allowed_next_step_on_freeze": "Manual review and freeze investigation",
    }


def base_evidence() -> dict:
    return {
        "exchange/logs/phase8_1_explicit_human_approval_result.json": {"status": "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY", "publish_allowed": False},
        "exchange/logs/phase8_2_final_live_preflight_result.json": {"status": "FINAL_PREFLIGHT_PASS_READY_FOR_PHASE8_3_SINGLE_DRAFT_CREATE", "publish_allowed": False},
        "exchange/logs/phase8_3_first_one_item_wordpress_draft_create_result.json": {
            "status": "DRAFT_CREATED_PENDING_HUMAN_REVIEW",
            "publish_allowed": False,
            "post_id": 123,
            "post_status": "draft",
        },
        "exchange/logs/phase8_4_post_execution_verification_result.json": {"status": "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW", "publish_allowed": False},
    }


def run_case(tmp_path: Path, policy=None, evidence=None, missing=None):
    p = copy.deepcopy(policy or base_policy())
    ev = copy.deepcopy(evidence or base_evidence())
    missing = set(missing or [])

    policy_path = tmp_path / "config/policy.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")

    for rel in p["required_evidence"]:
        if rel in missing:
            continue
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(ev[rel], ensure_ascii=False, indent=2), encoding="utf-8")

    return generate_completion_report(policy_path, out_json, out_md)


def test_verified_pending_human_review(tmp_path: Path):
    r = run_case(tmp_path)
    assert r["status"] == "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert r["human_review_required"] is True


def test_not_executed(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_4_post_execution_verification_result.json"]["status"] = "NOT_EXECUTED_CONFIRMED"
    assert run_case(tmp_path, evidence=ev)["status"] == "FIRST_DRAFT_NOT_EXECUTED"


def test_freeze_required(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_4_post_execution_verification_result.json"]["status"] = "FREEZE_REQUIRED"
    assert run_case(tmp_path, evidence=ev)["status"] == "FIRST_DRAFT_FREEZE_REQUIRED"


def test_abort(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_4_post_execution_verification_result.json"]["status"] = "ABORT"
    assert run_case(tmp_path, evidence=ev)["status"] == "ABORT"


def test_evidence_missing_freeze(tmp_path: Path):
    r = run_case(tmp_path, missing={"exchange/logs/phase8_3_first_one_item_wordpress_draft_create_result.json"})
    assert r["status"] == "FIRST_DRAFT_FREEZE_REQUIRED"


def test_publish_allowed_true_abort(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_2_final_live_preflight_result.json"]["publish_allowed"] = True
    assert run_case(tmp_path, evidence=ev)["status"] == "ABORT"


def test_update_allowed_true_abort(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_2_final_live_preflight_result.json"]["update_allowed"] = True
    assert run_case(tmp_path, evidence=ev)["status"] == "ABORT"


def test_delete_allowed_true_abort(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_2_final_live_preflight_result.json"]["delete_allowed"] = True
    assert run_case(tmp_path, evidence=ev)["status"] == "ABORT"


def test_auto_post_true_abort(tmp_path: Path):
    ev = base_evidence()
    ev["exchange/logs/phase8_2_final_live_preflight_result.json"]["auto_post"] = True
    assert run_case(tmp_path, evidence=ev)["status"] == "ABORT"


def test_success_keeps_human_review_true(tmp_path: Path):
    r = run_case(tmp_path)
    assert r["status"] == "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW"
    assert r["human_review_required"] is True
