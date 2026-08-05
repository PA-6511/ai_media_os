#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/phase8_2_manual_pre_publish_review.json"
FALLBACK_INPUT = ROOT / "exchange/human_review/phase8_2_manual_pre_publish_review.example.json"
PHASE8_1_RESULT = ROOT / "exchange/logs/phase8_1_pre_publish_review_design_validation_result.json"
PHASE7_6_RESULT = ROOT / "exchange/logs/phase7_6_wordpress_draft_creation_overall_completion_report.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_2_manual_pre_publish_review_result.json"

VALID_DECISIONS = {"APPROVE", "REQUEST_FIX", "REJECT", "ABORT"}

CONFIRMATION_KEYS = [
    "title_reviewed",
    "content_reviewed",
    "pr_disclosure_confirmed",
    "links_valid_confirmed",
    "affiliate_tag_confirmed",
    "category_confirmed",
    "tags_confirmed",
    "publish_block_conditions_checked",
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
        "package_type": "phase8_2_manual_pre_publish_review_result",
        "phase": "Phase 8-2",
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
            return abort_result(f"{flag}=true is forbidden in Phase 8-2")

    return None


def read_manual_pre_publish_review(input_path=None, output_path=None) -> dict:
    input_path = (
        Path(input_path)
        if input_path
        else (DEFAULT_INPUT if DEFAULT_INPUT.exists() else FALLBACK_INPUT)
    )
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not PHASE8_1_RESULT.exists():
        result = abort_result(f"phase8_1 result file not found: {PHASE8_1_RESULT}")
    elif not PHASE7_6_RESULT.exists():
        result = abort_result(f"phase7_6 result file not found: {PHASE7_6_RESULT}")
    elif not input_path.exists():
        result = abort_result(f"manual pre-publish review file not found: {input_path}")
    else:
        p81 = load_json(PHASE8_1_RESULT)
        p76 = load_json(PHASE7_6_RESULT)
        data = load_json(input_path)

        if data.get("mode") != "CONNECTION_TEST":
            result = abort_result("mode must be CONNECTION_TEST")
        elif data.get("execution") != "DRY_RUN":
            result = abort_result("execution must be DRY_RUN")
        elif data.get("reviewer_is_human") is not True:
            result = abort_result("reviewer_is_human must be true")
        elif p81.get("status") != "PASS":
            result = abort_result("phase8_1 status must be PASS")
        elif p76.get("status") != "PASS":
            result = abort_result("phase7_6 status must be PASS")
        elif p76.get("created_post_status") != "draft":
            result = abort_result("phase7_6 created_post_status must be draft")
        else:
            no_go_err = validate_no_go_flags(data)
            if no_go_err:
                result = no_go_err
            else:
                decision = data.get("decision")
                if decision not in VALID_DECISIONS:
                    result = abort_result(f"unknown decision: {decision}")
                else:
                    expected_draft_id = p76.get("wordpress_draft_id")
                    provided_draft_id = data.get("wordpress_draft_id")
                    if expected_draft_id is None:
                        result = abort_result("expected draft id not found in phase7_6 log")
                    elif provided_draft_id != expected_draft_id:
                        result = abort_result(
                            f"wordpress_draft_id mismatch: expected={expected_draft_id} actual={provided_draft_id}"
                        )
                    else:
                        all_confirmed = all_confirmations_true(data)
                        fix_requests = data.get("review_notes", {}).get("fix_requests", [])

                        base = {
                            "package_type": "phase8_2_manual_pre_publish_review_result",
                            "phase": "Phase 8-2",
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

                        if decision == "APPROVE":
                            if not all_confirmed:
                                result = abort_result(
                                    "all manual confirmation items must be true for APPROVE"
                                )
                            else:
                                result = {
                                    **base,
                                    "status": "PASS",
                                    "reason": "manual pre-publish review approved; publish remains locked in phase8_2",
                                    "next_step": "phase8_3_publish_gate_design_only",
                                }
                        elif decision == "REQUEST_FIX":
                            result = {
                                **base,
                                "status": "WARN",
                                "reason": "manual pre-publish review requested fixes",
                                "next_step": "request_fix_and_re_review",
                            }
                        elif decision == "REJECT":
                            result = {
                                **base,
                                "status": "WARN",
                                "reason": "manual pre-publish review rejected for publication",
                                "next_step": "reject_and_keep_draft",
                            }
                        else:
                            result = {
                                **base,
                                "status": "ABORT",
                                "reason": "human selected ABORT",
                                "next_step": "abort",
                            }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = read_manual_pre_publish_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") != "ABORT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
