#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/phase7_5f_manual_go_redecision.json"
FALLBACK_INPUT = ROOT / "exchange/human_review/phase7_5f_manual_go_redecision.example.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase7_5f_manual_go_redecision_result.json"

VALID_DECISIONS = {
    "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME",
    "KEEP_FREEZE",
    "REQUEST_FIX",
    "ABORT",
}

VALID_GO_TOKEN = "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"

CONFIRMATION_KEYS = [
    "payload_title_and_content_reviewed",
    "content_url_validity_confirmed",
    "affiliate_tag_confirmed",
    "pr_disclosure_confirmed",
    "wordpress_editor_role_confirmed",
    "status_draft_only_confirmed",
    "manual_delete_procedure_confirmed",
    "approval_token_expiry_confirmed",
]

FORBIDDEN_TRUE_FLAGS = [
    "wordpress_post_enabled",
    "real_write_enabled",
    "wordpress_write_executed",
    "auto_post",
    "auto_update",
    "auto_delete",
    "auto_export",
    "github_actions_triggered",
    "slack_notification_executed",
    "vps_self_builder_executed",
    "env_or_secrets_modified",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def abort_result(reason: str) -> dict:
    return {
        "package_type": "phase7_5f_manual_go_redecision_result",
        "phase": "Phase 7-5F",
        "status": "ABORT",
        "decision": "ABORT",
        "reason": reason,
        "manual_decision_recorded": False,
        "phase7_5c_execution_unlocked_for_operator": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "abort",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def validate_common(data: dict):
    if data.get("mode") != "CONNECTION_TEST":
        return abort_result("mode must be CONNECTION_TEST")

    if data.get("execution") != "DRY_RUN":
        return abort_result("execution must be DRY_RUN")

    if data.get("reviewer_is_human") is not True:
        return abort_result("reviewer_is_human must be true")

    reviewer = str(data.get("reviewer", "")).strip()
    if not reviewer or reviewer.lower().startswith(("ai_", "bot_", "agent_")):
        return abort_result("reviewer must be a human operator identifier")

    decision = data.get("decision")
    if decision not in VALID_DECISIONS:
        return abort_result(f"unknown decision: {decision}")

    safety_flags = data.get("safety_flags", {})
    if not isinstance(safety_flags, dict):
        return abort_result("safety_flags must be an object")

    for flag in FORBIDDEN_TRUE_FLAGS:
        if safety_flags.get(flag) is True or data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in Phase 7-5F")

    return None


def validate_token_constraints(data: dict):
    constraints = data.get("token_constraints", {})
    if constraints.get("one_time_only") is not True:
        return abort_result("one_time_only must be true")
    if constraints.get("expires_minutes") != 30:
        return abort_result("expires_minutes must be 30")
    if constraints.get("post_status") != "draft":
        return abort_result("post_status must be draft")
    if constraints.get("post_count_limit") != 1:
        return abort_result("post_count_limit must be 1")

    for key in ["publish_allowed", "update_allowed", "delete_allowed", "export_allowed"]:
        if constraints.get(key) is not False:
            return abort_result(f"{key} must be false")

    return None


def all_confirmations_true(data: dict) -> bool:
    confirmations = data.get("manual_confirmation", {})
    return all(confirmations.get(key) is True for key in CONFIRMATION_KEYS)


def read_manual_go_redecision(input_path=None, output_path=None) -> dict:
    input_path = (
        Path(input_path)
        if input_path
        else (DEFAULT_INPUT if DEFAULT_INPUT.exists() else FALLBACK_INPUT)
    )
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not input_path.exists():
        result = abort_result(f"manual go redecision file not found: {input_path}")
    else:
        data = load_json(input_path)

        common_error = validate_common(data)
        token_error = validate_token_constraints(data)
        if common_error:
            result = common_error
        elif token_error:
            result = token_error
        else:
            decision = data.get("decision")
            all_confirmed = all_confirmations_true(data)

            base = {
                "package_type": "phase7_5f_manual_go_redecision_result",
                "phase": "Phase 7-5F",
                "mode": "CONNECTION_TEST",
                "execution": "DRY_RUN",
                "decision": decision,
                "reviewer_is_human": True,
                "all_manual_confirmation_passed": all_confirmed,
                "manual_decision_recorded": True,
                "token_constraints_valid": True,
                "production_status": "NO_GO",
                "wordpress_post_enabled": False,
                "real_write_enabled": False,
                "wordpress_write_executed": False,
                "auto_post": False,
                "auto_update": False,
                "auto_delete": False,
                "auto_export": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            if decision == "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME":
                if data.get("approval_token") != VALID_GO_TOKEN:
                    result = abort_result(
                        "approval_token must be MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
                    )
                elif not all_confirmed:
                    result = abort_result(
                        "all manual confirmation items must be true for MANUAL_GO"
                    )
                else:
                    result = {
                        **base,
                        "status": "PASS",
                        "reason": "manual GO redecision recorded; this phase still performs no WordPress POST",
                        "wordpress_draft_creation": "PENDING_MANUAL_ONE_TIME_EXECUTION",
                        "phase7_5c_execution_unlocked_for_operator": True,
                        "next_step": "manual_execute_phase7_5c_with_execute_live_once",
                    }

            elif decision == "KEEP_FREEZE":
                result = {
                    **base,
                    "status": "PASS",
                    "reason": "FREEZE maintained by human decision",
                    "wordpress_draft_creation": "NO_GO",
                    "phase7_5c_execution_unlocked_for_operator": False,
                    "next_step": "freeze_maintain",
                }

            elif decision == "REQUEST_FIX":
                result = {
                    **base,
                    "status": "WARN",
                    "reason": "human requested fixes before any manual GO",
                    "wordpress_draft_creation": "NO_GO",
                    "phase7_5c_execution_unlocked_for_operator": False,
                    "next_step": "request_fix",
                }

            else:
                result = {
                    **base,
                    "status": "ABORT",
                    "reason": "human selected ABORT",
                    "wordpress_draft_creation": "NO_GO",
                    "phase7_5c_execution_unlocked_for_operator": False,
                    "next_step": "abort",
                }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = read_manual_go_redecision()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
