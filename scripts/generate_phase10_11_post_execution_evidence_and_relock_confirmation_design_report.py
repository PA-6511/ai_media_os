#!/usr/bin/env python3
"""Generate Phase 10-11 report for post-execution evidence and relock confirmation design."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_10 = LOG_DIR / "phase10_10_default_stop_guard_confirmation_report.json"
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.md"
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
        "package_type": "phase10_11_post_execution_evidence_and_relock_confirmation_design_report",
        "phase": "Phase 10-11",
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


def validate_phase10_10(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-10":
        return "phase10_10 input phase must be Phase 10-10"
    if source.get("status") != "PASS":
        return "phase10_10 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_10 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_10 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_10 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_10 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_10 production_status must be NO_GO"

    guard_confirmation = source.get("default_stop_guard_confirmation", {})
    if guard_confirmation.get("confirmed_default_stop") is not True:
        return "phase10_10 confirmed_default_stop must be true"
    if guard_confirmation.get("confirmed_live_requires_explicit_flag") is not True:
        return "phase10_10 confirmed_live_requires_explicit_flag must be true"
    if guard_confirmation.get("confirmed_live_is_blocked_without_flag") is not True:
        return "phase10_10 confirmed_live_is_blocked_without_flag must be true"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_10_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
        {
            "check": "confirmed_default_stop=true",
            "passed": source.get("default_stop_guard_confirmation", {}).get("confirmed_default_stop") is True,
            "actual": source.get("default_stop_guard_confirmation", {}).get("confirmed_default_stop"),
        },
        {
            "check": "confirmed_live_requires_explicit_flag=true",
            "passed": source.get("default_stop_guard_confirmation", {}).get("confirmed_live_requires_explicit_flag") is True,
            "actual": source.get("default_stop_guard_confirmation", {}).get("confirmed_live_requires_explicit_flag"),
        },
        {
            "check": "confirmed_live_is_blocked_without_flag=true",
            "passed": source.get("default_stop_guard_confirmation", {}).get("confirmed_live_is_blocked_without_flag") is True,
            "actual": source.get("default_stop_guard_confirmation", {}).get("confirmed_live_is_blocked_without_flag"),
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

    post_execution_evidence_and_relock_design = {
        "evidence_log_path": "exchange/logs/phase10_11_post_execution_evidence.json",
        "relock_log_path": "exchange/logs/phase10_11_relock_confirmation.json",
        "required_evidence_fields": [
            "phase",
            "run_mode",
            "execution_attempted",
            "live_flag_present",
            "target_draft_id",
            "target_draft_status_before",
            "target_draft_status_after",
            "publish_count",
            "result",
            "operator",
            "executed_at",
            "relock_status",
        ],
        "required_relock_fields": [
            "relock_applied",
            "relock_reason",
            "relocked_at",
            "lock_state_after",
        ],
        "relock_mandatory": True,
        "publish_execution_in_phase10_11": "NO_GO",
        "wordpress_write_executed_in_phase10_11": False,
    }

    post_execution_flow = [
        "load_phase10_10_default_stop_guard_confirmation",
        "define_post_execution_evidence_schema",
        "define_relock_confirmation_schema",
        "require_relock_after_any_attempt",
        "keep_publish_not_executed_in_phase10_11",
    ]

    post_execution_outcomes = [
        {
            "post_execution_result": "EVIDENCE_AND_RELOCK_DESIGN_FIXED",
            "publish_execution_in_phase10_11": "NO_GO",
            "wordpress_write_executed_in_phase10_11": False,
            "next_step": "phase10_12_manual_live_execution_readiness_review",
        },
        {
            "post_execution_result": "REQUEST_FIX_REQUIRED",
            "publish_execution_in_phase10_11": "NO_GO",
            "wordpress_write_executed_in_phase10_11": False,
            "next_step": "apply_requested_fix_before_next_redecision",
        },
    ]

    return {
        "package_type": "phase10_11_post_execution_evidence_and_relock_confirmation_design_report",
        "phase": "Phase 10-11",
        "title": "Phase 10-11 Post Execution Evidence and Relock Confirmation Design Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_11_design_status": "PASS" if all_passed else "ABORT",
        "design_scope": "post_execution_evidence_and_relock_confirmation_design_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id", 110),
        "target_draft_status": source.get("target_draft_status", "draft"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "post_execution_evidence_and_relock_design": post_execution_evidence_and_relock_design,
        "post_execution_flow": post_execution_flow,
        "post_execution_outcomes": post_execution_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "post_execution_evidence_design_fixed": True,
            "relock_confirmation_design_fixed": True,
            "publish_still_not_executed_in_phase10_11": True,
        },
        "next_step": "phase10_12_manual_live_execution_readiness_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-11 Post Execution Evidence and Relock Confirmation Design Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_11_design_status: {report['phase10_11_design_status']}",
        "",
        "## Post Execution Evidence and Relock Design",
        "",
    ]

    for key, value in report["post_execution_evidence_and_relock_design"].items():
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


def generate_report(input_10_10: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_10.exists():
        return abort_result(f"required input not found: {input_10_10}", output_json)

    source = load_json(input_10_10)
    err = validate_phase10_10(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_10)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_11_post_execution_evidence_and_relock_confirmation_design_report_result",
        "phase": "Phase 10-11",
        "status": report["status"],
        "phase10_11_design_status": report["phase10_11_design_status"],
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
        description="Generate Phase 10-11 post execution evidence and relock confirmation design report"
    )
    parser.add_argument("--input-10-10", type=Path, default=DEFAULT_INPUT_10_10)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_10, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
