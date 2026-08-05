import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_1_explicit_human_approval import validate_explicit_human_approval


def base_policy() -> dict:
    return {
        "phase": "Phase 8-1",
        "name": "explicit_human_approval_policy",
        "policy_status": "APPROVAL_FILE_VALIDATION_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "approval_file_is_execution_permission": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "wordpress_api_call_allowed": False,
        "publish_allowed": False,
        "required_evidence": ["exchange/logs/phase7_14_pre_live_unlock_final_report.json"],
        "required_phase7_14_status": "READY_FOR_PHASE8_HUMAN_APPROVAL_BUT_NO_GO",
        "allowed_human_decisions": [
            "APPROVE_DRAFT_CREATE_ONLY_EXPLICIT_FOR_PHASE8_PREFLIGHT",
            "REQUEST_FIX",
            "REJECT",
            "ABORT",
        ],
        "forbidden_human_decisions": [
            "APPROVE_PUBLISH",
            "APPROVE_BULK_RUN",
            "APPROVE_UPDATE",
            "APPROVE_DELETE",
            "APPROVE_EXPORT",
        ],
        "required_acknowledgements": [
            "acknowledged_single_item_only",
            "acknowledged_draft_only",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_bulk",
            "acknowledged_freeze_on_mismatch",
            "acknowledged_manual_review_after_creation",
        ],
        "approval_scope_required": {
            "draft_create_only": True,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
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


def base_approval() -> dict:
    return {
        "review_id": "phase8_1_explicit_human_approval_001",
        "phase": "Phase 8-1",
        "operator": "human",
        "decision": "APPROVE_DRAFT_CREATE_ONLY_EXPLICIT_FOR_PHASE8_PREFLIGHT",
        "target_item_count": 1,
        "candidate_id": "phase7_1_sample_candidate_001",
        "approval_token": "APPROVE_DRAFT_CREATE_ONLY",
        "acknowledged_single_item_only": True,
        "acknowledged_draft_only": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_bulk": True,
        "acknowledged_freeze_on_mismatch": True,
        "acknowledged_manual_review_after_creation": True,
        "approval_scope": {
            "draft_create_only": True,
            "publish": False,
            "update": False,
            "delete": False,
            "bulk": False,
            "external_export": False,
        },
    }


def run_case(tmp_path: Path, policy=None, approval=None, evidence_status="READY_FOR_PHASE8_HUMAN_APPROVAL_BUT_NO_GO", missing_evidence=False):
    p = copy.deepcopy(policy or base_policy())
    a = copy.deepcopy(approval or base_approval())

    policy_path = tmp_path / "config/policy.json"
    approval_path = tmp_path / "exchange/human_review/approval.json"
    out_json = tmp_path / "exchange/logs/out.json"
    out_md = tmp_path / "exchange/logs/out.md"

    policy_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.parent.mkdir(parents=True, exist_ok=True)

    policy_path.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    approval_path.write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")

    if not missing_evidence:
        evidence = tmp_path / p["required_evidence"][0]
        evidence.parent.mkdir(parents=True, exist_ok=True)
        evidence.write_text(json.dumps({"status": evidence_status}), encoding="utf-8")

    return validate_explicit_human_approval(policy_path, approval_path, out_json, out_md)


def test_normal_ok(tmp_path: Path):
    assert run_case(tmp_path)["status"] == "APPROVAL_FILE_VALID_FOR_PREFLIGHT_ONLY"


def test_request_fix_warn(tmp_path: Path):
    a = base_approval()
    a["decision"] = "REQUEST_FIX"
    assert run_case(tmp_path, approval=a)["status"] == "WARN"


def test_reject_fail(tmp_path: Path):
    a = base_approval()
    a["decision"] = "REJECT"
    assert run_case(tmp_path, approval=a)["status"] == "FAIL"


def test_abort_abort(tmp_path: Path):
    a = base_approval()
    a["decision"] = "ABORT"
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_token_missing_abort(tmp_path: Path):
    a = base_approval()
    a.pop("approval_token")
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_token_wrong_abort(tmp_path: Path):
    a = base_approval()
    a["approval_token"] = "WRONG"
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_target_count_two_abort(tmp_path: Path):
    a = base_approval()
    a["target_item_count"] = 2
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_ack_no_publish_false_abort(tmp_path: Path):
    a = base_approval()
    a["acknowledged_no_publish"] = False
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_ack_manual_review_false_abort(tmp_path: Path):
    a = base_approval()
    a["acknowledged_manual_review_after_creation"] = False
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_scope_draft_false_abort(tmp_path: Path):
    a = base_approval()
    a["approval_scope"]["draft_create_only"] = False
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_scope_publish_true_abort(tmp_path: Path):
    a = base_approval()
    a["approval_scope"]["publish"] = True
    assert run_case(tmp_path, approval=a)["status"] == "ABORT"


def test_approval_file_is_execution_permission_true_abort(tmp_path: Path):
    p = base_policy()
    p["approval_file_is_execution_permission"] = True
    assert run_case(tmp_path, policy=p)["status"] == "ABORT"


def test_approve_currently_allowed_true_abort(tmp_path: Path):
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


def test_phase714_missing_abort(tmp_path: Path):
    assert run_case(tmp_path, missing_evidence=True)["status"] == "ABORT"


def test_phase714_wrong_status_abort(tmp_path: Path):
    assert run_case(tmp_path, evidence_status="NOT_READY")["status"] == "ABORT"
