import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_4_execution_gate_no_go_freeze import validate_phase7_4_gate


def base_policy() -> dict:
    return {
        "phase": "Phase 7-4",
        "name": "execution_gate_no_go_freeze_policy",
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
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_rest_api_post": False,
            "wordpress_rest_api_put": False,
            "wordpress_rest_api_patch": False,
            "wordpress_rest_api_delete": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
        "required_upstream_evidence": [
            "exchange/logs/phase7_1_eligible_single_controlled_run_policy_result.json",
            "exchange/logs/phase7_2_approve_draft_create_only_pre_unlock_review_result.json",
            "exchange/logs/phase7_3_single_draft_final_preflight_design_result.json",
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
        "allowed_next_step": "Phase 7-5 freeze-or-live decision report generation",
        "blocked_next_steps": ["wordpress_draft_create"],
    }


def base_request() -> dict:
    return {
        "request_id": "phase7_4_execution_gate_validation_001",
        "phase": "Phase 7-4",
        "decision_token": "APPROVE_DRAFT_CREATE_ONLY",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "human_approval": {
            "required": True,
            "file_exists": True,
            "file_path": "exchange/human_review/phase7_3_single_draft_create_final_approval.example.json",
            "review_status": "UNDER_REVIEW",
            "token": "APPROVE_DRAFT_CREATE_ONLY",
        },
        "freeze_plan": {
            "exists": True,
            "freeze_on_missing_human_approval_file": True,
            "freeze_on_wordpress_write_attempt": True,
            "freeze_on_wordpress_rest_write_request": True,
            "freeze_on_bulk_execution": True,
            "freeze_on_external_write": True,
        },
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "approve_draft_create_only_currently_allowed": False,
            "unlock_in_this_phase": False,
            "publish_allowed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "wordpress_rest_api_post": False,
            "wordpress_rest_api_put": False,
            "wordpress_rest_api_patch": False,
            "wordpress_rest_api_delete": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def write_tree(tmp_path: Path, policy: dict, request: dict, statuses: list[str] | None = None) -> tuple[Path, Path, Path, Path]:
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exchange/examples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exchange/logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "exchange/human_review").mkdir(parents=True, exist_ok=True)

    policy_path = tmp_path / "config/phase7_4_execution_gate_no_go_freeze_policy.json"
    request_path = tmp_path / "exchange/examples/phase7_4_execution_gate_validation_request.example.json"
    out_json = tmp_path / "exchange/logs/result.json"
    out_md = tmp_path / "exchange/logs/result.md"

    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")

    human_file = tmp_path / "exchange/human_review/phase7_3_single_draft_create_final_approval.example.json"
    human_file.write_text(json.dumps({"phase": "Phase 7-3"}), encoding="utf-8")

    sts = statuses or ["ELIGIBLE_DRY_RUN_ONLY", "PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY"]
    for idx, rel in enumerate(policy["required_upstream_evidence"]):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"status": sts[idx]}), encoding="utf-8")

    return policy_path, request_path, out_json, out_md


def run_case(tmp_path: Path, policy: dict | None = None, request: dict | None = None, statuses: list[str] | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(request or base_request())
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, p, r, statuses)
    return validate_phase7_4_gate(policy_path, request_path, out_json, out_md)


def test_normal_case_pass_design_only(tmp_path: Path):
    result = run_case(tmp_path)
    assert result["status"] == "PASS_DESIGN_ONLY"


def test_target_item_count_not_1_aborts(tmp_path: Path):
    req = base_request()
    req["target_item_count"] = 2
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_human_approval_file_missing_aborts(tmp_path: Path):
    req = base_request()
    req["human_approval"]["file_exists"] = False
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_human_approval_token_mismatch_aborts(tmp_path: Path):
    req = base_request()
    req["human_approval"]["token"] = "APPROVE_SINGLE_DRAFT_CREATE_DRY_RUN_ONLY"
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_approve_token_enabled_in_policy_aborts(tmp_path: Path):
    policy = base_policy()
    policy["approve_draft_create_only_currently_allowed"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_unlock_in_this_phase_true_aborts(tmp_path: Path):
    policy = base_policy()
    policy["unlock_in_this_phase"] = True
    result = run_case(tmp_path, policy=policy)
    assert result["status"] == "ABORT"


def test_wordpress_rest_post_true_aborts(tmp_path: Path):
    req = base_request()
    req["safety_flags"]["wordpress_rest_api_post"] = True
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_aborts(tmp_path: Path):
    req = base_request()
    req["safety_flags"]["publish_allowed"] = True
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_freeze_plan_missing_flag_aborts(tmp_path: Path):
    req = base_request()
    req["freeze_plan"]["freeze_on_external_write"] = False
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"


def test_upstream_status_fail_aborts(tmp_path: Path):
    result = run_case(tmp_path, statuses=["FAIL", "PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY"])
    assert result["status"] == "ABORT"


def test_upstream_evidence_missing_aborts(tmp_path: Path):
    policy = base_policy()
    req = base_request()
    policy_path, request_path, out_json, out_md = write_tree(tmp_path, policy, req)
    (tmp_path / policy["required_upstream_evidence"][0]).unlink()
    result = validate_phase7_4_gate(policy_path, request_path, out_json, out_md)
    assert result["status"] == "ABORT"


def test_human_approval_review_status_invalid_aborts(tmp_path: Path):
    req = base_request()
    req["human_approval"]["review_status"] = "APPROVED"
    result = run_case(tmp_path, request=req)
    assert result["status"] == "ABORT"
