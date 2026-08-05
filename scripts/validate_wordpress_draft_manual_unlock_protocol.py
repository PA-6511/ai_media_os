#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_manual_unlock_protocol.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_9_manual_unlock_protocol_validation_result.json"

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

REQUIRED_CHECKLIST = {
    "phase6_1_through_6_8_all_PASS_confirmed",
    "readiness_result_is_READINESS_DESIGN_PASS",
    "final_go_no_go_reviewed_by_human",
    "warn_items_resolved_or_explicitly_overridden",
    "affiliate_tag_status_confirmed",
    "content_url_confirmed",
    "pr_disclosure_confirmed",
    "wordpress_user_role_confirmed",
    "application_password_active_confirmed",
    "no_forbidden_action_in_request",
    "secrets_env_non_edit_confirmed",
    "existing_post_impact_zero_confirmed",
}

REQUIRED_HARD_BLOCKS = {
    "human_review_missing == true",
    "human_review_expired == true",
    "review_decision_not_APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY == true",
    "checklist_item_not_confirmed == true",
    "warn_unresolved_without_override == true",
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
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_9_manual_unlock_protocol_validation_result",
        "phase": "Phase 6-9",
        "status": "ABORT",
        "reason": reason,
        "protocol_ready": False,
        "manual_unlock_status": "DESIGN_ONLY",
        "unlock_currently_allowed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_protocol(data: dict) -> dict:
    if data.get("phase") != "Phase 6-9":
        return _abort("phase must be Phase 6-9")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("manual_unlock_status") != "DESIGN_ONLY":
        return _abort("manual_unlock_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")
    if data.get("unlock_currently_allowed") is not False:
        return _abort("unlock_currently_allowed must be false")
    if data.get("real_write_enabled") is not False:
        return _abort("real_write_enabled must be false")
    if data.get("wordpress_write_executed") is not False:
        return _abort("wordpress_write_executed must be false")

    scope = data.get("unlock_scope", {})
    if scope.get("target") != "single_wordpress_draft_only":
        return _abort("unlock_scope.target must be single_wordpress_draft_only")
    if int(scope.get("max_posts_on_first_unlock", 0)) != 1:
        return _abort("unlock_scope.max_posts_on_first_unlock must be 1")
    if scope.get("target_post_status") != "draft":
        return _abort("unlock_scope.target_post_status must be draft")
    for key in ["publish_forbidden_on_unlock", "update_existing_post_forbidden_on_unlock", "delete_post_forbidden_on_unlock"]:
        if scope.get(key) is not True:
            return _abort(f"unlock_scope.{key} must be true")

    reviewer = data.get("reviewer_requirements", {})
    if reviewer.get("human_reviewer_required") is not True:
        return _abort("reviewer_requirements.human_reviewer_required must be true")
    if reviewer.get("reviewer_identity_must_be_recorded") is not True:
        return _abort("reviewer_requirements.reviewer_identity_must_be_recorded must be true")
    if reviewer.get("reviewer_cannot_be_automated_agent") is not True:
        return _abort("reviewer_requirements.reviewer_cannot_be_automated_agent must be true")
    if reviewer.get("review_decision_token") != "APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY":
        return _abort("reviewer_requirements.review_decision_token must be APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY")
    if int(reviewer.get("review_expiry_minutes", 0)) <= 0:
        return _abort("reviewer_requirements.review_expiry_minutes must be > 0")
    if reviewer.get("review_timestamp_required") is not True:
        return _abort("reviewer_requirements.review_timestamp_required must be true")

    checklist = set(data.get("evidence_checklist_before_unlock", []))
    if not REQUIRED_CHECKLIST.issubset(checklist):
        return _abort("evidence_checklist_before_unlock is missing required entries")

    mapping = data.get("unlock_decision_mapping", {})
    if mapping.get("all_checklist_items_confirmed_and_human_approved") != "UNLOCK_GRANTED_DRAFT_ONLY":
        return _abort("unlock_decision_mapping: all confirmed must map to UNLOCK_GRANTED_DRAFT_ONLY")
    if mapping.get("checklist_incomplete_or_warn_unresolved") != "UNLOCK_BLOCKED_PENDING_REVIEW":
        return _abort("unlock_decision_mapping: incomplete must map to UNLOCK_BLOCKED_PENDING_REVIEW")
    for key in ["forbidden_action_detected", "write_or_publish_detected"]:
        if mapping.get(key) != "UNLOCK_HARD_BLOCKED":
            return _abort(f"unlock_decision_mapping.{key} must map to UNLOCK_HARD_BLOCKED")
    if mapping.get("phase6_9_default") != "UNLOCK_BLOCKED_DESIGN_ONLY":
        return _abort("unlock_decision_mapping.phase6_9_default must be UNLOCK_BLOCKED_DESIGN_ONLY")

    hard_blocks = set(data.get("unlock_hard_block_conditions", []))
    if not REQUIRED_HARD_BLOCKS.issubset(hard_blocks):
        return _abort("unlock_hard_block_conditions is missing required entries")

    evidence = data.get("post_unlock_evidence_spec", {})
    if evidence.get("required_on_actual_unlock") is not True:
        return _abort("post_unlock_evidence_spec.required_on_actual_unlock must be true")
    if evidence.get("required_in_phase6_9") is not False:
        return _abort("post_unlock_evidence_spec.required_in_phase6_9 must be false")

    re_lock = data.get("re_lock_policy", {})
    if re_lock.get("auto_re_lock_after_single_use") is not True:
        return _abort("re_lock_policy.auto_re_lock_after_single_use must be true")
    if re_lock.get("re_unlock_requires_new_full_review") is not True:
        return _abort("re_lock_policy.re_unlock_requires_new_full_review must be true")
    if re_lock.get("bulk_unlock_forbidden") is not True:
        return _abort("re_lock_policy.bulk_unlock_forbidden must be true")

    retry = data.get("retry_policy", {})
    if retry.get("auto_retry_forbidden") is not True:
        return _abort("retry_policy.auto_retry_forbidden must be true")
    if retry.get("retry_on_failure") is not False:
        return _abort("retry_policy.retry_on_failure must be false")
    if retry.get("manual_rerun_requires_new_review") is not True:
        return _abort("retry_policy.manual_rerun_requires_new_review must be true")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_9_manual_unlock_protocol_validation_result",
        "phase": "Phase 6-9",
        "status": "PASS",
        "reason": "manual unlock protocol design is valid and keeps unlock_currently_allowed false",
        "protocol_ready": True,
        "manual_unlock_status": "DESIGN_ONLY",
        "unlock_currently_allowed": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_10_phase6_completion_report_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"protocol file not found: {input_path}")
    else:
        result = validate_protocol(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
