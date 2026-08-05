"""Tests for validate_phase8_24_operator_go_no_go."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_24_operator_go_no_go import validate_operator_go_no_go  # noqa: E402


def base_policy() -> dict:
    return {
        "phase": "Phase 8-24",
        "name": "operator_go_no_go_policy",
        "policy_status": "GO_NO_GO_REVIEW_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "operator_decision_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "target_item_count": 1,
        "required_evidence": ["exchange/logs/phase8_23_pre_rerun_safety_snapshot.json"],
        "ready_snapshot_status": "SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED",
        "not_ready_snapshot_status": "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING",
        "allowed_decisions": [
            "OPERATOR_GO_FOR_MANUAL_RERUN_HANDOFF_ONLY",
            "OPERATOR_NO_GO_CREDENTIALS_MISSING",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "required_acknowledgements": [
            "acknowledged_decision_not_execution",
            "acknowledged_manual_rerun_only",
            "acknowledged_no_api_call_in_phase8_24",
            "acknowledged_single_item_only",
            "acknowledged_draft_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
            "acknowledged_no_secret_output",
        ],
        "approval_scope_required": {
            "manual_rerun_handoff_only": True,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "allowed_next_step": "Phase 8-25 final manual rerun handoff package",
    }


def base_review() -> dict:
    return {
        "review_id": "phase8_24_operator_go_no_go_001",
        "phase": "Phase 8-24",
        "operator": "human",
        "decision": "OPERATOR_NO_GO_CREDENTIALS_MISSING",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "acknowledged_decision_not_execution": True,
        "acknowledged_manual_rerun_only": True,
        "acknowledged_no_api_call_in_phase8_24": True,
        "acknowledged_single_item_only": True,
        "acknowledged_draft_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "acknowledged_no_secret_output": True,
        "secret_values_included": False,
        "approval_scope": {
            "manual_rerun_handoff_only": True,
            "draft_create_only": False,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
        "note": "Operator GO/NO-GO review only. This is not execution permission.",
    }


def _write_snapshot(tmp_path: Path, status: str) -> None:
    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / "phase8_23_pre_rerun_safety_snapshot.json").write_text(
        json.dumps({"status": status, "secret_values_written": False}), encoding="utf-8"
    )


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    review: dict | None = None,
    snapshot_status: str = "SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING",
    missing_evidence: bool = False,
) -> dict:
    p = copy.deepcopy(policy) if policy is not None else base_policy()
    rv = copy.deepcopy(review) if review is not None else base_review()

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    pol_path = config_dir / "policy.json"
    pol_path.write_text(json.dumps(p), encoding="utf-8")

    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path = review_dir / "review.json"
    review_path.write_text(json.dumps(rv), encoding="utf-8")

    if not missing_evidence:
        _write_snapshot(tmp_path, snapshot_status)

    return validate_operator_go_no_go(
        policy_path=pol_path,
        review_path=review_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )


def test_ready_plus_go_status(tmp_path):
    rv = base_review()
    rv["decision"] = "OPERATOR_GO_FOR_MANUAL_RERUN_HANDOFF_ONLY"
    result = run_case(tmp_path, review=rv, snapshot_status="SAFETY_SNAPSHOT_READY_BUT_NOT_EXECUTED")
    assert result["status"] == "OPERATOR_GO_RECORDED_FOR_HANDOFF_ONLY"


def test_not_ready_plus_no_go_status(tmp_path):
    result = run_case(tmp_path)
    assert result["status"] == "OPERATOR_NO_GO_CREDENTIALS_MISSING"


def test_not_ready_plus_go_abort(tmp_path):
    rv = base_review()
    rv["decision"] = "OPERATOR_GO_FOR_MANUAL_RERUN_HANDOFF_ONLY"
    result = run_case(tmp_path, review=rv, snapshot_status="SAFETY_SNAPSHOT_NOT_READY_CREDENTIALS_MISSING")
    assert result["status"] == "ABORT"


def test_request_fix_warn(tmp_path):
    rv = base_review()
    rv["decision"] = "REQUEST_FIX"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "WARN"


def test_reject_fail(tmp_path):
    rv = base_review()
    rv["decision"] = "REJECT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "FAIL"


def test_abort_status(tmp_path):
    rv = base_review()
    rv["decision"] = "ABORT"
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_secret_values_included_abort(tmp_path):
    rv = base_review()
    rv["secret_values_included"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_target_item_count_two_abort(tmp_path):
    rv = base_review()
    rv["target_item_count"] = 2
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_acknowledged_no_secret_output_false_abort(tmp_path):
    rv = base_review()
    rv["acknowledged_no_secret_output"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_manual_handoff_false_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["manual_rerun_handoff_only"] = False
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_scope_draft_true_abort(tmp_path):
    rv = base_review()
    rv["approval_scope"]["draft_create_only"] = True
    result = run_case(tmp_path, review=rv)
    assert result["status"] == "ABORT"


def test_operator_decision_is_execution_permission_true_abort(tmp_path):
    p = base_policy()
    p["operator_decision_is_execution_permission"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_commands_executed_true_abort(tmp_path):
    p = base_policy()
    p["commands_executed_in_this_phase"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_wordpress_api_call_allowed_true_abort(tmp_path):
    p = base_policy()
    p["wordpress_api_call_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_publish_allowed_true_abort(tmp_path):
    p = base_policy()
    p["publish_allowed"] = True
    result = run_case(tmp_path, policy=p)
    assert result["status"] == "ABORT"


def test_phase823_missing_abort(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] == "ABORT"
