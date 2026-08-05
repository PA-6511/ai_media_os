#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/wordpress_draft_unlock_readiness_decision.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase6_7_unlock_readiness_decision_result.json"

REQUIRED_PHASE_CHECKS = {
    "phase6_1_release_policy_validation_result.status == PASS",
    "phase6_2_preflight_gate_validation_result.status == PASS",
    "phase6_3_release_decision_rules_validation_result.status == PASS",
    "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
    "phase6_5_execution_spec_validation_result.status == PASS",
    "phase6_6_pre_execution_rehearsal_validation_result.status == PASS",
}

REQUIRED_HARD_BLOCKS = {
    "phase_check_missing_or_failed == true",
    "warn_handling_not_confirmed == true",
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
        "package_type": "phase6_7_unlock_readiness_decision_result",
        "phase": "Phase 6-7",
        "status": "ABORT",
        "reason": reason,
        "readiness_ready": False,
        "decision_status": "DESIGN_ONLY",
        "readiness_result": "READINESS_DESIGN_BLOCK",
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


def validate_decision(data: dict) -> dict:
    if data.get("phase") != "Phase 6-7":
        return _abort("phase must be Phase 6-7")
    if data.get("mode") != "CONNECTION_TEST":
        return _abort("mode must be CONNECTION_TEST")
    if data.get("execution") != "DRY_RUN":
        return _abort("execution must be DRY_RUN")
    if data.get("decision_status") != "DESIGN_ONLY":
        return _abort("decision_status must be DESIGN_ONLY")
    if data.get("production_status") != "NO_GO":
        return _abort("production_status must be NO_GO")
    if data.get("wordpress_draft_creation") != "NO_GO":
        return _abort("wordpress_draft_creation must be NO_GO")
    if data.get("real_write_enabled") is not False:
        return _abort("real_write_enabled must be false")
    if data.get("readiness_result") != "READINESS_DESIGN_PASS":
        return _abort("readiness_result must be READINESS_DESIGN_PASS in design phase")

    phase_checks = set(data.get("required_phase_checks", []))
    if not REQUIRED_PHASE_CHECKS.issubset(phase_checks):
        return _abort("required_phase_checks is missing required entries")

    warn_rules = data.get("warn_review_requirements", {})
    if warn_rules.get("phase5_warn_handling_confirmed") is not True:
        return _abort("warn_review_requirements.phase5_warn_handling_confirmed must be true")
    if warn_rules.get("affiliate_tag_warn_handling_confirmed") is not True:
        return _abort("warn_review_requirements.affiliate_tag_warn_handling_confirmed must be true")
    if warn_rules.get("content_url_missing_warn_handling_confirmed") is not True:
        return _abort("warn_review_requirements.content_url_missing_warn_handling_confirmed must be true")
    if warn_rules.get("explicit_human_override_required_for_warn") is not True:
        return _abort("warn_review_requirements.explicit_human_override_required_for_warn must be true")

    logic = data.get("readiness_logic", {})
    required_logic_flags = [
        "all_phase_checks_must_pass",
        "warn_handling_must_be_documented",
        "real_write_must_remain_disabled",
        "wordpress_write_executed_must_be_false",
    ]
    for key in required_logic_flags:
        if logic.get(key) is not True:
            return _abort(f"readiness_logic.{key} must be true")
    if logic.get("result_when_all_conditions_met") != "READINESS_DESIGN_PASS":
        return _abort("readiness_logic.result_when_all_conditions_met must be READINESS_DESIGN_PASS")
    if logic.get("result_when_any_condition_missing") != "READINESS_DESIGN_BLOCK":
        return _abort("readiness_logic.result_when_any_condition_missing must be READINESS_DESIGN_BLOCK")

    hard_blocks = set(data.get("hard_block_conditions", []))
    if not REQUIRED_HARD_BLOCKS.issubset(hard_blocks):
        return _abort("hard_block_conditions is missing required entries")

    forbidden = set(data.get("forbidden_actions", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        return _abort("forbidden_actions is missing required entries")

    return {
        "package_type": "phase6_7_unlock_readiness_decision_result",
        "phase": "Phase 6-7",
        "status": "PASS",
        "reason": "unlock readiness decision design is valid while keeping all real write actions disabled",
        "readiness_ready": True,
        "decision_status": "DESIGN_ONLY",
        "readiness_result": "READINESS_DESIGN_PASS",
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
        "next_step": "phase6_8_final_unlock_go_no_go_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_validation(input_path: Path | None = None, output_path: Path | None = None) -> dict:
    input_path = Path(input_path or DEFAULT_INPUT)
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = _abort(f"readiness decision file not found: {input_path}")
    else:
        result = validate_decision(load_json(input_path))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
