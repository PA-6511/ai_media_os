import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_phase8_4_post_execution_evidence import verify_post_execution_evidence


def base_policy() -> dict:
    return {
        "phase": "Phase 8-4",
        "name": "post_execution_verification_policy",
        "policy_status": "VERIFY_ONLY",
        "human_approval_required": True,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_cleanup_allowed": False,
        "auto_publish_allowed": False,
        "required_evidence": ["exchange/logs/phase8_3_first_one_item_wordpress_draft_create_result.json"],
        "success_status": "DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "not_executed_status": "NOT_EXECUTED_MISSING_CREDENTIALS",
        "failure_statuses": ["DRAFT_CREATE_FAILED_FREEZE_REQUIRED", "ABORT"],
        "required_success_fields": ["post_id", "post_status"],
        "required_post_status": "draft",
    }


def base_phase83(status="DRAFT_CREATED_PENDING_HUMAN_REVIEW") -> dict:
    return {
        "phase": "Phase 8-3",
        "status": status,
        "wordpress_write_executed": status == "DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "publish_allowed": False,
        "post_id": 123 if status == "DRAFT_CREATED_PENDING_HUMAN_REVIEW" else None,
        "post_status": "draft" if status == "DRAFT_CREATED_PENDING_HUMAN_REVIEW" else None,
    }


def run_case(tmp_path: Path, policy=None, phase83=None, missing=False):
    p = copy.deepcopy(policy or base_policy())
    e = copy.deepcopy(phase83 or base_phase83())

    policy_path = tmp_path / "config/policy.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")

    if not missing:
        ev = tmp_path / p["required_evidence"][0]
        ev.parent.mkdir(parents=True, exist_ok=True)
        ev.write_text(json.dumps(e, ensure_ascii=False, indent=2), encoding="utf-8")

    return verify_post_execution_evidence(policy_path, out_json, out_md)


def test_success_draft_verified(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW"


def test_not_executed_confirmed(tmp_path: Path):
    e = base_phase83("NOT_EXECUTED_MISSING_CREDENTIALS")
    assert run_case(tmp_path, phase83=e)["status"] == "NOT_EXECUTED_CONFIRMED"


def test_failed_freeze(tmp_path: Path):
    e = base_phase83("DRAFT_CREATE_FAILED_FREEZE_REQUIRED")
    assert run_case(tmp_path, phase83=e)["status"] == "FREEZE_REQUIRED"


def test_abort_freeze(tmp_path: Path):
    e = base_phase83("ABORT")
    assert run_case(tmp_path, phase83=e)["status"] == "FREEZE_REQUIRED"


def test_success_missing_post_id_freeze(tmp_path: Path):
    e = base_phase83("DRAFT_CREATED_PENDING_HUMAN_REVIEW")
    e["post_id"] = None
    assert run_case(tmp_path, phase83=e)["status"] == "FREEZE_REQUIRED"


def test_success_publish_abort(tmp_path: Path):
    e = base_phase83("DRAFT_CREATED_PENDING_HUMAN_REVIEW")
    e["post_status"] = "publish"
    assert run_case(tmp_path, phase83=e)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["publish_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_update_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["update_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_delete_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["delete_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_auto_cleanup_true_abort(tmp_path: Path):
    p = base_policy()
    p["auto_cleanup_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"
