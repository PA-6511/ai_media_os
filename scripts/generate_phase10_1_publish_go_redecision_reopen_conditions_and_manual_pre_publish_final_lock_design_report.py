#!/usr/bin/env python3
"""Generate Phase 10-1 design report for reopen conditions and manual pre-publish final lock."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_9_5 = LOG_DIR / "phase9_5_publish_go_redecision_route_no_go_maintenance_closure_report.json"
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report.md"
)

STILL_FORBIDDEN = [
    "wordpress_publish",
    "wordpress_update_existing_post",
    "wordpress_delete_post",
    "wordpress_export",
    "wordpress_bulk_post",
    "cron_automation",
    "github_actions_trigger",
    "slack_production_notification",
    "vps_self_builder_execution",
    "env_or_secrets_or_credentials_auto_edit",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def abort_result(reason: str, output_json: Path) -> dict:
    result = {
        "package_type": "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report",
        "phase": "Phase 10-1",
        "status": "ABORT",
        "reason": reason,
        "design_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase9_5(source: dict) -> str | None:
    if source.get("phase") != "Phase 9-5":
        return "phase9_5 input phase must be Phase 9-5"
    if source.get("status") != "PASS":
        return "phase9_5 input status must be PASS"
    if source.get("phase9_2_decision") != "KEEP_NO_GO":
        return "phase9_5 phase9_2_decision must be KEEP_NO_GO"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase9_5 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase9_5 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase9_5 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase9_5 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase9_5 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase9_5 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase9_5 target_draft_status must be draft"
    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase9_5_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
        {
            "check": "phase9_5_current_decision=KEEP_NO_GO",
            "passed": source.get("current_decision") == "KEEP_NO_GO",
            "actual": source.get("current_decision"),
        },
        {
            "check": "publish_candidate_unlocked_for_operator=false",
            "passed": source.get("publish_candidate_unlocked_for_operator") is False,
            "actual": source.get("publish_candidate_unlocked_for_operator"),
        },
        {
            "check": "wordpress_publish_execution=NO_GO",
            "passed": source.get("wordpress_publish_execution") == "NO_GO",
            "actual": source.get("wordpress_publish_execution"),
        },
        {
            "check": "wordpress_write_executed=false",
            "passed": source.get("wordpress_write_executed") is False,
            "actual": source.get("wordpress_write_executed"),
        },
        {
            "check": "production_status=NO_GO",
            "passed": source.get("production_status") == "NO_GO",
            "actual": source.get("production_status"),
        },
        {
            "check": "wordpress_draft_id=110",
            "passed": source.get("wordpress_draft_id") == 110,
            "actual": source.get("wordpress_draft_id"),
        },
        {
            "check": "target_draft_status=draft",
            "passed": source.get("target_draft_status") == "draft",
            "actual": source.get("target_draft_status"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    reopen_conditions = [
        "phase9_5 closure report remains PASS",
        "current_decision is explicitly changed by a human reviewer",
        "approval token APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY is newly issued",
        "approval token is valid within 30 minutes",
        "one-time publish scope is explicitly confirmed",
        "target draft id remains 110 and status remains draft",
        "publish/update/delete/export remain disabled until explicit manual unlock",
        "rollback path is manually confirmed before any publish attempt",
        "all prohibited automation paths remain NO_GO",
        "manual operator identity and timestamp are recorded",
    ]

    manual_pre_publish_final_lock_design = {
        "lock_state_default": "LOCKED",
        "unlock_trigger": "human_manual_go_redecision_only",
        "unlock_scope": "one_time_manual_publish_only",
        "approval_token_name": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
        "token_expiry_minutes": 30,
        "max_publish_count": 1,
        "requires_human_reviewer": True,
        "requires_pre_publish_checklist": True,
        "relock_required_after_attempt": True,
    }

    return {
        "package_type": "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report",
        "phase": "Phase 10-1",
        "title": "Phase 10-1 Reopen Conditions and Manual Pre-Publish Final Lock Design Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_1_design_status": "PASS" if all_passed else "ABORT",
        "design_scope": "reopen_conditions_and_manual_pre_publish_final_lock_design_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "reopen_conditions": reopen_conditions,
        "manual_pre_publish_final_lock_design": manual_pre_publish_final_lock_design,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "phase9_closed_safely": True,
            "reopen_route_designed": True,
            "manual_pre_publish_final_lock_designed": True,
            "publish_still_not_executed": True,
        },
        "next_step": "phase10_2_manual_redecision_input_and_final_lock_validation_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-1 Reopen Conditions and Manual Pre-Publish Final Lock Design Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_1_design_status: {report['phase10_1_design_status']}",
        f"- design_scope: {report['design_scope']}",
        "",
        "## Current Confirmed State",
        "",
        f"- current_decision: {report['current_decision']}",
        f"- wordpress_draft_id: {report['wordpress_draft_id']}",
        f"- target_draft_status: {report['target_draft_status']}",
        f"- publish_candidate_unlocked_for_operator: {report['publish_candidate_unlocked_for_operator']}",
        f"- wordpress_publish_execution: {report['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- production_status: {report['production_status']}",
        "",
        "## Reopen Conditions",
        "",
    ]

    for item in report["reopen_conditions"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Manual Pre-Publish Final Lock Design",
        "",
    ]

    for key, value in report["manual_pre_publish_final_lock_design"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Validation Checks",
        "",
        "| Check | Result |",
        "|---|---|",
    ]

    for c in report["validation_checks"]:
        lines.append(f"| {c['check']} | {'OK' if c['passed'] else 'NG'} |")

    lines += [
        "",
        "## Still Forbidden",
        "",
    ]

    for item in report["still_forbidden"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Next Step",
        "",
        report["next_step"],
        "",
    ]

    return "\n".join(lines)


def generate_report(input_9_5: Path, output_json: Path, output_md: Path) -> dict:
    if not input_9_5.exists():
        return abort_result(f"required input not found: {input_9_5}", output_json)

    source = load_json(input_9_5)
    err = validate_phase9_5(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_9_5)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report_result",
        "phase": "Phase 10-1",
        "status": report["status"],
        "phase10_1_design_status": report["phase10_1_design_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": normalize_path(output_json),
        "markdown_output": normalize_path(output_md),
        "current_decision": report["current_decision"],
        "publish_candidate_unlocked_for_operator": report["publish_candidate_unlocked_for_operator"],
        "wordpress_publish_execution": report["wordpress_publish_execution"],
        "wordpress_write_executed": report["wordpress_write_executed"],
        "next_step": report["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Phase 10-1 reopen conditions and manual pre-publish final lock design report"
    )
    parser.add_argument("--input-9-5", type=Path, default=DEFAULT_INPUT_9_5)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_9_5, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
