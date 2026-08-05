import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_3_single_draft_final_preflight_design import validate_phase7_3_preflight_design


def base_policy() -> dict:
    return {
        "phase": "Phase 7-3",
        "name": "single_draft_final_preflight_design_policy",
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
            "exchange/logs/phase7_2_approve_draft_create_only_pre_unlock_review_result.json",
            "exchange/logs/phase6_9_hardening_preflight_report.json",
            "exchange/logs/phase6_10_existing_generated_test_fix_report.json",
        ],
        "acceptable_upstream_statuses": [
            "PASS",
            "PASS_DRY_RUN_ONLY",
            "PASS_DRY_RUN_ONLY_WITH_WARN",
            "ELIGIBLE_DRY_RUN_ONLY",
            "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN",
            "PASS_DESIGN_ONLY",
            "PASS_DESIGN_ONLY_WITH_WARN",
        ],
        "blocked_operations": ["wordpress_rest_post"],
        "allowed_next_step": "Phase 7-4 execution gate validation with NO_GO freeze maintained",
    }


def base_request() -> dict:
    return {
        "request_id": "phase7_3_final_preflight_request_001",
        "phase": "Phase 7-3",
        "decision_token": "APPROVE_DRAFT_CREATE_ONLY",
        "preflight_mode": "FINAL_PREFLIGHT_DESIGN_ONLY",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "single_item_lock": True,
        "human_approval": {
            "file_exists": True,
            "file_path": "exchange/human_review/phase7_3_single_draft_create_final_approval.example.json",
            "review_status": "UNDER_REVIEW",
            "approved_for_live_execution": False,
            "token": "APPROVE_DRAFT_CREATE_ONLY",
            "expired": False,
        },
        "freeze_plan": {
            "exists": True,
            "freeze_on_wordpress_write_attempt": True,
            "freeze_on_publish_attempt": True,
            "freeze_on_bulk_execution": True,
            "freeze_on_external_write": True,
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

    policy_path = tmp_path / "config/phase7_3_single_draft_final_preflight_design_policy.json"
    request_path = tmp_path / "exchange/examples/phase7_3_single_draft_final_preflight_request.example.json"
    out_json = tmp_path / "exchange/logs/result.json"
    out_md = tmp_path / "exchange/logs/result.md"

    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")

    sts = statuses or ["ELIGIBLE_DRY_RUN_ONLY", "PASS_DESIGN_ONLY", "PASS_DRY_RUN_ONLY", "PASS"]
    for idx, rel in enumerate(policy["required_upstream_evidence"]):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {"status": sts[idx]}
        if "phase6_9" in rel:
            payload = {"overall_status": sts[idx]}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return policy_path, request_path, out_json, out_md


def run_case(tmp_path: Path, policy: dict | None = None, request: dict | None = None, statuses: list[str] | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(request or base_request())
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, p, r, statuses)
    return validate_phase7_3_preflight_design(policy_path, request_path, out_json, out_md)


def test_normal_case_pass_design_only(tmp_path: Path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_DESIGN_ONLY"


def test_policy_execution_live_aborts(tmp_path: Path):
    policy = base_policy()
    policy["execution"] = "LIVE"
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_approve_flag_enabled_aborts(tmp_path: Path):
    policy = base_policy()
    policy["approve_draft_create_only_currently_allowed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_target_item_count_two_aborts(tmp_path: Path):
    request = base_request()
    request["target_item_count"] = 2
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_human_approval_missing_aborts(tmp_path: Path):
    request = base_request()
    request.pop("human_approval")
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_human_approval_expired_aborts(tmp_path: Path):
    request = base_request()
    request["human_approval"]["expired"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_human_approval_token_mismatch_aborts(tmp_path: Path):
    request = base_request()
    request["human_approval"]["token"] = "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY"
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_human_approval_live_approved_true_aborts(tmp_path: Path):
    request = base_request()
    request["human_approval"]["approved_for_live_execution"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_freeze_plan_missing_flag_aborts(tmp_path: Path):
    request = base_request()
    request["freeze_plan"]["freeze_on_publish_attempt"] = False
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_safety_flag_publish_allowed_true_aborts(tmp_path: Path):
    request = base_request()
    request["safety_flags"]["publish_allowed"] = True
    result = run_case(tmp_path, request=request)
    assert result["status"] == "ABORT"


def test_upstream_status_fail_aborts(tmp_path: Path):
    result = run_case(tmp_path, statuses=["FAIL", "PASS_DESIGN_ONLY", "PASS_DRY_RUN_ONLY", "PASS"])
    assert result["status"] == "ABORT"


def test_upstream_evidence_missing_aborts(tmp_path: Path):
    policy = base_policy()
    request = base_request()
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, policy, request)
    (tmp_path / policy["required_upstream_evidence"][0]).unlink()
    result = validate_phase7_3_preflight_design(policy_path, request_path, out_json, out_md)
    assert result["status"] == "ABORT"
