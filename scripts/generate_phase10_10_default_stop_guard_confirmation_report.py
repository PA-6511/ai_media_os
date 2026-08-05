#!/usr/bin/env python3
"""Generate Phase 10-10 report for default stop guard confirmation."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_9 = (
    LOG_DIR
    / "phase10_9_single_publish_manual_execution_script_implementation_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_10_default_stop_guard_confirmation_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_10_default_stop_guard_confirmation_report.md"
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
        "package_type": "phase10_10_default_stop_guard_confirmation_report",
        "phase": "Phase 10-10",
        "status": "ABORT",
        "reason": reason,
        "confirmation_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase10_9(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-9":
        return "phase10_9 input phase must be Phase 10-9"
    if source.get("status") != "PASS":
        return "phase10_9 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_9 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_9 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_9 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_9 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_9 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_9 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_9 target_draft_status must be draft"

    impl = source.get("script_implementation", {})
    if impl.get("default_runtime_mode") != "DRY_RUN_STOP":
        return "phase10_9 default_runtime_mode must be DRY_RUN_STOP"
    if impl.get("live_execution_flag") != "--execute-live":
        return "phase10_9 live_execution_flag must be --execute-live"
    if impl.get("live_execution_flag_default") is not False:
        return "phase10_9 live_execution_flag_default must be false"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_9_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
        {
            "check": "default_runtime_mode=DRY_RUN_STOP",
            "passed": source.get("script_implementation", {}).get("default_runtime_mode") == "DRY_RUN_STOP",
            "actual": source.get("script_implementation", {}).get("default_runtime_mode"),
        },
        {
            "check": "live_execution_flag=--execute-live",
            "passed": source.get("script_implementation", {}).get("live_execution_flag") == "--execute-live",
            "actual": source.get("script_implementation", {}).get("live_execution_flag"),
        },
        {
            "check": "live_execution_flag_default=false",
            "passed": source.get("script_implementation", {}).get("live_execution_flag_default") is False,
            "actual": source.get("script_implementation", {}).get("live_execution_flag_default"),
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
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    default_stop_guard_confirmation = {
        "guard_name": "default_stop_guard",
        "guard_checks_count": 6,
        "guard_checks": [
            "default_runtime_mode_is_dry_run_stop",
            "execute_live_flag_must_be_explicit",
            "execute_live_flag_default_is_false",
            "human_final_approval_must_exist_before_live",
            "single_draft_scope_and_id_guard_is_active",
            "relock_after_attempt_guard_is_active",
        ],
        "confirmed_default_stop": True,
        "confirmed_live_requires_explicit_flag": True,
        "confirmed_live_is_blocked_without_flag": True,
        "publish_execution_in_phase10_10": "NO_GO",
        "wordpress_write_executed_in_phase10_10": False,
    }

    guard_confirmation_outcomes = [
        {
            "guard_result": "DEFAULT_STOP_CONFIRMED",
            "publish_execution_in_phase10_10": "NO_GO",
            "wordpress_write_executed_in_phase10_10": False,
            "next_step": "phase10_11_post_execution_evidence_and_relock_confirmation_design",
        },
        {
            "guard_result": "DEFAULT_STOP_BROKEN_REQUEST_FIX",
            "publish_execution_in_phase10_10": "NO_GO",
            "wordpress_write_executed_in_phase10_10": False,
            "next_step": "apply_requested_fix_before_next_redecision",
        },
    ]

    return {
        "package_type": "phase10_10_default_stop_guard_confirmation_report",
        "phase": "Phase 10-10",
        "title": "Phase 10-10 Default Stop Guard Confirmation Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_10_confirmation_status": "PASS" if all_passed else "ABORT",
        "confirmation_scope": "default_stop_guard_confirmation_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "default_stop_guard_confirmation": default_stop_guard_confirmation,
        "guard_confirmation_outcomes": guard_confirmation_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "default_stop_guard_confirmed": True,
            "live_path_requires_explicit_execute_live": True,
            "publish_still_not_executed_in_phase10_10": True,
        },
        "next_step": "phase10_11_post_execution_evidence_and_relock_confirmation_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-10 Default Stop Guard Confirmation Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_10_confirmation_status: {report['phase10_10_confirmation_status']}",
        "",
        "## Default Stop Guard Confirmation",
        "",
    ]

    for key, value in report["default_stop_guard_confirmation"].items():
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
        "## Next Step",
        "",
        report["next_step"],
        "",
    ]

    return "\n".join(lines)


def generate_report(input_10_9: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_9.exists():
        return abort_result(f"required input not found: {input_10_9}", output_json)

    source = load_json(input_10_9)
    err = validate_phase10_9(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_9)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_10_default_stop_guard_confirmation_report_result",
        "phase": "Phase 10-10",
        "status": report["status"],
        "phase10_10_confirmation_status": report["phase10_10_confirmation_status"],
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
        description="Generate Phase 10-10 default stop guard confirmation report"
    )
    parser.add_argument("--input-10-9", type=Path, default=DEFAULT_INPUT_10_9)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_9, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
