import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_controlled_unlock_plan import run_validation, validate_plan


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_plan() -> dict:
    return {
        "phase": "Phase 6-4",
        "plan_name": "wordpress_draft_controlled_unlock_plan_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "plan_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "unlock_target": {
            "decision_token": "APPROVE_DRAFT_CREATE_ONLY",
            "currently_allowed": False,
            "unlock_in_this_phase": False,
            "note": "reserved"
        },
        "minimal_activation_conditions": [
            "phase6_1_release_policy_validation_result.status == PASS",
            "phase6_2_preflight_gate_validation_result.status == PASS",
            "phase6_3_release_decision_rules_validation_result.status == PASS",
            "phase5_overall_completion_status in [PASS_DRY_RUN_ONLY, PASS_DRY_RUN_ONLY_WITH_WARN]",
            "human_review_final_decision == APPROVE_DRAFT_CREATE_ONLY",
            "all_pre_execution_checklist_items == PASS",
            "single_draft_limit == 1",
            "post_status == draft",
            "wordpress_write_executed == false"
        ],
        "transition_conditions": {
            "from": "single_dry_run",
            "to": "single_real_draft",
            "enabled": False,
            "required_checks": [
                "latest_dry_run_result.status == PASS",
                "candidate_quality_check.status in [PASS, WARN_WITH_EXPLICIT_HUMAN_OVERRIDE]",
                "explicit_human_override_for_warn == true when quality is WARN",
                "wordpress_dedicated_user_permission_verified == true",
                "secrets_env_non_edit_verified == true",
                "existing_post_impact_zero_verified == true"
            ]
        },
        "pre_execution_checklist": {
            "required": True,
            "items": [
                "request_id_present",
                "reviewer_identity_verified",
                "review_decision_is_APPROVE_DRAFT_CREATE_ONLY",
                "decision_not_expired",
                "wordpress_role_in_allowed_roles",
                "application_password_active",
                "single_draft_limit_is_1",
                "target_post_status_is_draft",
                "existing_post_impact_zero",
                "secrets_env_not_edited",
                "forbidden_actions_not_requested"
            ]
        },
        "post_execution_evidence_spec": {
            "required_in_phase6_4": False,
            "future_required_fields": ["request_id", "draft_post_id"]
        },
        "failure_handling_policy": {
            "auto_retry_forbidden": True,
            "retry_on_failure": False,
            "manual_requeue_requires_new_review": True
        },
        "impact_guardrails": {
            "existing_post_impact_must_be_zero": True,
            "update_existing_post_forbidden": True,
            "delete_existing_post_forbidden": True,
            "bulk_operation_forbidden": True
        },
        "wordpress_permission_requirements": {
            "allowed_roles": ["editor", "administrator"],
            "dedicated_username_required": True,
            "application_password_required": True,
            "token_scope_limited": True
        },
        "secrets_env_policy": {
            "auto_edit_forbidden": True,
            "manual_rotation_only": True,
            "runtime_secret_write_forbidden": True
        },
        "rollback_policy": {
            "auto_rollback": False,
            "strategy": "manual_verify_and_manual_delete_only"
        },
        "phase6_5_entry_conditions": [
            "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
            "controlled_unlock_execution_spec_is_defined",
            "manual_operation_runbook_is_approved",
            "no_production_action_executed_in_phase6_4"
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


def test_valid_plan_pass():
    result = validate_plan(base_plan())
    assert result["status"] == "PASS"
    assert result["unlock_currently_allowed"] is False


def test_unlock_target_enabled_aborts():
    p = base_plan()
    p["unlock_target"]["currently_allowed"] = True
    result = validate_plan(p)
    assert result["status"] == "ABORT"


def test_transition_enabled_aborts():
    p = base_plan()
    p["transition_conditions"]["enabled"] = True
    result = validate_plan(p)
    assert result["status"] == "ABORT"


def test_missing_checklist_item_aborts():
    p = base_plan()
    p["pre_execution_checklist"]["items"].remove("secrets_env_not_edited")
    result = validate_plan(p)
    assert result["status"] == "ABORT"


def test_bad_rollback_strategy_aborts():
    p = base_plan()
    p["rollback_policy"]["strategy"] = "auto_rollback_if_failed"
    result = validate_plan(p)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "plan.json"
        out = base / "result.json"
        write_json(inp, base_plan())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
