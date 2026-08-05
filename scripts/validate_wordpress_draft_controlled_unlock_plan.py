#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_controlled_unlock_plan.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_4_controlled_unlock_plan_validation_result.json"

REQUIRED_FORBIDDEN = {
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
    "vps_self_builder_execution",
}

REQUIRED_MINIMAL_CONDITIONS = {
    "phase6_1_release_policy_validation_result.status == PASS",
    "phase6_2_preflight_gate_validation_result.status == PASS",
    "phase6_3_release_decision_rules_validation_result.status == PASS",
    "phase5_overall_completion_status in [PASS_DRY_RUN_ONLY, PASS_DRY_RUN_ONLY_WITH_WARN]",
    "human_review_final_decision == APPROVE_DRAFT_CREATE_ONLY",
    "all_pre_execution_checklist_items == PASS",
    "single_draft_limit == 1",
    "post_status == draft",
    "wordpress_write_executed == false",
}

REQUIRED_TRANSITION_CHECKS = {
    "latest_dry_run_result.status == PASS",
    "candidate_quality_check.status in [PASS, WARN_WITH_EXPLICIT_HUMAN_OVERRIDE]",
    "explicit_human_override_for_warn == true when quality is WARN",
    "wordpress_dedicated_user_permission_verified == true",
    "secrets_env_non_edit_verified == true",
    "existing_post_impact_zero_verified == true",
}

REQUIRED_CHECKLIST_ITEMS = {
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
    "forbidden_actions_not_requested",
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_4_controlled_unlock_plan_validation_result",
        "phase": "Phase 6-4",
        "status": "ABORT",
        "reason": reason,
        "plan_ready": False,
        "plan_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan(data: dict) -> dict:
    if data.get("phase") != "Phase 6-4":
        return _abort("phase must be Phase 6-4")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("plan_status") != "DESIGN_ONLY":
        return _abort("plan_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")

    unlock_target = data.get("unlock_target", {})
    if unlock_target.get("decision_token") != "APPROVE_DRAFT_CREATE_ONLY":
        return _abort("unlock_target.decision_token must be APPROVE_DRAFT_CREATE_ONLY")
    if unlock_target.get("currently_allowed") is not False:
        return _abort("unlock_target.currently_allowed must be false")
    if unlock_target.get("unlock_in_this_phase") is not False:
        return _abort("unlock_target.unlock_in_this_phase must be false")

    minimal = set(data.get("minimal_activation_conditions", []))
    if not REQUIRED_MINIMAL_CONDITIONS.issubset(minimal):
        return _abort("minimal_activation_conditions is missing required entries")

    transition = data.get("transition_conditions", {})
    if transition.get("from") != "single_dry_run":
        return _abort("transition_conditions.from must be single_dry_run")
    if transition.get("to") != "single_real_draft":
        return _abort("transition_conditions.to must be single_real_draft")
    if transition.get("enabled") is not False:
        return _abort("transition_conditions.enabled must be false in Phase 6-4")
    transition_checks = set(transition.get("required_checks", []))
    if not REQUIRED_TRANSITION_CHECKS.issubset(transition_checks):
        return _abort("transition_conditions.required_checks is missing required entries")

    checklist = data.get("pre_execution_checklist", {})
    if checklist.get("required") is not True:
        return _abort("pre_execution_checklist.required must be true")
    checklist_items = set(checklist.get("items", []))
    if not REQUIRED_CHECKLIST_ITEMS.issubset(checklist_items):
        return _abort("pre_execution_checklist.items is missing required entries")

    evidence = data.get("post_execution_evidence_spec", {})
    if evidence.get("required_in_phase6_4") is not False:
        return _abort("post_execution_evidence_spec.required_in_phase6_4 must be false")

    failure = data.get("failure_handling_policy", {})
    if failure.get("auto_retry_forbidden") is not True:
        return _abort("failure_handling_policy.auto_retry_forbidden must be true")
    if failure.get("retry_on_failure") is not False:
        return _abort("failure_handling_policy.retry_on_failure must be false")
    if failure.get("manual_requeue_requires_new_review") is not True:
        return _abort("failure_handling_policy.manual_requeue_requires_new_review must be true")

    guardrails = data.get("impact_guardrails", {})
    for key in [
        "existing_post_impact_must_be_zero",
        "update_existing_post_forbidden",
        "delete_existing_post_forbidden",
        "bulk_operation_forbidden",
    ]:
        if guardrails.get(key) is not True:
            return _abort(f"impact_guardrails.{key} must be true")

    permission = data.get("wordpress_permission_requirements", {})
    roles = set(permission.get("allowed_roles", []))
    if not {"editor", "administrator"}.issubset(roles):
        return _abort("wordpress_permission_requirements.allowed_roles must include editor and administrator")
    for key in ["dedicated_username_required", "application_password_required", "token_scope_limited"]:
        if permission.get(key) is not True:
            return _abort(f"wordpress_permission_requirements.{key} must be true")

    secrets_policy = data.get("secrets_env_policy", {})
    for key in ["auto_edit_forbidden", "manual_rotation_only", "runtime_secret_write_forbidden"]:
        if secrets_policy.get(key) is not True:
            return _abort(f"secrets_env_policy.{key} must be true")

    rollback = data.get("rollback_policy", {})
    if rollback.get("auto_rollback") is not False:
        return _abort("rollback_policy.auto_rollback must be false")
    if rollback.get("strategy") != "manual_verify_and_manual_delete_only":
        return _abort("rollback_policy.strategy must be manual_verify_and_manual_delete_only")

    phase6_5 = set(data.get("phase6_5_entry_conditions", []))
    required_phase6_5 = {
        "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
        "controlled_unlock_execution_spec_is_defined",
        "manual_operation_runbook_is_approved",
        "no_production_action_executed_in_phase6_4",
    }
    if not required_phase6_5.issubset(phase6_5):
        return _abort("phase6_5_entry_conditions is missing required entries")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_4_controlled_unlock_plan_validation_result",
        "phase": "Phase 6-4",
        "status": "PASS",
        "reason": "controlled unlock plan design is valid and keeps all production actions NO_GO",
        "plan_ready": True,
        "plan_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "unlock_currently_allowed": False,
        "next_step": "phase6_5_controlled_unlock_execution_spec_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"plan file not found: {input_path}")
    else:
        result = validate_plan(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
