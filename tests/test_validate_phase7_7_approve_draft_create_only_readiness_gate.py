import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_7_approve_draft_create_only_readiness_gate import validate_gate


def base_policy() -> dict:
    return {
        "phase": "Phase 7-7",
        "name": "approve_draft_create_only_readiness_gate",
        "gate_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "approve_draft_create_only_currently_allowed": False,
        "readiness_is_activation": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "required_evidence": [
            "exchange/logs/phase7_5_freeze_or_live_decision_report.json",
            "exchange/logs/phase7_6_human_approval_evidence_package_result.json",
        ],
        "required_conditions": {
            "phase7_5_status": "LIVE_CANDIDATE_BUT_LOCKED",
            "phase7_6_status": "PASS_DESIGN_ONLY",
            "target_item_count": 1,
            "human_approval_required": True,
            "publish_allowed": False,
            "wordpress_write_executed": False,
        },
        "dangerous_operations": {
            "auto_post": False,
            "auto_update": False,
            "auto_delete": False,
            "auto_export": False,
            "publish_allowed": False,
            "wordpress_write_executed": False,
            "bulk_execution": False,
            "external_write": False,
            "vps_self_builder_execution": False,
        },
    }


def base_request() -> dict:
    return {
        "phase": "Phase 7-7",
        "source": "APPROVE_DRAFT_CREATE_ONLY_READINESS_DRY_RUN",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_item_count": 1,
        "readiness_check_requested": True,
        "activation_requested": False,
        "approve_draft_create_only_requested": False,
        "human_approval_required": True,
        "safety_flags": {
            "production_status": "NO_GO",
            "wordpress_draft_creation": "NO_GO",
            "wordpress_write_executed": False,
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


def run_case(tmp_path: Path, policy: dict | None = None, req: dict | None = None, p75="LIVE_CANDIDATE_BUT_LOCKED", p76="PASS_DESIGN_ONLY", missing: str | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    r = copy.deepcopy(req or base_request())
    policy_path = tmp_path / "config/policy.json"
    request_path = tmp_path / "exchange/examples/req.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    request_path.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")

    e1 = tmp_path / p["required_evidence"][0]
    e2 = tmp_path / p["required_evidence"][1]
    e1.parent.mkdir(parents=True, exist_ok=True)
    e2.parent.mkdir(parents=True, exist_ok=True)
    if missing != "p75":
        e1.write_text(json.dumps({"status": p75}), encoding="utf-8")
    if missing != "p76":
        e2.write_text(json.dumps({"status": p76}), encoding="utf-8")

    return validate_gate(policy_path, request_path, out_json, out_md)


def test_normal_ready_but_locked(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "READY_BUT_LOCKED"


def test_missing_phase75_not_ready(tmp_path: Path):
    assert run_case(tmp_path, missing="p75")["status"] == "NOT_READY"


def test_phase76_fail_abort(tmp_path: Path):
    assert run_case(tmp_path, p76="FAIL")["status"] == "ABORT"


def test_activation_requested_abort(tmp_path: Path):
    r = base_request()
    r["activation_requested"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_approve_requested_abort(tmp_path: Path):
    r = base_request()
    r["approve_draft_create_only_requested"] = True
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_policy_approve_enabled_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_readiness_is_activation_abort(tmp_path: Path):
    p = base_policy()
    p["readiness_is_activation"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_unlock_true_abort(tmp_path: Path):
    p = base_policy()
    p["unlock_in_this_phase"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    r = base_request()
    r["target_item_count"] = 2
    assert run_case(tmp_path, req=r)["status"] == "ABORT"


def test_wordpress_write_true_abort(tmp_path: Path):
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
