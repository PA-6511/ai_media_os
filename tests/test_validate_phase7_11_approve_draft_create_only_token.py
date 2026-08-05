import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_11_approve_draft_create_only_token import validate_token


def base_policy() -> dict:
    return {
        "phase": "Phase 7-11",
        "name": "approve_draft_create_only_token_validation_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "token_validation_is_activation": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "required_evidence": ["exchange/logs/phase7_10_human_unlock_decision_result.json"],
        "required_phase7_10_status": "PASS_REVIEW_ONLY_NO_GO",
        "token_rules": {
            "token_name": "APPROVE_DRAFT_CREATE_ONLY",
            "token_may_be_requested_in_future_phase": True,
            "token_may_be_activated_in_phase7_11": False,
            "token_is_execution_permission_in_phase7_11": False,
            "requires_target_item_count": 1,
            "requires_human_approval_file": True,
            "requires_final_preflight": True,
            "requires_freeze_path": True,
        },
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


def base_request() -> dict:
    return {
        "phase": "Phase 7-11",
        "source": "APPROVE_DRAFT_CREATE_ONLY_TOKEN_VALIDATION_DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "token_name": "APPROVE_DRAFT_CREATE_ONLY",
        "token_validation_requested": True,
        "token_activation_requested": False,
        "token_execution_requested": False,
        "human_approval_required": True,
        "final_preflight_required": True,
        "freeze_path_exists": True,
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
            "wordpress_api_call_allowed": False,
            "publish_allowed": False,
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def run_case(tmp_path: Path, policy=None, req=None, evidence_status="PASS_REVIEW_ONLY_NO_GO", missing=False) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(req or base_request())
    policy_path = tmp_path / "config/policy.json"
    req_path = tmp_path / "exchange/examples/request.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    req_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    req_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    if not missing:
        e = tmp_path / p["required_evidence"][0]
        e.parent.mkdir(parents=True, exist_ok=True)
        e.write_text(json.dumps({"status": evidence_status}), encoding="utf-8")
    return validate_token(policy_path, req_path, out_json, out_md)


def test_normal_ready_but_locked(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "TOKEN_READY_BUT_LOCKED"


def test_evidence_missing_not_ready(tmp_path: Path):
    assert run_case(tmp_path, missing=True)["status"] == "TOKEN_NOT_READY"


def test_evidence_fail_abort(tmp_path: Path):
    assert run_case(tmp_path, evidence_status="FAIL")["status"] == "ABORT"


def test_token_validation_is_activation_abort(tmp_path: Path):
    p = base_policy()
    p["token_validation_is_activation"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_policy_approve_enabled_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_unlock_true_abort(tmp_path: Path):
    p = base_policy()
    p["unlock_in_this_phase"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_activation_requested_abort(tmp_path: Path):
    r = base_request()
    r["token_activation_requested"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_execution_requested_abort(tmp_path: Path):
    r = base_request()
    r["token_execution_requested"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    r = base_request()
    r["target_item_count"] = 2
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_final_preflight_false_not_ready(tmp_path: Path):
    r = base_request()
    r["final_preflight_required"] = False
    assert run_case(tmp_path, req=r)["status"] == "TOKEN_NOT_READY"


def test_freeze_path_false_not_ready(tmp_path: Path):
    r = base_request()
    r["freeze_path_exists"] = False
    assert run_case(tmp_path, req=r)["status"] == "TOKEN_NOT_READY"


def test_api_allowed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_write_executed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["wordpress_write_executed"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["publish_allowed"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_auto_post_true_abort(tmp_path: Path):
    r = base_request()
    r["safety_flags"]["auto_post"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"
