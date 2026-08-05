#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_creation_execution_spec.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_5_execution_spec_validation_result.json"

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

REQUIRED_INPUT_FIELDS = {
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

REQUIRED_GATE_CHECKS = {
    "phase6_1_release_policy_validation_result.status == PASS",
    "phase6_2_preflight_gate_validation_result.status == PASS",
    "phase6_3_release_decision_rules_validation_result.status == PASS",
    "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
    "unlock_currently_allowed == false in phase6_5",
    "wordpress_write_executed == false",
}

REQUIRED_STOP_CONDITIONS = {
    "input_validation_failed == true",
    "required_phase_gate_missing == true",
    "human_review_missing_or_expired == true",
    "wordpress_role_not_allowed == true",
    "secrets_env_auto_edit_detected == true",
    "publish_request_detected == true",
    "update_request_detected == true",
    "delete_request_detected == true",
    "wordpress_rest_post_requested == true",
    "wordpress_rest_put_patch_requested == true",
    "cron_change_requested == true",
    "github_actions_trigger_requested == true",
    "slack_production_notification_requested == true",
    "vps_self_builder_execution_enabled == true",
}

REQUIRED_SEQUENCE_NAMES = [
    "load_and_validate_inputs",
    "validate_phase_gates",
    "validate_human_review_freshness",
    "validate_wordpress_permission",
    "dry_run_payload_build_only",
    "record_planned_evidence_schema",
]


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_5_execution_spec_validation_result",
        "phase": "Phase 6-5",
        "status": "ABORT",
        "reason": reason,
        "spec_ready": False,
        "spec_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "execution_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_spec(data: dict) -> dict:
    if data.get("phase") != "Phase 6-5":
        return _abort("phase must be Phase 6-5")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("spec_status") != "DESIGN_ONLY":
        return _abort("spec_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")
    if data.get("execution_enabled") is not False:
        return _abort("execution_enabled must be false")

    target = data.get("target_scope", {})
    if target.get("operation") != "create_single_wordpress_draft":
        return _abort("target_scope.operation must be create_single_wordpress_draft")
    if int(target.get("max_posts_per_run", 0)) != 1:
        return _abort("target_scope.max_posts_per_run must be 1")
    if target.get("target_post_status") != "draft":
        return _abort("target_scope.target_post_status must be draft")
    if target.get("existing_post_impact_must_be_zero") is not True:
        return _abort("target_scope.existing_post_impact_must_be_zero must be true")

    contract = data.get("input_contract", {})
    required_fields = set(contract.get("required_fields", []))
    if not REQUIRED_INPUT_FIELDS.issubset(required_fields):
        return _abort("input_contract.required_fields is missing required entries")

    sequence = data.get("execution_sequence", [])
    if len(sequence) != 6:
        return _abort("execution_sequence must contain exactly 6 steps")
    for idx, item in enumerate(sequence, start=1):
        if int(item.get("step", 0)) != idx:
            return _abort("execution_sequence steps must be contiguous from 1 to 6")
        if item.get("stop_on_failure") is not True:
            return _abort("each execution_sequence step must have stop_on_failure true")
    names = [item.get("name") for item in sequence]
    if names != REQUIRED_SEQUENCE_NAMES:
        return _abort("execution_sequence names/order is invalid")

    gates = data.get("gates_before_any_write", {})
    if gates.get("required") is not True:
        return _abort("gates_before_any_write.required must be true")
    gate_checks = set(gates.get("checks", []))
    if not REQUIRED_GATE_CHECKS.issubset(gate_checks):
        return _abort("gates_before_any_write.checks is missing required entries")

    evidence = data.get("evidence_spec", {})
    if evidence.get("required_in_phase6_5") is not False:
        return _abort("evidence_spec.required_in_phase6_5 must be false")

    stop_conditions = set(data.get("immediate_stop_conditions", []))
    if not REQUIRED_STOP_CONDITIONS.issubset(stop_conditions):
        return _abort("immediate_stop_conditions is missing required entries")

    retry = data.get("retry_policy", {})
    if retry.get("retry_on_failure") is not False:
        return _abort("retry_policy.retry_on_failure must be false")
    if retry.get("auto_retry_forbidden") is not True:
        return _abort("retry_policy.auto_retry_forbidden must be true")
    if retry.get("manual_requeue_requires_new_review") is not True:
        return _abort("retry_policy.manual_requeue_requires_new_review must be true")

    restrictions = data.get("runtime_restrictions", {})
    required_restriction_keys = [
        "wordpress_rest_post_forbidden",
        "wordpress_rest_put_patch_forbidden",
        "publish_forbidden",
        "update_existing_post_forbidden",
        "delete_post_forbidden",
        "cron_change_forbidden",
        "github_actions_trigger_forbidden",
        "slack_production_notification_forbidden",
        "vps_self_builder_execution_forbidden",
        "env_secret_credential_auto_edit_forbidden",
    ]
    for key in required_restriction_keys:
        if restrictions.get(key) is not True:
            return _abort(f"runtime_restrictions.{key} must be true")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_5_execution_spec_validation_result",
        "phase": "Phase 6-5",
        "status": "PASS",
        "reason": "execution spec design is valid and keeps all write actions NO_GO",
        "spec_ready": True,
        "spec_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "execution_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "phase6_6_pre_execution_rehearsal_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"execution spec file not found: {input_path}")
    else:
        result = validate_spec(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
