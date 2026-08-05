#!/usr/bin/env python3
"""Generate Phase 10-14 report for pre-execution final freeze release judgment."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_13 = (
    LOG_DIR
    / "phase10_13_execute_live_final_human_authorization_gate_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_14_pre_execution_final_freeze_release_judgment_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_14_pre_execution_final_freeze_release_judgment_report.md"
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
        "package_type": "phase10_14_pre_execution_final_freeze_release_judgment_report",
        "phase": "Phase 10-14",
        "status": "ABORT",
        "reason": reason,
        "judgment_generated": False,
        "phase10_14_final_judgment": "KEEP_NO_GO",
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase10_13(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-13":
        return "phase10_13 input phase must be Phase 10-13"
    if source.get("status") != "PASS":
        return "phase10_13 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_13 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_13 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_13 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_13 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_13 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_13 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_13 target_draft_status must be draft"

    gate = source.get("execute_live_final_human_authorization_gate", {})
    if gate.get("default_authorization") != "DENY":
        return "phase10_13 default_authorization must be DENY"
    if gate.get("required_authorization_token") != "APPROVE_EXECUTE_LIVE_ONE_TIME_MANUAL_ONLY":
        return "phase10_13 required_authorization_token mismatch"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_13_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
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
            "check": "default_authorization=DENY",
            "passed": source.get("execute_live_final_human_authorization_gate", {}).get("default_authorization") == "DENY",
            "actual": source.get("execute_live_final_human_authorization_gate", {}).get("default_authorization"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    final_freeze_release_judgment = {
        "judgment_name": "pre_execution_final_freeze_release_judgment",
        "default_judgment": "KEEP_NO_GO",
        "allowed_judgments": [
            "KEEP_NO_GO",
            "READY_FOR_MANUAL_EXECUTE_LIVE_ONE_TIME",
            "ABORT",
        ],
        "freeze_release_checks_count": 8,
        "freeze_release_checks": [
            "final_human_authorization_gate_passed",
            "target_draft_id_is_110",
            "target_draft_status_is_draft",
            "single_publish_limit_is_1",
            "relock_requirement_still_mandatory",
            "forbidden_operations_remain_locked",
            "publish_not_executed_in_phase10_14",
            "explicit_execute_live_runtime_command_required",
        ],
        "phase10_14_final_judgment": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "publish_execution_in_phase10_14": "NO_GO",
        "wordpress_write_executed_in_phase10_14": False,
    }

    freeze_release_outcomes = [
        {
            "judgment_result": "KEEP_NO_GO",
            "publish_candidate_unlocked_for_operator": False,
            "publish_execution_in_phase10_14": "NO_GO",
            "wordpress_write_executed_in_phase10_14": False,
            "next_step": "await_manual_redecision_before_any_execute_live",
        },
        {
            "judgment_result": "READY_FOR_MANUAL_EXECUTE_LIVE_ONE_TIME",
            "publish_candidate_unlocked_for_operator": False,
            "publish_execution_in_phase10_14": "NO_GO",
            "wordpress_write_executed_in_phase10_14": False,
            "next_step": "manual_operator_may_issue_explicit_execute_live_command_after_separate_go",
        },
    ]

    return {
        "package_type": "phase10_14_pre_execution_final_freeze_release_judgment_report",
        "phase": "Phase 10-14",
        "title": "Phase 10-14 Pre Execution Final Freeze Release Judgment Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_14_judgment_status": "PASS" if all_passed else "ABORT",
        "judgment_scope": "pre_execution_final_freeze_release_judgment_only",
        "source_report": normalize_path(input_path),
        "phase10_14_final_judgment": "KEEP_NO_GO",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "final_freeze_release_judgment": final_freeze_release_judgment,
        "freeze_release_outcomes": freeze_release_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "final_freeze_release_judgment_fixed": True,
            "phase10_14_final_judgment_keep_no_go": True,
            "publish_still_not_executed_in_phase10_14": True,
            "wordpress_write_still_not_executed_in_phase10_14": True,
        },
        "next_step": "hold_no_go_until_separate_manual_execute_live_authorization",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-14 Pre Execution Final Freeze Release Judgment Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_14_judgment_status: {report['phase10_14_judgment_status']}",
        f"- phase10_14_final_judgment: {report['phase10_14_final_judgment']}",
        "",
        "## Final Freeze Release Judgment",
        "",
    ]

    for key, value in report["final_freeze_release_judgment"].items():
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


def generate_report(input_10_13: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_13.exists():
        return abort_result(f"required input not found: {input_10_13}", output_json)

    source = load_json(input_10_13)
    err = validate_phase10_13(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_13)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_14_pre_execution_final_freeze_release_judgment_report_result",
        "phase": "Phase 10-14",
        "status": report["status"],
        "phase10_14_judgment_status": report["phase10_14_judgment_status"],
        "phase10_14_final_judgment": report["phase10_14_final_judgment"],
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
        description="Generate Phase 10-14 pre-execution final freeze release judgment report"
    )
    parser.add_argument("--input-10-13", type=Path, default=DEFAULT_INPUT_10_13)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_13, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
