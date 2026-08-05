#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "exchange/human_review/phase7_5h_manual_wp_admin_verification.json"
FALLBACK_INPUT = ROOT / "exchange/human_review/phase7_5h_manual_wp_admin_verification.example.json"
PHASE7_5C_RESULT = ROOT / "exchange/logs/phase7_5c_single_draft_create_live_result.json"
PHASE7_5G_RESULT = ROOT / "exchange/logs/phase7_5g_post_draft_creation_verification_report.json"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase7_5h_manual_wp_admin_verification_result.json"

VALID_DECISIONS = {"KEEP", "MANUAL_DELETE", "REQUEST_FIX", "ABORT"}

CONFIRMATION_KEYS = [
    "post_id_exists_confirmed",
    "status_is_draft_confirmed",
    "not_published_confirmed",
    "title_matches_expected_confirmed",
    "content_sanity_checked_confirmed",
    "manual_delete_if_unneeded_confirmed",
]

FORBIDDEN_TRUE_FLAGS = [
    "publish_allowed",
    "update_allowed",
    "delete_allowed",
    "export_allowed",
    "wordpress_post_enabled",
    "real_write_enabled",
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
        "package_type": "phase7_5h_manual_wp_admin_verification_result",
        "phase": "Phase 7-5H",
        "status": "ABORT",
        "decision": "ABORT",
        "reason": reason,
        "manual_decision_recorded": False,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "DONE_DRAFT_CREATED",
        "wordpress_post_enabled": False,
        "real_write_enabled": False,
        "wordpress_write_executed": True,
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
    confirmations = data.get("manual_confirmation", {})
    return all(confirmations.get(key) is True for key in CONFIRMATION_KEYS)


def validate_no_go_flags(data: dict) -> dict | None:
    safety_flags = data.get("safety_flags", {})
    if not isinstance(safety_flags, dict):
        return abort_result("safety_flags must be an object")

    for flag in FORBIDDEN_TRUE_FLAGS:
        if safety_flags.get(flag) is True or data.get(flag) is True:
            return abort_result(f"{flag}=true is forbidden in Phase 7-5H")

    return None


def read_manual_wp_admin_verification(input_path=None, output_path=None) -> dict:
    input_path = (
        Path(input_path)
        if input_path
        else (DEFAULT_INPUT if DEFAULT_INPUT.exists() else FALLBACK_INPUT)
    )
    output_path = Path(output_path or DEFAULT_OUTPUT)

    if not PHASE7_5C_RESULT.exists():
        result = abort_result(f"phase7_5c result file not found: {PHASE7_5C_RESULT}")
    elif not PHASE7_5G_RESULT.exists():
        result = abort_result(f"phase7_5g result file not found: {PHASE7_5G_RESULT}")
    elif not input_path.exists():
        result = abort_result(f"manual wp-admin verification file not found: {input_path}")
    else:
        phase7_5c = load_json(PHASE7_5C_RESULT)
        phase7_5g = load_json(PHASE7_5G_RESULT)
        data = load_json(input_path)

        if data.get("mode") != "CONNECTION_TEST":
            result = abort_result("mode must be CONNECTION_TEST")
        elif data.get("execution") != "DRY_RUN":
            result = abort_result("execution must be DRY_RUN")
        elif data.get("reviewer_is_human") is not True:
            result = abort_result("reviewer_is_human must be true")
        elif phase7_5c.get("status") != "PASS":
            result = abort_result("phase7_5c status must be PASS")
        elif phase7_5g.get("status") != "PASS":
            result = abort_result("phase7_5g status must be PASS")
        elif phase7_5c.get("created_post_status") != "draft":
            result = abort_result("phase7_5c created_post_status must be draft")
        elif phase7_5c.get("wordpress_write_executed") is not True:
            result = abort_result("phase7_5c wordpress_write_executed must be true")
        elif phase7_5c.get("relocked_after_execution") is not True:
            result = abort_result("phase7_5c relocked_after_execution must be true")
        else:
            no_go_err = validate_no_go_flags(data)
            if no_go_err:
                result = no_go_err
            else:
                decision = data.get("decision")
                if decision not in VALID_DECISIONS:
                    result = abort_result(f"unknown decision: {decision}")
                else:
                    expected_draft_id = (
                        phase7_5c.get("wordpress_draft_id")
                        or phase7_5c.get("created_post_id")
                        or phase7_5g.get("wordpress_draft_id")
                    )
                    provided_draft_id = data.get("wordpress_draft_id")

                    if expected_draft_id is None:
                        result = abort_result("expected draft id not found in phase7_5c/7_5g logs")
                    elif provided_draft_id != expected_draft_id:
                        result = abort_result(
                            f"wordpress_draft_id mismatch: expected={expected_draft_id} actual={provided_draft_id}"
                        )
                    else:
                        all_confirmed = all_confirmations_true(data)

                        base = {
                            "package_type": "phase7_5h_manual_wp_admin_verification_result",
                            "phase": "Phase 7-5H",
                            "mode": "CONNECTION_TEST",
                            "execution": "DRY_RUN",
                            "decision": decision,
                            "reviewer": data.get("reviewer"),
                            "reviewer_is_human": True,
                            "manual_decision_recorded": True,
                            "all_manual_confirmation_passed": all_confirmed,
                            "wordpress_draft_id": expected_draft_id,
                            "created_post_status": "draft",
                            "wordpress_write_executed": True,
                            "relocked_after_execution": True,
                            "production_status": "NO_GO",
                            "wordpress_draft_creation": "DONE_DRAFT_CREATED",
                            "publish_allowed": False,
                            "update_allowed": False,
                            "delete_allowed": False,
                            "export_allowed": False,
                            "auto_post": False,
                            "auto_update": False,
                            "auto_delete": False,
                            "auto_export": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        }

                        if decision == "KEEP":
                            if not all_confirmed:
                                result = abort_result(
                                    "all manual confirmation items must be true for KEEP decision"
                                )
                            else:
                                result = {
                                    **base,
                                    "status": "PASS",
                                    "reason": "manual wp-admin verification completed; draft kept",
                                    "next_step": "keep_draft_and_maintain_no_go",
                                }
                        elif decision == "MANUAL_DELETE":
                            if not all_confirmed:
                                result = abort_result(
                                    "all manual confirmation items must be true for MANUAL_DELETE decision"
                                )
                            else:
                                result = {
                                    **base,
                                    "status": "PASS",
                                    "reason": "manual wp-admin verification completed; proceed with human manual delete if needed",
                                    "next_step": "manual_delete_in_wp_admin_if_unneeded",
                                }
                        elif decision == "REQUEST_FIX":
                            result = {
                                **base,
                                "status": "WARN",
                                "reason": "manual verification found issues; fixes requested",
                                "next_step": "request_fix",
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
    result = read_manual_wp_admin_verification()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "ABORT":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
