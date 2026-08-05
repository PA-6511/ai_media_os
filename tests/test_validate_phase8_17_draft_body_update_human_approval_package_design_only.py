"""Regression test for Phase 8-17 design-only human approval package."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase8_17_draft_body_update_human_approval_package_design_only import (  # noqa: E402
    validate_phase8_17_draft_body_update_human_approval_package_design_only,
)


def test_phase8_17_ready_design_only_no_execution(tmp_path):
    policy = {
        "phase": "Phase 8-17",
        "name": "draft_body_update_human_approval_package_design_only_policy",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "mode": "HUMAN_APPROVAL_PACKAGE",
        "execution": "DRY_RUN",
        "target_post_id": 114,
        "human_approval_required": True,
        "required_evidence": [
            "exchange/logs/phase8_16_draft_body_update_unlock_request_design_only_result.json"
        ],
        "required_phase8_16_status": "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION",
        "required_phase8_16_production_status": "NO_GO",
        "required_human_approval_package": "exchange/human_review/phase8_17_draft_body_update_human_approval_package_post_114.json",
        "required_human_approval_fields": [
            "package_id",
            "phase",
            "operator",
            "decision",
            "target_post_id",
            "target_item_count",
            "summary",
            "acknowledged_no_go",
            "acknowledged_no_wordpress_api_call",
            "acknowledged_no_wordpress_write",
            "acknowledged_no_publish",
            "acknowledged_no_update",
            "acknowledged_no_delete",
            "acknowledged_no_export",
            "acknowledged_no_auto_post",
            "acknowledged_no_systemctl",
            "approval_scope",
            "change_request"
        ],
        "allowed_decisions": [
            "ACKNOWLEDGE_PACKAGE_READY_ONLY",
            "REQUEST_FIX",
            "REJECT",
            "ABORT"
        ],
        "forbidden_decisions": [
            "APPROVE_WORDPRESS_BODY_UPDATE",
            "APPROVE_PUBLISH",
            "APPROVE_AUTO_POST",
            "APPROVE_SYSTEMCTL_OPERATION"
        ],
        "approval_scope_required": {
            "wordpress_api_call": False,
            "wordpress_body_update": False,
            "publish": False,
            "update": False,
            "delete": False,
            "export": False,
            "auto_post": False,
            "systemctl": False,
            "credential_env_edit": False,
            "gate_is_execution_permission": False
        },
        "wordpress_api_call_allowed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_write_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "publish": False,
        "update": False,
        "delete": False,
        "export": False,
        "auto_post": False,
        "gate_is_execution_permission": False,
        "systemctl_restart_allowed": False,
        "systemctl_daemon_reload_allowed": False,
        "credential_env_edit_allowed": False,
        "allowed_next_step_if_ready": "ready-next-step",
        "allowed_next_step_if_blocked": "blocked-next-step"
    }

    package = {
        "package_id": "phase8_17_pkg_test_001",
        "phase": "Phase 8-17",
        "operator": "human",
        "decision": "ACKNOWLEDGE_PACKAGE_READY_ONLY",
        "target_post_id": 114,
        "target_item_count": 1,
        "summary": "design-only package",
        "acknowledged_no_go": True,
        "acknowledged_no_wordpress_api_call": True,
        "acknowledged_no_wordpress_write": True,
        "acknowledged_no_publish": True,
        "acknowledged_no_update": True,
        "acknowledged_no_delete": True,
        "acknowledged_no_export": True,
        "acknowledged_no_auto_post": True,
        "acknowledged_no_systemctl": True,
        "approval_scope": {
            "wordpress_api_call": False,
            "wordpress_body_update": False,
            "publish": False,
            "update": False,
            "delete": False,
            "export": False,
            "auto_post": False,
            "systemctl": False,
            "credential_env_edit": False,
            "gate_is_execution_permission": False
        },
        "change_request": {
            "intent": "package only",
            "execute_now": False,
            "requires_additional_human_approval_for_execution": True
        }
    }

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    policy_path = config_dir / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    review_dir = tmp_path / "exchange" / "human_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    package_path = review_dir / "phase8_17_draft_body_update_human_approval_package_post_114.json"
    package_path.write_text(json.dumps(package), encoding="utf-8")

    logs_dir = tmp_path / "exchange" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "phase8_16_draft_body_update_unlock_request_design_only_result.json").write_text(
        json.dumps(
            {
                "status": "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION",
                "production_status": "NO_GO"
            }
        ),
        encoding="utf-8",
    )

    out_json = tmp_path / "out.json"
    result = validate_phase8_17_draft_body_update_human_approval_package_design_only(
        policy_path=policy_path,
        package_path=package_path,
        output_json_path=out_json,
        output_md_path=tmp_path / "out.md",
    )

    persisted = json.loads(out_json.read_text(encoding="utf-8"))

    assert result["status"] == "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_READY_DESIGN_ONLY_NO_EXECUTION"
    assert persisted["status"] == "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_READY_DESIGN_ONLY_NO_EXECUTION"
    assert result["production_status"] == "NO_GO"
    assert result["human_approval_required"] is True
    assert result["wordpress_api_call_allowed"] is False
    assert result["wordpress_write_executed"] is False
    assert result["publish_allowed"] is False
    assert result["update_allowed"] is False
    assert result["delete_allowed"] is False
    assert result["export_allowed"] is False
    assert result["publish"] is False
    assert result["update"] is False
    assert result["delete"] is False
    assert result["export"] is False
    assert result["auto_post"] is False
    assert result["gate_is_execution_permission"] is False
