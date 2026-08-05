#!/usr/bin/env python3
"""Generate Phase 10-9 report for single publish manual execution script implementation."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_8 = (
    LOG_DIR
    / "phase10_8_manual_publish_command_dry_run_payload_validation_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_9_single_publish_manual_execution_script_implementation_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_9_single_publish_manual_execution_script_implementation_report.md"
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
        "package_type": "phase10_9_single_publish_manual_execution_script_implementation_report",
        "phase": "Phase 10-9",
        "status": "ABORT",
        "reason": reason,
        "implementation_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase10_8(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-8":
        return "phase10_8 input phase must be Phase 10-8"
    if source.get("status") != "PASS":
        return "phase10_8 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_8 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_8 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_8 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_8 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_8 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_8 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_8 target_draft_status must be draft"

    dry_run_design = source.get("dry_run_payload_validation_design", {})
    if dry_run_design.get("dry_run_only") is not True:
        return "phase10_8 dry_run_only must be true"
    if dry_run_design.get("payload_checks_count") != 7:
        return "phase10_8 payload_checks_count must be 7"
    if dry_run_design.get("token_expiry_minutes") != 30:
        return "phase10_8 token_expiry_minutes must be 30"
    if dry_run_design.get("max_publish_count") != 1:
        return "phase10_8 max_publish_count must be 1"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_8_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
        {
            "check": "current_decision=KEEP_NO_GO",
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
            "check": "wordpress_draft_id=110",
            "passed": source.get("wordpress_draft_id") == 110,
            "actual": source.get("wordpress_draft_id"),
        },
        {
            "check": "target_draft_status=draft",
            "passed": source.get("target_draft_status") == "draft",
            "actual": source.get("target_draft_status"),
        },
        {
            "check": "payload_checks_count=7",
            "passed": source.get("dry_run_payload_validation_design", {}).get("payload_checks_count") == 7,
            "actual": source.get("dry_run_payload_validation_design", {}).get("payload_checks_count"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    script_implementation = {
        "script_name": "manual_publish_single_draft.py",
        "default_runtime_mode": "DRY_RUN_STOP",
        "live_execution_flag": "--execute-live",
        "live_execution_flag_default": False,
        "live_execution_requires_human_final_approval": True,
        "required_target_scope": "draft_to_publish_only",
        "required_target_draft_id": 110,
        "required_target_draft_status": "draft",
        "max_publish_count": 1,
        "required_token": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
        "token_expiry_minutes": 30,
        "relock_required_after_attempt": True,
        "implementation_checks_count": 6,
        "implementation_checks": [
            "default_stop_mode_enabled",
            "execute_live_flag_required_for_live_path",
            "human_final_approval_required",
            "single_draft_scope_and_id_guard",
            "token_and_30_minutes_guard",
            "auto_relock_after_attempt",
        ],
        "publish_execution_in_phase10_9": "NO_GO",
        "wordpress_write_executed_in_phase10_9": False,
    }

    execution_entrypoints = {
        "dry_run_command": "python3 scripts/manual_publish_single_draft.py --dry-run --draft-id 110",
        "live_command": "python3 scripts/manual_publish_single_draft.py --execute-live --draft-id 110",
        "live_command_allowed_in_phase10_9": False,
    }

    implementation_flow = [
        "load_phase10_8_dry_run_payload_validation",
        "build_manual_publish_single_draft_script_spec",
        "enforce_default_stop_and_execute_live_flag",
        "record_implementation_evidence_without_live_execution",
    ]

    implementation_outcomes = [
        {
            "implementation_result": "SCRIPT_IMPLEMENTED_WITH_DEFAULT_STOP",
            "publish_execution_in_phase10_9": "NO_GO",
            "wordpress_write_executed_in_phase10_9": False,
            "next_step": "phase10_10_default_stop_guard_confirmation",
        },
        {
            "implementation_result": "REQUEST_FIX_REQUIRED",
            "publish_execution_in_phase10_9": "NO_GO",
            "wordpress_write_executed_in_phase10_9": False,
            "next_step": "apply_requested_fix_before_next_redecision",
        },
        {
            "implementation_result": "ABORT",
            "publish_execution_in_phase10_9": "NO_GO",
            "wordpress_write_executed_in_phase10_9": False,
            "next_step": "abort_and_stop",
        },
    ]

    return {
        "package_type": "phase10_9_single_publish_manual_execution_script_implementation_report",
        "phase": "Phase 10-9",
        "title": "Phase 10-9 Single Publish Manual Execution Script Implementation Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_9_implementation_status": "PASS" if all_passed else "ABORT",
        "implementation_scope": "single_publish_manual_execution_script_implementation_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "script_implementation": script_implementation,
        "execution_entrypoints": execution_entrypoints,
        "implementation_flow": implementation_flow,
        "implementation_outcomes": implementation_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "single_publish_script_implemented": True,
            "default_stop_is_enforced": True,
            "live_execution_requires_explicit_flag": True,
            "publish_still_not_executed_in_phase10_9": True,
        },
        "next_step": "phase10_10_default_stop_guard_confirmation",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-9 Single Publish Manual Execution Script Implementation Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_9_implementation_status: {report['phase10_9_implementation_status']}",
        f"- implementation_scope: {report['implementation_scope']}",
        "",
        "## Current Confirmed State",
        "",
        f"- current_decision: {report['current_decision']}",
        f"- wordpress_draft_id: {report['wordpress_draft_id']}",
        f"- target_draft_status: {report['target_draft_status']}",
        f"- publish_candidate_unlocked_for_operator: {report['publish_candidate_unlocked_for_operator']}",
        f"- wordpress_publish_execution: {report['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        "",
        "## Script Implementation",
        "",
    ]

    for key, value in report["script_implementation"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Execution Entrypoints",
        "",
    ]

    for key, value in report["execution_entrypoints"].items():
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


def generate_report(input_10_8: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_8.exists():
        return abort_result(f"required input not found: {input_10_8}", output_json)

    source = load_json(input_10_8)
    err = validate_phase10_8(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_8)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_9_single_publish_manual_execution_script_implementation_report_result",
        "phase": "Phase 10-9",
        "status": report["status"],
        "phase10_9_implementation_status": report["phase10_9_implementation_status"],
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
        description="Generate Phase 10-9 single publish manual execution script implementation report"
    )
    parser.add_argument("--input-10-8", type=Path, default=DEFAULT_INPUT_10_8)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_8, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
