#!/usr/bin/env python3
import json
import sys
from pathlib import Path

POLICY_PATH = Path("config/pr_warn_backfill_valid_until_reaction_handler_policy.json")

REQUIRED_STATES = {
    "VALID",
    "SOFT_EXPIRING",
    "REACTION_PENDING",
    "REACTION_BUSY",
    "HARD_EXPIRED",
    "REVALIDATING",
    "RESNAPSHOT_READY",
    "REVALIDATION_ABORT",
}

REQUIRED_PROHIBITED = {
    "WORDPRESS_POST",
    "WORDPRESS_PUT",
    "WORDPRESS_PATCH",
    "WORDPRESS_DELETE",
    "WORDPRESS_WRITE",
    "PUBLISH",
    "STATUS_CHANGE",
    "APPROVED_TRUE",
    "WORDPRESS_LIVE_WRITE_ALLOWED_TRUE",
    "CREATED_FOR_EXECUTION_TRUE",
    "FINAL_APPROVAL_TRUE_CREATION",
    "LIVE_EXECUTION",
    "DISPLAY_SNAPSHOT_BODY",
    "DISPLAY_PAYLOAD_BODY",
    "DISPLAY_SECRETS",
    "COMMIT",
    "PUSH",
}

def load_policy(path: Path = POLICY_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def validate(policy: dict) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(policy.get("policy_name") == "PR_WARN_BACKFILL_VALID_UNTIL_REACTION_HANDLER_POLICY", "invalid policy_name")
    require(policy.get("phase") == "PR_WARN_BACKFILL_PHASE1Y_VALID_UNTIL_REACTION_HANDLER_POLICY", "invalid phase")
    require(policy.get("mode") == "DESIGN_ONLY_NO_EXECUTION", "mode must be DESIGN_ONLY_NO_EXECUTION")
    require(policy.get("target_post_id") == 101, "target_post_id must be 101")

    require(policy.get("soft_expiry_threshold_minutes") == 10, "soft expiry threshold must be 10")
    require(policy.get("reaction_timeout_minutes") == 2, "reaction timeout must be 2")
    require(policy.get("busy_fallback_enabled") is True, "busy fallback must be enabled")
    require(policy.get("busy_fallback_action") == "READ_ONLY_REVALIDATION", "busy fallback action must be READ_ONLY_REVALIDATION")

    require(policy.get("auto_resnapshot_allowed") is True, "auto resnapshot must be allowed")
    require(policy.get("auto_active_approval_refresh_allowed") is True, "auto active approval refresh must be allowed")
    require(policy.get("wordpress_get_allowed_only_during_revalidation") is True, "GET only during revalidation must be true")
    require(policy.get("wordpress_post_put_patch_delete_allowed") is False, "POST/PUT/PATCH/DELETE must be false")
    require(policy.get("wordpress_write_allowed") is False, "wordpress write must be false")
    require(policy.get("approved_true_allowed") is False, "approved true must be false")
    require(policy.get("live_execution_allowed") is False, "live execution must be false")
    require(policy.get("human_approval_required_for_approved_true") is True, "human approval required for approved true")
    require(policy.get("human_approval_required_for_live_write") is True, "human approval required for live write")

    constraints = policy.get("auto_active_approval_refresh_constraints", {})
    require(constraints.get("approved_must_remain_false") is True, "approved must remain false")
    require(constraints.get("wordpress_live_write_allowed_must_remain_false") is True, "wordpress live write must remain false")
    require(constraints.get("created_for_execution_must_remain_false") is True, "created_for_execution must remain false")
    require(constraints.get("allowed_changed_fields_must_equal") == ["content"], "allowed fields must be content only")
    require(constraints.get("max_live_updates_must_equal") == 1, "max live updates must be 1")
    require(constraints.get("wordpress_write_allowed") is False, "constraint wordpress write must be false")
    require(constraints.get("live_execution_allowed") is False, "constraint live execution must be false")

    states = set(policy.get("reaction_states", []))
    require(REQUIRED_STATES.issubset(states), "missing required reaction states")

    prohibited = set(policy.get("prohibited_actions", []))
    require(REQUIRED_PROHIBITED.issubset(prohibited), "missing required prohibited actions")

    checks = policy.get("revalidation_checks", {})
    require(checks.get("fetched_post_id_equals_target_post_id") is True, "must check post_id")
    require(checks.get("status_from_wp_must_be") == "draft", "status must be draft")
    require(checks.get("modified_must_match_rollback_snapshot") is True, "must check modified")
    require(checks.get("content_hash_must_match_rollback_snapshot") is True, "must check content hash")
    require(checks.get("payload_changed_fields_must_equal") == ["content"], "payload must be content only")
    require(checks.get("active_approval_approved_must_be_false") is True, "active approval approved must be false")
    require(checks.get("active_approval_wordpress_live_write_allowed_must_be_false") is True, "active approval live write must be false")
    require(checks.get("active_approval_created_for_execution_must_be_false") is True, "active approval created_for_execution must be false")

    implementation = policy.get("implementation_status", {})
    require(implementation.get("reaction_monitor_created") is False, "reaction monitor must not be created in design-only phase")
    require(implementation.get("notification_sender_created") is False, "notification sender must not be created in design-only phase")
    require(implementation.get("auto_revalidation_runner_created") is False, "auto revalidation runner must not be created in design-only phase")
    require(implementation.get("wordpress_api_called_in_this_phase") is False, "wordpress api must not be called in this phase")
    require(implementation.get("wordpress_write_executed") is False, "wordpress write must not execute")
    require(implementation.get("live_execution_executed") is False, "live execution must not execute")
    require(implementation.get("approved_true_created") is False, "approved true must not be created")

    require(policy.get("next_phase_after_policy") == "Phase 1S-FINAL-APPROVAL-TRUE-PREP-RERUN3", "unexpected next phase")
    require(policy.get("if_current_valid_until_expired") == "Phase 1N-RERUN", "expired route must return to Phase 1N-RERUN")

    return errors

def main() -> int:
    policy = load_policy()
    errors = validate(policy)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("PASS: valid_until reaction handler policy is valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
