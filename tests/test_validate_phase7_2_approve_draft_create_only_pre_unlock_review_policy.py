import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_2_approve_draft_create_only_pre_unlock_review_policy import validate_phase7_2_policy


def base_policy() -> dict:
    return {
        "phase": "Phase 7-2",
        "name": "approve_draft_create_only_pre_unlock_review_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "eligible_is_execution_permission": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "required_upstream_evidence": [
            "exchange/logs/phase7_1_eligible_single_controlled_run_policy_result.json",
            "exchange/logs/phase6_9_hardening_preflight_report.json",
            "exchange/logs/phase6_10_existing_generated_test_fix_report.json",
        ],
        "acceptable_upstream_statuses": [
            "PASS",
            "PASS_DRY_RUN_ONLY",
            "PASS_DRY_RUN_ONLY_WITH_WARN",
            "ELIGIBLE_DRY_RUN_ONLY",
            "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN",
        ],
        "blocked_operations": ["wordpress_rest_post"],
        "allowed_next_step": "Phase 7-3 WordPress single draft final preflight design",
    }


def base_request() -> dict:
    return {
        "request_id": "phase7_2_pre_unlock_review_request_001",
        "phase": "Phase 7-2",
        "decision_token": "APPROVE_DRAFT_CREATE_ONLY",
        "review_mode": "PRE_UNLOCK_DESIGN_REVIEW_ONLY",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "single_item_lock": True,
        "human_approval_file": {
            "exists": True,
            "path": "exchange/human_review/phase7_2_approve_draft_create_only_pre_unlock_review.example.json",
            "review_status": "PENDING_REVIEW",
            "approved": False,
        },
        "reviewer_verification": {
            "exists": True,
            "reviewer_id": "reviewer_sample",
            "identity_verified": True,
        },
        "decision_expiry": {"exists": True, "expired": False},
        "freeze_conditions": {
            "exists": True,
            "freeze_on_wordpress_write_attempt": True,
            "freeze_on_bulk_execution": True,
            "freeze_on_external_write": True,
            "freeze_on_missing_preflight": True,
        },
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "approve_draft_create_only_currently_allowed": False,
            "unlock_in_this_phase": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def write_tree(tmp_path: Path, policy: dict, request: dict, statuses: list[str] | None = None) -> tuple[Path, Path, Path, Path]:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exchange/examples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exchange/logs").mkdir(parents=True, exist_ok=True)

    policy_path = tmp_path / "config/phase7_2_approve_draft_create_only_pre_unlock_review_policy.json"
    request_path = tmp_path / "exchange/examples/phase7_2_approve_draft_create_only_pre_unlock_review_request.example.json"
    out_json = tmp_path / "exchange/logs/result.json"
    out_md = tmp_path / "exchange/logs/result.md"

    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")

    sts = statuses or ["ELIGIBLE_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY", "PASS"]
    for idx, rel in enumerate(policy["required_upstream_evidence"]):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"phase": f"upstream-{idx}", "status": sts[idx]}
        if "phase6_9" in rel:
            payload = {"phase": "Phase 6-9", "overall_status": sts[idx]}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return policy_path, request_path, out_json, out_md


def run_case(tmp_path: Path, policy: dict | None = None, request: dict | None = None, statuses: list[str] | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(request or base_request())
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, p, r, statuses)
    return validate_phase7_2_policy(policy_path, request_path, out_json, out_md)


def test_normal_case_pass_design_only(tmp_path: Path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_DESIGN_ONLY"


def test_unlock_currently_allowed_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["approve_draft_create_only_currently_allowed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_unlock_in_this_phase_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["unlock_in_this_phase"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_execution_live_aborts(tmp_path: Path):
    policy = base_policy()
    policy["execution"] = "LIVE"
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_missing_upstream_evidence_aborts(tmp_path: Path):
    policy = base_policy()
    request = base_request()
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, policy, request)
    (tmp_path / policy["required_upstream_evidence"][0]).unlink()
    result = validate_phase7_2_policy(policy_path, request_path, out_json, out_md)
    assert result["status"] == "ABORT"


def test_upstream_fail_aborts(tmp_path: Path):
    result = run_case(tmp_path, statuses=["FAIL", "PASS_DRY_RUN_ONLY", "PASS"])
    assert result["status"] == "ABORT"


def test_human_approval_approved_true_aborts(tmp_path: Path):
    request = base_request()
    request["human_approval_file"]["approved"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_target_item_count_two_aborts(tmp_path: Path):
    request = base_request()
    request["target_item_count"] = 2
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_single_item_lock_false_aborts(tmp_path: Path):
    request = base_request()
    request["single_item_lock"] = False
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_expired_decision_aborts(tmp_path: Path):
    request = base_request()
    request["decision_expiry"]["expired"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_missing_freeze_condition_flag_aborts(tmp_path: Path):
    request = base_request()
    request["freeze_conditions"]["freeze_on_external_write"] = False
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_safety_flag_auto_post_true_aborts(tmp_path: Path):
    request = base_request()
    request["safety_flags"]["auto_post"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"
