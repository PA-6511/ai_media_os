"""Tests for generate_phase8_10_post_rerun_closure_report."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_phase8_10_post_rerun_closure_report import generate_post_rerun_closure_report  # noqa: E402


PHASE86_REL = "exchange/logs/phase8_6_wordpress_credentials_readiness_result.json"
PHASE87_REL = "exchange/logs/phase8_7_rerun_approval_review_result.json"
PHASE88_REL = "exchange/logs/phase8_8_final_credentialed_live_preflight_result.json"
PHASE89_REL = "exchange/logs/phase8_9_first_one_item_wordpress_draft_create_rerun_result.json"


def base_policy():
    return {
        "phase": "Phase 8-10",
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_cleanup_allowed": False,
        "auto_publish_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "required_evidence": [PHASE86_REL, PHASE87_REL, PHASE88_REL, PHASE89_REL],
        "decision_rules": {
            "rerun_draft_created": "RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW",
            "rerun_not_executed": "RERUN_NOT_EXECUTED_CONFIRMED",
            "rerun_failed": "RERUN_FREEZE_REQUIRED",
            "abort": "ABORT",
        },
        "allowed_next_step_on_success": "Phase 8-11 manual inspection of created WordPress draft",
        "allowed_next_step_on_not_executed": "Keep NO_GO, set credentials, rerun after review",
        "allowed_next_step_on_freeze": "Manual freeze investigation, no auto cleanup",
    }


def base_phase89_result(status: str = "RERUN_NOT_EXECUTED_MISSING_CREDENTIALS") -> dict:
    base = {
        "status": status,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "post_id": None,
        "post_status": None,
        "post_link": None,
    }
    if status == "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW":
        base["wordpress_write_executed"] = True
        base["post_id"] = 42
        base["post_status"] = "draft"
        base["post_link"] = "https://example.com/wp-admin/post.php?post=42"
    return base


def run_case(
    tmp_path: Path,
    policy: dict | None = None,
    phase89_status: str = "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY",
    phase89_override: dict | None = None,
    missing_evidence: bool = False,
):
    p = copy.deepcopy(policy) if policy is not None else base_policy()

    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps(p), encoding="utf-8")

    ev_dir = tmp_path / "exchange" / "logs"
    ev_dir.mkdir(parents=True, exist_ok=True)

    if not missing_evidence:
        for name, status in [
            ("phase8_6_wordpress_credentials_readiness_result.json", "CREDENTIALS_NOT_READY_NO_SECRET_OUTPUT"),
            ("phase8_7_rerun_approval_review_result.json", "PASS_RERUN_REVIEW_ONLY"),
            ("phase8_8_final_credentialed_live_preflight_result.json", "NOT_READY_CREDENTIALS_MISSING"),
        ]:
            (ev_dir / name).write_text(json.dumps({"status": status}), encoding="utf-8")

        phase89_data = phase89_override if phase89_override is not None else base_phase89_result(phase89_status)
        (ev_dir / "phase8_9_first_one_item_wordpress_draft_create_rerun_result.json").write_text(
            json.dumps(phase89_data), encoding="utf-8"
        )

        p["required_evidence"] = [
            str(ev_dir / "phase8_6_wordpress_credentials_readiness_result.json"),
            str(ev_dir / "phase8_7_rerun_approval_review_result.json"),
            str(ev_dir / "phase8_8_final_credentialed_live_preflight_result.json"),
            str(ev_dir / "phase8_9_first_one_item_wordpress_draft_create_rerun_result.json"),
        ]
        policy_file.write_text(json.dumps(p), encoding="utf-8")

    out_json = tmp_path / "out.json"
    out_md = tmp_path / "out.md"
    return generate_post_rerun_closure_report(policy_file, out_json, out_md)


def test_not_executed_credential_preflight_not_ready_confirms(tmp_path):
    result = run_case(tmp_path, phase89_status="NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY")
    assert result["status"] == "RERUN_NOT_EXECUTED_CONFIRMED"
    assert result["freeze_required"] is False
    assert result["post_id"] is None


def test_missing_credentials_not_executed_confirms(tmp_path):
    result = run_case(tmp_path, phase89_status="RERUN_NOT_EXECUTED_MISSING_CREDENTIALS")
    assert result["status"] == "RERUN_NOT_EXECUTED_CONFIRMED"
    assert result["freeze_required"] is False


def test_draft_created_verified(tmp_path):
    phase89 = base_phase89_result("RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW")
    result = run_case(tmp_path, phase89_status="RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW", phase89_override=phase89)
    assert result["status"] == "RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW"
    assert result["post_id"] == 42
    assert result["post_status"] == "draft"
    assert result["freeze_required"] is False


def test_draft_created_missing_post_id_freeze(tmp_path):
    phase89 = {
        "status": "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "wordpress_write_executed": True,
        "publish_allowed": False,
        "post_id": None,
        "post_status": "draft",
        "post_link": None,
    }
    result = run_case(tmp_path, phase89_override=phase89)
    assert result["status"] == "RERUN_FREEZE_REQUIRED"
    assert result["freeze_required"] is True


def test_draft_created_wrong_post_status_freeze(tmp_path):
    phase89 = {
        "status": "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "wordpress_write_executed": True,
        "publish_allowed": False,
        "post_id": 42,
        "post_status": "pending",
        "post_link": "https://example.com/wp-admin/post.php?post=42",
    }
    result = run_case(tmp_path, phase89_override=phase89)
    assert result["status"] == "RERUN_FREEZE_REQUIRED"


def test_phase89_failed_freeze(tmp_path):
    result = run_case(tmp_path, phase89_status="RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED")
    assert result["status"] == "RERUN_FREEZE_REQUIRED"
    assert result["freeze_required"] is True


def test_phase89_abort_propagates(tmp_path):
    phase89 = base_phase89_result("ABORT")
    phase89["status"] = "ABORT"
    result = run_case(tmp_path, phase89_override=phase89)
    assert result["status"] == "ABORT"


def test_abort_phase89_publish_status(tmp_path):
    phase89 = {
        "status": "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "wordpress_write_executed": True,
        "publish_allowed": False,
        "post_id": 42,
        "post_status": "publish",
        "post_link": "https://example.com/?p=42",
    }
    result = run_case(tmp_path, phase89_override=phase89)
    assert result["status"] == "ABORT"


def test_abort_phase89_publish_allowed_true(tmp_path):
    phase89 = base_phase89_result("NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY")
    phase89["publish_allowed"] = True
    result = run_case(tmp_path, phase89_override=phase89)
    assert result["status"] == "ABORT"


def test_abort_missing_evidence(tmp_path):
    result = run_case(tmp_path, missing_evidence=True)
    assert result["status"] in {"RERUN_FREEZE_REQUIRED", "ABORT"}
    assert result["freeze_required"] is True


def test_abort_policy_publish_allowed_true(tmp_path):
    pol = base_policy()
    pol["publish_allowed"] = True
    result = run_case(tmp_path, policy=pol)
    assert result["status"] == "ABORT"


def test_fixed_safety_flags(tmp_path):
    result = run_case(tmp_path)
    assert result["publish_allowed"] is False
    assert result["update_allowed"] is False
    assert result["delete_allowed"] is False
    assert result["auto_cleanup_allowed"] is False
    assert result["auto_post"] is False
    assert result["auto_update"] is False
    assert result["auto_delete"] is False
    assert result["auto_export"] is False


def test_human_review_required(tmp_path):
    result = run_case(tmp_path)
    assert result["human_review_required"] is True
