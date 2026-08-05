#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/phase8_7_publish_go_no_go_decision.json"
FALLBACK_INPUT = ROOT / "exchange/human_review/phase8_7_publish_go_no_go_decision.example.json"
PHASE8_6_RESULT = ROOT / "exchange/logs/phase8_6_pre_publish_final_readiness_validation_result.json"
PHASE8_2_RESULT = ROOT / "exchange/logs/phase8_2_manual_pre_publish_review_result.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_7_publish_go_no_go_decision_result.json"

VALID_DECISIONS = {
    "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
    "KEEP_NO_GO",
    "REQUEST_FIX",
    "ABORT",
}

VALID_GO_TOKEN = "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY"

CONFIRMATION_KEYS = [
    "phase8_6_readiness_pass_confirmed",
    "target_draft_id_confirmed",
    "target_status_draft_confirmed",
    "human_reviewer_confirmed",
    "token_constraints_confirmed",
    "no_go_scope_understood_confirmed",
    "manual_publish_only_confirmed",
    "publish_not_executed_in_phase8_7_confirmed",
]

FORBIDDEN_TRUE_FLAGS = [
    "publish_allowed",
    "update_allowed",
    "delete_allowed",
    "export_allowed",
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
        "package_type": "phase8_7_publish_go_no_go_decision_result",
        "phase": "Phase 8-7",
        "status": "ABORT",
        "decision": "ABORT",
        "reason": reason,
        "manual_decision_recorded": False,
        "production_status": "NO_GO",
        "wordpress_publish_execution": "NO_GO",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "next_step": "abort",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def all_confirmations_true(data: dict) -> bool:
    confirmation = data.get("manual_confirmation", {})
    return all(confirmation.get(k) is True for k in CONFIRMATION_KEYS)


def validate_no_go_flags(data: dict) -> dict | None:
    flags = data.get("safety_flags", {})
    if not isinstance(flags, dict):
        return abort_result("safety_flags must be an object")

    for flag in FORBIDDEN_TRUE_FLAGS:
        if flags.get(flag) is True or data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in Phase 8-7")

    return None


def read_publish_go_no_go_decision(input_path=None, output_path=None) -> dict:
    input_path = (
        Path(input_path)
        if input_path
        else (DEFAULT_INPUT if DEFAULT_INPUT.exists() else FALLBACK_INPUT)
    )
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not PHASE8_6_RESULT.exists():
        result = abort_result(f"phase8_6 result file not found: {PHASE8_6_RESULT}")
    elif not PHASE8_2_RESULT.exists():
        result = abort_result(f"phase8_2 result file not found: {PHASE8_2_RESULT}")
    elif not input_path.exists():
        result = abort_result(f"manual go/no-go decision file not found: {input_path}")
    else:
        p86 = load_json(PHASE8_6_RESULT)
        p82 = load_json(PHASE8_2_RESULT)
        data = load_json(input_path)

        if data.get("mode") != "CONNECTION_TEST":
            result = abort_result("mode must be CONNECTION_TEST")
        elif data.get("execution") != "DRY_RUN":
            result = abort_result("execution must be DRY_RUN")
        elif data.get("reviewer_is_human") is not True:
            result = abort_result("reviewer_is_human must be true")
        elif p86.get("status") != "PASS":
            result = abort_result("phase8_6 status must be PASS")
        elif p82.get("decision") != "APPROVE":
            result = abort_result("phase8_2 decision must be APPROVE")
        else:
            no_go_err = validate_no_go_flags(data)
            if no_go_err:
                result = no_go_err
            else:
                decision = data.get("decision")
                if decision not in VALID_DECISIONS:
                    result = abort_result(f"unknown decision: {decision}")
                else:
                    expected_draft_id = p86.get("target_draft_id")
                    provided_draft_id = data.get("wordpress_draft_id")
                    if expected_draft_id is None:
                        result = abort_result("expected draft id not found in phase8_6 log")
                    elif provided_draft_id != expected_draft_id:
                        result = abort_result(
                            f"wordpress_draft_id mismatch: expected={expected_draft_id} actual={provided_draft_id}"
                        )
                    else:
                        all_confirmed = all_confirmations_true(data)
                        fix_requests = data.get("review_notes", {}).get("fix_requests", [])

                        base = {
                            "package_type": "phase8_7_publish_go_no_go_decision_result",
                            "phase": "Phase 8-7",
                            "mode": "CONNECTION_TEST",
                            "execution": "DRY_RUN",
                            "decision": decision,
                            "reviewer": data.get("reviewer"),
                            "reviewer_is_human": True,
                            "manual_decision_recorded": True,
                            "all_manual_confirmation_passed": all_confirmed,
                            "wordpress_draft_id": expected_draft_id,
                            "target_draft_status": "draft",
                            "production_status": "NO_GO",
                            "wordpress_publish_execution": "NO_GO",
                            "wordpress_post_enabled": False,
                            "real_write_enabled": False,
                            "wordpress_write_executed": False,
                            "publish_allowed": False,
                            "update_allowed": False,
                            "delete_allowed": False,
                            "export_allowed": False,
                            "auto_post": False,
                            "auto_update": False,
                            "auto_delete": False,
                            "auto_export": False,
                            "fix_requests": fix_requests,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }

                        if decision == "GO_PUBLISH_ONE_TIME_MANUAL_ONLY":
                            if data.get("approval_token") != VALID_GO_TOKEN:
                                result = abort_result(
                                    "approval_token must be APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY"
                                )
                            elif not all_confirmed:
                                result = abort_result(
                                    "all manual confirmation items must be true for GO decision"
                                )
                            else:
                                result = {
                                    **base,
                                    "status": "PASS",
                                    "reason": "manual publish GO decision recorded; publish remains locked in phase8_7",
                                    "publish_candidate_unlocked_for_operator": True,
                                    "next_step": "phase8_8_manual_publish_candidate_only",
                                }
                        elif decision == "KEEP_NO_GO":
                            result = {
                                **base,
                                "status": "PASS",
                                "reason": "manual KEEP_NO_GO decision recorded",
                                "publish_candidate_unlocked_for_operator": False,
                                "next_step": "maintain_no_go",
                            }
                        elif decision == "REQUEST_FIX":
                            result = {
                                **base,
                                "status": "WARN",
                                "reason": "manual decision requested fixes before publish candidate",
                                "publish_candidate_unlocked_for_operator": False,
                                "next_step": "request_fix",
                            }
                        else:
                            result = {
                                **base,
                                "status": "ABORT",
                                "reason": "human selected ABORT",
                                "publish_candidate_unlocked_for_operator": False,
                                "next_step": "abort",
                            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = read_publish_go_no_go_decision()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "ABORT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
