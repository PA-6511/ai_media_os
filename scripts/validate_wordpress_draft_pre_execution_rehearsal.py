#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_pre_execution_rehearsal.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_6_pre_execution_rehearsal_validation_result.json"

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

REQUIRED_INPUTS = {
    "request_id",
    "candidate_id",
    "title",
    "body_markdown",
    "content_url",
    "pr_disclosure",
    "affiliate_check_result",
    "human_review_decision",
    "reviewer_id",
    "reviewed_at",
}

REQUIRED_PRECONDITIONS = {
    "phase6_1_release_policy_validation_result.status == PASS",
    "phase6_2_preflight_gate_validation_result.status == PASS",
    "phase6_3_release_decision_rules_validation_result.status == PASS",
    "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
    "phase6_5_execution_spec_validation_result.status == PASS",
    "execution_enabled == false",
    "wordpress_write_executed == false",
}

REQUIRED_SEQUENCE_NAMES = [
    "load_inputs_and_schema_check",
    "phase_gate_and_policy_check",
    "human_review_and_expiry_check",
    "wordpress_permission_and_scope_check",
    "payload_simulation_without_send",
    "evidence_dry_record_and_signoff",
]

REQUIRED_EVIDENCE_FIELDS = {
    "request_id",
    "candidate_id",
    "reviewer_id",
    "decision_token",
    "simulated_payload_hash",
    "simulated_at",
    "result_status",
    "write_api_called",
}

REQUIRED_STOP_CONDITIONS = {
    "missing_required_input == true",
    "precondition_not_met == true",
    "human_review_missing_or_expired == true",
    "affiliate_check_unresolved_warn == true",
    "content_url_missing == true",
    "pr_disclosure_missing == true",
    "wordpress_role_not_allowed == true",
    "wordpress_rest_post_attempted == true",
    "wordpress_rest_put_patch_attempted == true",
    "publish_attempted == true",
    "update_existing_post_attempted == true",
    "delete_post_attempted == true",
    "cron_change_attempted == true",
    "github_actions_trigger_attempted == true",
    "slack_production_notification_attempted == true",
    "vps_self_builder_execution_attempted == true",
    "env_secret_credential_auto_edit_attempted == true",
}


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_6_pre_execution_rehearsal_validation_result",
        "phase": "Phase 6-6",
        "status": "ABORT",
        "reason": reason,
        "rehearsal_ready": False,
        "rehearsal_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "rehearsal_enabled": True,
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


def validate_rehearsal(data: dict) -> dict:
    if data.get("phase") != "Phase 6-6":
        return _abort("phase must be Phase 6-6")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("rehearsal_status") != "DESIGN_ONLY":
        return _abort("rehearsal_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")
    if data.get("rehearsal_enabled") is not True:
        return _abort("rehearsal_enabled must be true")
    if data.get("real_write_enabled") is not False:
        return _abort("real_write_enabled must be false")

    scope = data.get("rehearsal_scope", {})
    if scope.get("target_operation") != "single_wordpress_draft_creation_rehearsal":
        return _abort("rehearsal_scope.target_operation must be single_wordpress_draft_creation_rehearsal")
    if int(scope.get("max_posts_per_run", 0)) != 1:
        return _abort("rehearsal_scope.max_posts_per_run must be 1")
    if scope.get("target_post_status") != "draft":
        return _abort("rehearsal_scope.target_post_status must be draft")
    if scope.get("simulate_only") is not True:
        return _abort("rehearsal_scope.simulate_only must be true")
    if scope.get("wordpress_rest_call_must_be_skipped") is not True:
        return _abort("rehearsal_scope.wordpress_rest_call_must_be_skipped must be true")

    required_inputs = set(data.get("required_inputs", []))
    if not REQUIRED_INPUTS.issubset(required_inputs):
        return _abort("required_inputs is missing required entries")

    preconditions = set(data.get("preconditions", []))
    if not REQUIRED_PRECONDITIONS.issubset(preconditions):
        return _abort("preconditions is missing required entries")

    sequence = data.get("rehearsal_sequence", [])
    if len(sequence) != 6:
        return _abort("rehearsal_sequence must contain exactly 6 steps")
    for idx, item in enumerate(sequence, start=1):
        if int(item.get("step", 0)) != idx:
            return _abort("rehearsal_sequence steps must be contiguous from 1 to 6")
        if item.get("stop_on_failure") is not True:
            return _abort("each rehearsal_sequence step must have stop_on_failure true")
    names = [item.get("name") for item in sequence]
    if names != REQUIRED_SEQUENCE_NAMES:
        return _abort("rehearsal_sequence names/order is invalid")

    evidence = data.get("evidence_requirements", {})
    if evidence.get("required_in_phase6_6") is not True:
        return _abort("evidence_requirements.required_in_phase6_6 must be true")
    if evidence.get("store_as_simulation_only") is not True:
        return _abort("evidence_requirements.store_as_simulation_only must be true")
    evidence_fields = set(evidence.get("required_fields", []))
    if not REQUIRED_EVIDENCE_FIELDS.issubset(evidence_fields):
        return _abort("evidence_requirements.required_fields is missing required entries")

    stop_conditions = set(data.get("stop_conditions", []))
    if not REQUIRED_STOP_CONDITIONS.issubset(stop_conditions):
        return _abort("stop_conditions is missing required entries")

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
        "package_type": "phase6_6_pre_execution_rehearsal_validation_result",
        "phase": "Phase 6-6",
        "status": "PASS",
        "reason": "pre-execution rehearsal design is valid and keeps real write actions disabled",
        "rehearsal_ready": True,
        "rehearsal_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "rehearsal_enabled": True,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_7_unlock_readiness_decision_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"rehearsal file not found: {input_path}")
    else:
        result = validate_rehearsal(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
