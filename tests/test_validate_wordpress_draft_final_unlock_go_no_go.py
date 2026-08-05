import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_final_unlock_go_no_go import run_validation, validate_final_unlock


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_final_unlock() -> dict:
    return {
        "phase": "Phase 6-8",
        "final_unlock_name": "wordpress_draft_final_unlock_go_no_go_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "final_unlock_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "final_decision": "NO_GO_DESIGN_LOCK",
        "decision_framework": {
            "allowed_values": [
                "GO_READY_FOR_MANUAL_APPROVAL_ONLY",
                "CONDITIONAL_GO_REQUIREMENTS_PENDING",
                "NO_GO_DESIGN_LOCK"
            ],
            "selected_value_in_phase6_8": "NO_GO_DESIGN_LOCK",
            "decision_locked_in_this_phase": True
        },
        "readiness_requirements": [
            "phase6_1_release_policy_validation_result.status == PASS",
            "phase6_2_preflight_gate_validation_result.status == PASS",
            "phase6_3_release_decision_rules_validation_result.status == PASS",
            "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
            "phase6_5_execution_spec_validation_result.status == PASS",
            "phase6_6_pre_execution_rehearsal_validation_result.status == PASS",
            "phase6_7_unlock_readiness_decision_result.status == PASS",
            "phase6_7_readiness_result == READINESS_DESIGN_PASS"
        ],
        "warn_clearance_requirements": {
            "phase5_warn_reviewed": True,
            "content_url_missing_warn_addressed_or_explicitly_overridden": True,
            "affiliate_tag_warn_addressed_or_explicitly_overridden": True,
            "explicit_human_override_record_required": True
        },
        "mandatory_no_go_locks": {
            "real_write_must_remain_disabled": True,
            "wordpress_rest_post_forbidden": True,
            "wordpress_rest_put_patch_forbidden": True,
            "publish_forbidden": True,
            "update_existing_post_forbidden": True,
            "delete_post_forbidden": True,
            "external_export_forbidden": True,
            "github_actions_trigger_forbidden": True,
            "slack_production_notification_forbidden": True,
            "vps_self_builder_execution_forbidden": True,
            "env_secret_credential_auto_edit_forbidden": True
        },
        "final_go_no_go_logic": {
            "all_readiness_requirements_pass_and_warns_handled": "GO_READY_FOR_MANUAL_APPROVAL_ONLY",
            "readiness_pass_but_warn_or_evidence_pending": "CONDITIONAL_GO_REQUIREMENTS_PENDING",
            "any_write_or_forbidden_action_detected": "NO_GO_DESIGN_LOCK",
            "phase6_8_default": "NO_GO_DESIGN_LOCK"
        },
        "hard_no_go_conditions": [
            "real_write_enabled == true",
            "wordpress_write_executed == true",
            "wordpress_rest_post_attempted == true",
            "wordpress_rest_put_patch_attempted == true",
            "publish_attempted == true",
            "update_existing_post_attempted == true",
            "delete_post_attempted == true",
            "external_export_attempted == true",
            "github_actions_trigger_attempted == true",
            "slack_production_notification_attempted == true",
            "vps_self_builder_execution_attempted == true",
            "env_secret_credential_auto_edit_attempted == true",
            "readiness_result_not_pass == true",
            "phase_gate_missing_or_failed == true"
        ],
        "forbidden_actions": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "update_existing_post",
            "delete_post",
            "bulk_posting",
            "external_export",
            "github_actions_trigger",
            "slack_production_notification",
            "cron_automation",
            "env_secret_auto_edit",
            "vps_self_builder_execution"
        ]
    }


def test_valid_final_unlock_pass():
    result = validate_final_unlock(base_final_unlock())
    assert result["status"] == "PASS"
    assert result["final_decision"] == "NO_GO_DESIGN_LOCK"


def test_real_write_enabled_true_aborts():
    d = base_final_unlock()
    d["real_write_enabled"] = True
    result = validate_final_unlock(d)
    assert result["status"] == "ABORT"


def test_wrong_final_decision_aborts():
    d = base_final_unlock()
    d["final_decision"] = "GO_READY_FOR_MANUAL_APPROVAL_ONLY"
    result = validate_final_unlock(d)
    assert result["status"] == "ABORT"


def test_missing_readiness_requirement_aborts():
    d = base_final_unlock()
    d["readiness_requirements"].remove("phase6_7_readiness_result == READINESS_DESIGN_PASS")
    result = validate_final_unlock(d)
    assert result["status"] == "ABORT"


def test_missing_warn_clearance_aborts():
    d = base_final_unlock()
    d["warn_clearance_requirements"]["affiliate_tag_warn_addressed_or_explicitly_overridden"] = False
    result = validate_final_unlock(d)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "final_unlock.json"
        out = base / "result.json"
        write_json(inp, base_final_unlock())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["final_unlock_status"] == "DESIGN_ONLY"
        assert saved["final_decision"] == "NO_GO_DESIGN_LOCK"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
