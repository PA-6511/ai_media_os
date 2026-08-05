#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_final_unlock_go_no_go.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_8_final_unlock_go_no_go_result.json"

REQUIRED_READINESS = {
    "phase6_1_release_policy_validation_result.status == PASS",
    "phase6_2_preflight_gate_validation_result.status == PASS",
    "phase6_3_release_decision_rules_validation_result.status == PASS",
    "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
    "phase6_5_execution_spec_validation_result.status == PASS",
    "phase6_6_pre_execution_rehearsal_validation_result.status == PASS",
    "phase6_7_unlock_readiness_decision_result.status == PASS",
    "phase6_7_readiness_result == READINESS_DESIGN_PASS",
}

REQUIRED_HARD_NO_GO = {
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
    "phase_gate_missing_or_failed == true",
}

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


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase6_8_final_unlock_go_no_go_result",
        "phase": "Phase 6-8",
        "status": "ABORT",
        "reason": reason,
        "final_unlock_ready": False,
        "final_unlock_status": "DESIGN_ONLY",
        "final_decision": "NO_GO_DESIGN_LOCK",
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


def validate_final_unlock(data: dict) -> dict:
    if data.get("phase") != "Phase 6-8":
        return _abort("phase must be Phase 6-8")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("final_unlock_status") != "DESIGN_ONLY":
        return _abort("final_unlock_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")
    if data.get("real_write_enabled") is not False:
        return _abort("real_write_enabled must be false")
    if data.get("wordpress_write_executed") is not False:
        return _abort("wordpress_write_executed must be false")
    if data.get("final_decision") != "NO_GO_DESIGN_LOCK":
        return _abort("final_decision must be NO_GO_DESIGN_LOCK in Phase 6-8")

    framework = data.get("decision_framework", {})
    allowed_values = set(framework.get("allowed_values", []))
    required_values = {
        "GO_READY_FOR_MANUAL_APPROVAL_ONLY",
        "CONDITIONAL_GO_REQUIREMENTS_PENDING",
        "NO_GO_DESIGN_LOCK",
    }
    if not required_values.issubset(allowed_values):
        return _abort("decision_framework.allowed_values is missing required entries")
    if framework.get("selected_value_in_phase6_8") != "NO_GO_DESIGN_LOCK":
        return _abort("decision_framework.selected_value_in_phase6_8 must be NO_GO_DESIGN_LOCK")
    if framework.get("decision_locked_in_this_phase") is not True:
        return _abort("decision_framework.decision_locked_in_this_phase must be true")

    readiness = set(data.get("readiness_requirements", []))
    if not REQUIRED_READINESS.issubset(readiness):
        return _abort("readiness_requirements is missing required entries")

    warns = data.get("warn_clearance_requirements", {})
    for key in [
        "phase5_warn_reviewed",
        "content_url_missing_warn_addressed_or_explicitly_overridden",
        "affiliate_tag_warn_addressed_or_explicitly_overridden",
        "explicit_human_override_record_required",
    ]:
        if warns.get(key) is not True:
            return _abort(f"warn_clearance_requirements.{key} must be true")

    locks = data.get("mandatory_no_go_locks", {})
    for key in [
        "real_write_must_remain_disabled",
        "wordpress_rest_post_forbidden",
        "wordpress_rest_put_patch_forbidden",
        "publish_forbidden",
        "update_existing_post_forbidden",
        "delete_post_forbidden",
        "external_export_forbidden",
        "github_actions_trigger_forbidden",
        "slack_production_notification_forbidden",
        "vps_self_builder_execution_forbidden",
        "env_secret_credential_auto_edit_forbidden",
    ]:
        if locks.get(key) is not True:
            return _abort(f"mandatory_no_go_locks.{key} must be true")

    logic = data.get("final_go_no_go_logic", {})
    if logic.get("all_readiness_requirements_pass_and_warns_handled") != "GO_READY_FOR_MANUAL_APPROVAL_ONLY":
        return _abort("final_go_no_go_logic for all readiness pass is invalid")
    if logic.get("readiness_pass_but_warn_or_evidence_pending") != "CONDITIONAL_GO_REQUIREMENTS_PENDING":
        return _abort("final_go_no_go_logic for conditional is invalid")
    if logic.get("any_write_or_forbidden_action_detected") != "NO_GO_DESIGN_LOCK":
        return _abort("final_go_no_go_logic for write/forbidden detected is invalid")
    if logic.get("phase6_8_default") != "NO_GO_DESIGN_LOCK":
        return _abort("final_go_no_go_logic.phase6_8_default must be NO_GO_DESIGN_LOCK")

    hard = set(data.get("hard_no_go_conditions", []))
    if not REQUIRED_HARD_NO_GO.issubset(hard):
        return _abort("hard_no_go_conditions is missing required entries")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_8_final_unlock_go_no_go_result",
        "phase": "Phase 6-8",
        "status": "PASS",
        "reason": "final unlock GO/NO-GO design is valid and remains NO_GO in this phase",
        "final_unlock_ready": True,
        "final_unlock_status": "DESIGN_ONLY",
        "final_decision": "NO_GO_DESIGN_LOCK",
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
        "next_step": "phase6_9_manual_unlock_protocol_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"final unlock design file not found: {input_path}")
    else:
        result = validate_final_unlock(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
