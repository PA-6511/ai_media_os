import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase7_14_pre_live_unlock_final_report import generate_report


def base_policy() -> dict:
    return {
        "phase": "Phase 7-14",
        "name": "pre_live_unlock_final_report_policy",
        "policy_status": "REPORT_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "final_report_is_execution_permission": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "required_evidence": [
            "exchange/logs/phase7_10_human_unlock_decision_result.json",
            "exchange/logs/phase7_11_approve_draft_create_only_token_validation_result.json",
            "exchange/logs/phase7_12_one_item_draft_execution_plan_result.json",
            "exchange/logs/phase7_13_operator_runbook_validation_result.json",
        ],
        "acceptable_statuses": [
            "PASS_REVIEW_ONLY_NO_GO",
            "TOKEN_READY_BUT_LOCKED",
            "EXECUTION_PLAN_READY_BUT_NO_GO",
            "PASS_RUNBOOK_ONLY",
        ],
        "warn_statuses": ["WARN"],
        "reject_statuses": ["FAIL", "ABORT", "TOKEN_NOT_READY", "NOT_READY"],
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


def run_case(tmp_path: Path, policy=None, statuses=None, missing_idx=None) -> dict:
    p = copy.deepcopy(policy or base_policy())
    policy_path = tmp_path / "config/policy.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    sts = statuses or [
        "PASS_REVIEW_ONLY_NO_GO",
        "TOKEN_READY_BUT_LOCKED",
        "EXECUTION_PLAN_READY_BUT_NO_GO",
        "PASS_RUNBOOK_ONLY",
    ]
    for idx, rel in enumerate(p["required_evidence"]):
        if missing_idx is not None and idx == missing_idx:
            continue
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"status": sts[idx]}), encoding="utf-8")
    return generate_report(policy_path, out_json, out_md)


def test_normal_ready_no_go(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "READY_FOR_PHASE8_HUMAN_APPROVAL_BUT_NO_GO"


def test_warn_mixed_ready_warn(tmp_path: Path):
    sts = ["WARN", "TOKEN_READY_BUT_LOCKED", "EXECUTION_PLAN_READY_BUT_NO_GO", "PASS_RUNBOOK_ONLY"]
    assert run_case(tmp_path, statuses=sts)["status"] == "READY_FOR_PHASE8_HUMAN_APPROVAL_WITH_WARN_BUT_NO_GO"


def test_missing_evidence_not_ready(tmp_path: Path):
    assert run_case(tmp_path, missing_idx=1)["status"] == "NOT_READY"


def test_evidence_fail_not_ready(tmp_path: Path):
    sts = ["PASS_REVIEW_ONLY_NO_GO", "FAIL", "EXECUTION_PLAN_READY_BUT_NO_GO", "PASS_RUNBOOK_ONLY"]
    assert run_case(tmp_path, statuses=sts)["status"] in {"NOT_READY", "ABORT"}


def test_evidence_abort_not_ready(tmp_path: Path):
    sts = ["PASS_REVIEW_ONLY_NO_GO", "ABORT", "EXECUTION_PLAN_READY_BUT_NO_GO", "PASS_RUNBOOK_ONLY"]
    assert run_case(tmp_path, statuses=sts)["status"] in {"NOT_READY", "ABORT"}


def test_final_report_is_execution_permission_true_abort(tmp_path: Path):
    p = base_policy()
    p["final_report_is_execution_permission"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_approve_enabled_true_abort(tmp_path: Path):
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


def test_auto_post_true_abort(tmp_path: Path):
    p = base_policy()
    p["dangerous_operations"]["auto_post"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"
