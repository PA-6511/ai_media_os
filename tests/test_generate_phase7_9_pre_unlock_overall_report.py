import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase7_9_pre_unlock_overall_report import generate_report


def base_policy() -> dict:
    return {
        "phase": "Phase 7-9",
        "name": "phase7_pre_unlock_overall_report_policy",
        "policy_status": "REPORT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "overall_is_execution_permission": False,
        "required_evidence": [
            "exchange/logs/phase7_1_eligible_single_controlled_run_policy_result.json",
            "exchange/logs/phase7_2_approve_draft_create_only_pre_unlock_review_result.json",
            "exchange/logs/phase7_3_single_draft_final_preflight_design_result.json",
            "exchange/logs/phase7_4_execution_gate_no_go_freeze_result.json",
            "exchange/logs/phase7_5_freeze_or_live_decision_report.json",
            "exchange/logs/phase7_6_human_approval_evidence_package_result.json",
            "exchange/logs/phase7_7_approve_draft_create_only_readiness_gate_result.json",
            "exchange/logs/phase7_8_single_draft_create_simulation_result.json",
        ],
        "acceptable_statuses": [
            "PASS",
            "PASS_DESIGN_ONLY",
            "ELIGIBLE_DRY_RUN_ONLY",
            "LIVE_CANDIDATE_BUT_LOCKED",
            "READY_BUT_LOCKED",
            "SIMULATION_PASS_DRY_RUN_ONLY",
            "PASS_DRY_RUN_ONLY",
            "PASS_DRY_RUN_ONLY_WITH_WARN",
        ],
        "warn_statuses": ["WARN", "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN"],
        "reject_statuses": ["FAIL", "ABORT", "NOT_ELIGIBLE", "NOT_READY", "FREEZE_MAINTAINED"],
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


def seed_evidence(tmp_path: Path, policy: dict, statuses: list[str], missing_idx: int | None = None):
    for idx, rel in enumerate(policy["required_evidence"]):
        if missing_idx is not None and idx == missing_idx:
            continue
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"status": statuses[idx]}), encoding="utf-8")


def run_case(tmp_path: Path, policy: dict | None = None, statuses: list[str] | None = None, missing_idx: int | None = None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    policy_path = tmp_path / "config/policy.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    sts = statuses or [
        "ELIGIBLE_DRY_RUN_ONLY",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
        "LIVE_CANDIDATE_BUT_LOCKED",
        "PASS_DESIGN_ONLY",
        "READY_BUT_LOCKED",
        "SIMULATION_PASS_DRY_RUN_ONLY",
    ]
    seed_evidence(tmp_path, p, sts, missing_idx)
    return generate_report(policy_path, out_json, out_md)


def test_normal_ready_but_no_go(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "PRE_UNLOCK_READY_BUT_NO_GO"


def test_warn_mixed_ready_with_warn(tmp_path: Path):
    sts = [
        "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
        "PASS_DESIGN_ONLY",
        "LIVE_CANDIDATE_BUT_LOCKED",
        "PASS_DESIGN_ONLY",
        "READY_BUT_LOCKED",
        "SIMULATION_PASS_DRY_RUN_ONLY",
    ]
    assert run_case(tmp_path, statuses=sts)["status"] == "PRE_UNLOCK_READY_WITH_WARN_BUT_NO_GO"


def test_missing_evidence_not_ready(tmp_path: Path):
    assert run_case(tmp_path, missing_idx=2)["status"] == "PRE_UNLOCK_NOT_READY"


def test_evidence_fail_not_ready(tmp_path: Path):
    sts = [
        "ELIGIBLE_DRY_RUN_ONLY",
        "PASS_DESIGN_ONLY",
        "FAIL",
        "PASS_DESIGN_ONLY",
        "LIVE_CANDIDATE_BUT_LOCKED",
        "PASS_DESIGN_ONLY",
        "READY_BUT_LOCKED",
        "SIMULATION_PASS_DRY_RUN_ONLY",
    ]
    assert run_case(tmp_path, statuses=sts)["status"] == "PRE_UNLOCK_NOT_READY"


def test_evidence_abort_not_ready(tmp_path: Path):
    sts = [
        "ELIGIBLE_DRY_RUN_ONLY",
        "PASS_DESIGN_ONLY",
        "ABORT",
        "PASS_DESIGN_ONLY",
        "LIVE_CANDIDATE_BUT_LOCKED",
        "PASS_DESIGN_ONLY",
        "READY_BUT_LOCKED",
        "SIMULATION_PASS_DRY_RUN_ONLY",
    ]
    assert run_case(tmp_path, statuses=sts)["status"] == "PRE_UNLOCK_NOT_READY"


def test_approve_flag_true_abort(tmp_path: Path):
    p = base_policy()
    p["approve_draft_create_only_currently_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_unlock_true_abort(tmp_path: Path):
    p = base_policy()
    p["unlock_in_this_phase"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_wordpress_write_true_abort(tmp_path: Path):
    p = base_policy()
    p["wordpress_write_executed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_api_call_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["dangerous_operations"]["wordpress_api_call_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path: Path):
    p = base_policy()
    p["publish_allowed"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_overall_is_execution_permission_true_abort(tmp_path: Path):
    p = base_policy()
    p["overall_is_execution_permission"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_auto_post_true_abort(tmp_path: Path):
    p = base_policy()
    p["dangerous_operations"]["auto_post"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"
