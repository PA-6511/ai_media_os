#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_release_decision_rules.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_3_release_decision_rules_validation_result.json"

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

REQUIRED_HARD_STOPS = {
    "affiliate_tag_unverified == true",
    "content_url_missing == true",
    "pr_label_missing == true",
    "post_count_limit != 1",
    "post_status != draft",
    "wordpress_user_role_not_allowed == true",
    "human_review_missing == true",
    "human_review_decision_not_APPROVE_DRAFT_CREATE_ONLY == true",
    "secrets_or_env_auto_edit_detected == true",
    "wordpress_rest_execute_before_gate == true",
    "publish_request_detected == true",
    "update_request_detected == true",
    "delete_request_detected == true",
    "export_request_detected == true",
    "vps_self_builder_execution_enabled == true",
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_3_release_decision_rules_validation_result",
        "phase": "Phase 6-3",
        "status": "ABORT",
        "reason": reason,
        "rules_ready": False,
        "rules_status": "DESIGN_ONLY",
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


def validate_rules(data: dict) -> dict:
    if data.get("phase") != "Phase 6-3":
        return _abort("phase must be Phase 6-3")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("rules_status") != "DESIGN_ONLY":
        return _abort("rules_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")

    activation = data.get("activation_target", {})
    if activation.get("decision_token") != "APPROVE_DRAFT_CREATE_ONLY":
        return _abort("activation_target.decision_token must be APPROVE_DRAFT_CREATE_ONLY")
    if activation.get("currently_allowed") is not False:
        return _abort("activation_target.currently_allowed must be false")

    prerequisites = set(data.get("prerequisites_for_activation", []))
    required_prereq = {
        "phase5_overall_completion_status in [PASS_DRY_RUN_ONLY, PASS_DRY_RUN_ONLY_WITH_WARN]",
        "phase6_1_design_validation_result.status == PASS",
        "phase6_2_preflight_gate_validation_result.status == PASS",
        "human_review_final_decision == APPROVE_DRAFT_CREATE_ONLY",
        "post_count_limit == 1",
        "post_status == draft",
        "wordpress_write_executed == false",
    }
    if not required_prereq.issubset(prerequisites):
        return _abort("prerequisites_for_activation is missing required entries")

    warn_rules = data.get("warn_handling_rules", {})
    if warn_rules.get("phase5_warn_requires_explicit_human_override") is not True:
        return _abort("warn_handling_rules.phase5_warn_requires_explicit_human_override must be true")
    if warn_rules.get("phase5_warn_without_override_is_block") is not True:
        return _abort("warn_handling_rules.phase5_warn_without_override_is_block must be true")
    if warn_rules.get("quality_warn_requires_human_review") is not True:
        return _abort("warn_handling_rules.quality_warn_requires_human_review must be true")

    hard_stops = set(data.get("hard_stop_conditions", []))
    if not REQUIRED_HARD_STOPS.issubset(hard_stops):
        return _abort("hard_stop_conditions is missing required stop conditions")

    perm = data.get("wordpress_permission_requirements", {})
    roles = set(perm.get("allowed_roles", []))
    if not {"editor", "administrator"}.issubset(roles):
        return _abort("wordpress_permission_requirements.allowed_roles must include editor and administrator")
    for key in ["application_password_required", "token_scope_limited", "username_must_be_dedicated"]:
        if perm.get(key) is not True:
            return _abort(f"wordpress_permission_requirements.{key} must be true")

    final_review = data.get("final_human_review_requirements", {})
    if final_review.get("required") is not True:
        return _abort("final_human_review_requirements.required must be true")
    if final_review.get("decision_must_be") != "APPROVE_DRAFT_CREATE_ONLY":
        return _abort("final_human_review_requirements.decision_must_be must be APPROVE_DRAFT_CREATE_ONLY")
    if int(final_review.get("decision_expiry_minutes", 0)) <= 0:
        return _abort("final_human_review_requirements.decision_expiry_minutes must be > 0")
    if final_review.get("reviewer_identity_required") is not True:
        return _abort("final_human_review_requirements.reviewer_identity_required must be true")
    if final_review.get("review_timestamp_required") is not True:
        return _abort("final_human_review_requirements.review_timestamp_required must be true")

    evidence = data.get("post_execution_evidence_requirements", {})
    if evidence.get("required") is not False:
        return _abort("post_execution_evidence_requirements.required must be false in Phase 6-3")

    retry = data.get("retry_policy", {})
    if retry.get("retry_on_failure") is not False:
        return _abort("retry_policy.retry_on_failure must be false")
    if retry.get("auto_retry_forbidden") is not True:
        return _abort("retry_policy.auto_retry_forbidden must be true")
    if retry.get("manual_requeue_requires_new_review") is not True:
        return _abort("retry_policy.manual_requeue_requires_new_review must be true")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_3_release_decision_rules_validation_result",
        "phase": "Phase 6-3",
        "status": "PASS",
        "reason": "release decision rules design is valid and keeps NO_GO for real draft creation",
        "rules_ready": True,
        "rules_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_4_controlled_unlock_plan_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"rules file not found: {input_path}")
    else:
        result = validate_rules(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
