"""Regression test for Phase 8-14 design-only blocked behavior."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_14_draft_body_update_authorization_gate_design_only import (  # noqa: E402
    validate_phase8_14_draft_body_update_authorization_gate_design_only,
)


def test_phase8_13_request_fix_keeps_phase8_14_blocked(tmp_path):
    policy = {
        "phase": "Phase 8-14",
        "name": "draft_body_update_authorization_gate_design_only_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "target_post_id": 114,
        "required_evidence": [
            "exchange/logs/phase8_13_final_draft_fix_review_post_114_result.json"
        ],
        "required_previous_status": "PHASE8_13_APPROVE_FIX_DRY_RUN_ONLY",
        "blocked_previous_statuses": [
            "PHASE8_13_REQUEST_FIX",
            "PHASE8_13_REJECTED",
            "PENDING_REVIEW_INCOMPLETE"
        ],
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "gate_is_execution_permission": False,
        "allowed_next_step_if_ready": "ready-next-step",
        "allowed_next_step_if_blocked": "blocked-next-step",
    }

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    policy_path = config_dir / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    logs_dir = tmp_path / "exchange" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "phase8_13_final_draft_fix_review_post_114_result.json").write_text(
        json.dumps({"status": "PHASE8_13_REQUEST_FIX"}),
        encoding="utf-8",
    )

    result = validate_phase8_14_draft_body_update_authorization_gate_design_only(
        policy_path=policy_path,
        output_json_path=tmp_path / "out.json",
        output_md_path=tmp_path / "out.md",
    )

    assert result["status"] == "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_BLOCKED_PHASE8_13_REQUEST_FIX"
    assert result["previous_phase_status"] == "PHASE8_13_REQUEST_FIX"
    assert result["production_status"] == "NO_GO"
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["update_allowed"] is False
    assert result["delete_allowed"] is False
    assert result["export_allowed"] is False
    assert result["auto_post"] is False
    assert result["gate_is_execution_permission"] is False
