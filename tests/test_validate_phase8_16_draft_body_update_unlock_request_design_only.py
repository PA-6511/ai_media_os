"""Regression test for Phase 8-16 design-only unlock request readiness."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase8_16_draft_body_update_unlock_request_design_only import (  # noqa: E402
    validate_phase8_16_draft_body_update_unlock_request_design_only,
)


def test_phase8_16_ready_when_phase8_15_locked_and_all_execution_flags_false(tmp_path):
    policy = {
        "phase": "Phase 8-16",
        "name": "draft_body_update_unlock_request_design_only_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "UNLOCK_REQUEST",
        "execution": "DRY_RUN",
        "target_post_id": 114,
        "required_evidence": [
            "exchange/logs/phase8_15_draft_body_update_execution_authorization_gate_design_only_result.json"
        ],
        "required_phase8_15_status": "PHASE8_15_DRAFT_BODY_UPDATE_EXECUTION_AUTHORIZATION_READY_BUT_LOCKED_DESIGN_ONLY_NO_EXECUTION",
        "required_phase8_15_gate_is_execution_permission": False,
        "required_phase8_15_production_status": "NO_GO",
        "unlock_request_is_execution_permission": False,
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
        "systemctl_restart_allowed": False,
        "systemctl_daemon_reload_allowed": False,
        "allowed_next_step_if_ready": "ready-next-step",
        "allowed_next_step_if_blocked": "blocked-next-step",
    }

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    policy_path = config_dir / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    logs_dir = tmp_path / "exchange" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "phase8_15_draft_body_update_execution_authorization_gate_design_only_result.json").write_text(
        json.dumps(
            {
                "status": "PHASE8_15_DRAFT_BODY_UPDATE_EXECUTION_AUTHORIZATION_READY_BUT_LOCKED_DESIGN_ONLY_NO_EXECUTION",
                "production_status": "NO_GO",
                "gate_is_execution_permission": False,
            }
        ),
        encoding="utf-8",
    )

    out_json = tmp_path / "out.json"
    result = validate_phase8_16_draft_body_update_unlock_request_design_only(
        policy_path=policy_path,
        output_json_path=out_json,
        output_md_path=tmp_path / "out.md",
    )
    persisted = json.loads(out_json.read_text(encoding="utf-8"))

    expected_status = "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION"
    assert result["status"] == expected_status
    assert persisted["status"] == expected_status
    assert result["phase8_15_status"] == "PHASE8_15_DRAFT_BODY_UPDATE_EXECUTION_AUTHORIZATION_READY_BUT_LOCKED_DESIGN_ONLY_NO_EXECUTION"
    assert result["production_status"] == "NO_GO"

    assert result["unlock_request_is_execution_permission"] is False
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_api_call_attempted"] is False
    assert result["wordpress_write_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["update_allowed"] is False
    assert result["delete_allowed"] is False
    assert result["export_allowed"] is False
    assert result["auto_post"] is False
    assert result["auto_update"] is False
    assert result["auto_delete"] is False
    assert result["auto_export"] is False
    assert result["gate_is_execution_permission"] is False
    assert result["systemctl_restart_allowed"] is False
    assert result["systemctl_daemon_reload_allowed"] is False
