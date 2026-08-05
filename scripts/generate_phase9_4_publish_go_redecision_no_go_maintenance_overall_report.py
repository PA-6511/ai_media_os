#!/usr/bin/env python3
"""Generate Phase 9-4 overall report for GO redecision route and NO_GO maintenance."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_9_1 = LOG_DIR / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"
DEFAULT_INPUT_9_2 = LOG_DIR / "phase9_2_publish_go_redecision_input_gate_result.json"
DEFAULT_INPUT_9_3 = LOG_DIR / "phase9_3_keep_no_go_input_gate_completion_report.json"
DEFAULT_OUTPUT_JSON = LOG_DIR / "phase9_4_publish_go_redecision_no_go_maintenance_overall_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase9_4_publish_go_redecision_no_go_maintenance_overall_report.md"

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
        "package_type": "phase9_4_publish_go_redecision_no_go_maintenance_overall_report",
        "phase": "Phase 9-4",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "production_status": "NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_inputs(p91: dict, p92: dict, p93: dict) -> str | None:
    if p91.get("phase") != "Phase 9-1" or p91.get("status") != "PASS":
        return "phase9_1 input must be PASS"
    if p92.get("phase") != "Phase 9-2" or p92.get("status") != "PASS":
        return "phase9_2 input must be PASS"
    if p93.get("phase") != "Phase 9-3" or p93.get("status") != "PASS":
        return "phase9_3 input must be PASS"

    if p92.get("decision") != "KEEP_NO_GO":
        return "phase9_2 decision must be KEEP_NO_GO"
    if p93.get("phase9_2_decision") != "KEEP_NO_GO":
        return "phase9_3 phase9_2_decision must be KEEP_NO_GO"

    if p92.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase9_2 publish_candidate_unlocked_for_operator must be false"
    if p93.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase9_3 publish_candidate_unlocked_for_operator must be false"

    if p92.get("wordpress_publish_execution") != "NO_GO":
        return "phase9_2 wordpress_publish_execution must be NO_GO"
    if p93.get("wordpress_publish_execution") != "NO_GO":
        return "phase9_3 wordpress_publish_execution must be NO_GO"

    if p92.get("wordpress_write_executed") is not False:
        return "phase9_2 wordpress_write_executed must be false"
    if p93.get("wordpress_write_executed") is not False:
        return "phase9_3 wordpress_write_executed must be false"

    draft_ids = {p91.get("target_draft_id"), p92.get("wordpress_draft_id"), p93.get("wordpress_draft_id")}
    if len(draft_ids) != 1:
        return "draft id mismatch between phase9_1/9_2/9_3"
    if list(draft_ids)[0] != 110:
        return "target draft id must be 110"

    status_values = {p91.get("target_draft_status"), p92.get("target_draft_status"), p93.get("target_draft_status")}
    if status_values != {"draft"}:
        return "target_draft_status must be draft across phase9_1/9_2/9_3"

    if p91.get("wordpress_publish_execution") != "NO_GO":
        return "phase9_1 wordpress_publish_execution must be NO_GO"
    if p91.get("wordpress_write_executed") is not False:
        return "phase9_1 wordpress_write_executed must be false"

    if p91.get("production_status") != "NO_GO" or p92.get("production_status") != "NO_GO" or p93.get("production_status") != "NO_GO":
        return "production_status must remain NO_GO across phase9_1/9_2/9_3"

    for flag in FORBIDDEN_TRUE_FLAGS:
        if p92.get(flag) is True:
            return f"{flag}=true is forbidden"

    return None


def build_checks(p91: dict, p92: dict, p93: dict) -> list[dict]:
    checks = [
        {"check": "phase9_1_status=PASS", "passed": p91.get("status") == "PASS", "actual": p91.get("status")},
        {"check": "phase9_2_status=PASS", "passed": p92.get("status") == "PASS", "actual": p92.get("status")},
        {"check": "phase9_3_status=PASS", "passed": p93.get("status") == "PASS", "actual": p93.get("status")},
        {"check": "phase9_2_decision=KEEP_NO_GO", "passed": p92.get("decision") == "KEEP_NO_GO", "actual": p92.get("decision")},
        {
            "check": "phase9_3_phase9_2_decision=KEEP_NO_GO",
            "passed": p93.get("phase9_2_decision") == "KEEP_NO_GO",
            "actual": p93.get("phase9_2_decision"),
        },
        {
            "check": "publish_candidate_unlocked_for_operator=false",
            "passed": p92.get("publish_candidate_unlocked_for_operator") is False and p93.get("publish_candidate_unlocked_for_operator") is False,
            "actual": {
                "phase9_2": p92.get("publish_candidate_unlocked_for_operator"),
                "phase9_3": p93.get("publish_candidate_unlocked_for_operator"),
            },
        },
        {
            "check": "wordpress_publish_execution=NO_GO",
            "passed": p91.get("wordpress_publish_execution") == "NO_GO" and p92.get("wordpress_publish_execution") == "NO_GO" and p93.get("wordpress_publish_execution") == "NO_GO",
            "actual": {
                "phase9_1": p91.get("wordpress_publish_execution"),
                "phase9_2": p92.get("wordpress_publish_execution"),
                "phase9_3": p93.get("wordpress_publish_execution"),
            },
        },
        {
            "check": "wordpress_write_executed=false",
            "passed": p91.get("wordpress_write_executed") is False and p92.get("wordpress_write_executed") is False and p93.get("wordpress_write_executed") is False,
            "actual": {
                "phase9_1": p91.get("wordpress_write_executed"),
                "phase9_2": p92.get("wordpress_write_executed"),
                "phase9_3": p93.get("wordpress_write_executed"),
            },
        },
        {
            "check": "target_draft_id=110",
            "passed": p91.get("target_draft_id") == 110 and p92.get("wordpress_draft_id") == 110 and p93.get("wordpress_draft_id") == 110,
            "actual": {
                "phase9_1": p91.get("target_draft_id"),
                "phase9_2": p92.get("wordpress_draft_id"),
                "phase9_3": p93.get("wordpress_draft_id"),
            },
        },
        {
            "check": "target_draft_status=draft",
            "passed": p91.get("target_draft_status") == "draft" and p92.get("target_draft_status") == "draft" and p93.get("target_draft_status") == "draft",
            "actual": {
                "phase9_1": p91.get("target_draft_status"),
                "phase9_2": p92.get("target_draft_status"),
                "phase9_3": p93.get("target_draft_status"),
            },
        },
        {
            "check": "production_status=NO_GO",
            "passed": p91.get("production_status") == "NO_GO" and p92.get("production_status") == "NO_GO" and p93.get("production_status") == "NO_GO",
            "actual": {
                "phase9_1": p91.get("production_status"),
                "phase9_2": p92.get("production_status"),
                "phase9_3": p93.get("production_status"),
            },
        },
    ]
    return checks


def build_report(p91: dict, p92: dict, p93: dict, input_paths: dict[str, Path]) -> dict:
    checks = build_checks(p91, p92, p93)
    all_passed = all(c["passed"] for c in checks)

    report = {
        "package_type": "phase9_4_publish_go_redecision_no_go_maintenance_overall_report",
        "phase": "Phase 9-4",
        "title": "Phase 9-4 Publish GO Redecision and NO_GO Maintenance Overall Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase9_4_overall_status": "PASS" if all_passed else "ABORT",
        "aggregation_scope": "phase9_1_through_phase9_3",
        "source_reports": {
            "phase9_1": normalize_path(input_paths["phase9_1"]),
            "phase9_2": normalize_path(input_paths["phase9_2"]),
            "phase9_3": normalize_path(input_paths["phase9_3"]),
        },
        "route_readiness": {
            "publish_go_redecision_route_ready": True,
            "manual_publish_runbook_ready": p91.get("runbook_generated") is True,
            "input_gate_ready": p92.get("status") == "PASS",
            "keep_no_go_confirmation_ready": p93.get("status") == "PASS",
        },
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": p92.get("decision"),
        "wordpress_draft_id": p92.get("wordpress_draft_id"),
        "target_draft_status": p92.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "prohibited_actions_snapshot": {
            "wordpress_publish": "NO_GO",
            "wordpress_update": "NO_GO",
            "wordpress_delete": "NO_GO",
            "wordpress_export": "NO_GO",
            "github_actions_trigger": "NO_GO",
            "slack_production_notification": "NO_GO",
            "vps_self_builder_execute": "NO_GO",
        },
        "forbidden_true_flags_checked": FORBIDDEN_TRUE_FLAGS,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "route_prepared_but_not_executed": True,
            "keep_no_go_maintained": True,
            "publish_candidate_locked": True,
            "publish_not_executed": True,
        },
        "next_step": "maintain_no_go_or_manual_publish_go_redecision",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return report


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 9-4 Publish GO Redecision and NO_GO Maintenance Overall Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase9_4_overall_status: {report['phase9_4_overall_status']}",
        f"- aggregation_scope: {report['aggregation_scope']}",
        "",
        "## Current Confirmed State",
        "",
        f"- phase9_2_decision: {report['phase9_2_decision']}",
        f"- wordpress_draft_id: {report['wordpress_draft_id']}",
        f"- target_draft_status: {report['target_draft_status']}",
        f"- publish_candidate_unlocked_for_operator: {report['publish_candidate_unlocked_for_operator']}",
        f"- wordpress_publish_execution: {report['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- production_status: {report['production_status']}",
        "",
        "## Route Readiness",
        "",
        f"- publish_go_redecision_route_ready: {report['route_readiness']['publish_go_redecision_route_ready']}",
        f"- manual_publish_runbook_ready: {report['route_readiness']['manual_publish_runbook_ready']}",
        f"- input_gate_ready: {report['route_readiness']['input_gate_ready']}",
        f"- keep_no_go_confirmation_ready: {report['route_readiness']['keep_no_go_confirmation_ready']}",
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
        "## Prohibited Actions (Maintained)",
        "",
        "- WordPress publish/update/delete/export: NO_GO",
        "- GitHub Actions trigger: NO_GO",
        "- Slack production notification: NO_GO",
        "- VPS self builder execution: NO_GO",
        "",
        "## Next Step",
        "",
        report["next_step"],
        "",
    ]
    return "\n".join(lines)


def generate_report(
    input_9_1: Path,
    input_9_2: Path,
    input_9_3: Path,
    output_json: Path,
    output_md: Path,
) -> dict:
    for p in [input_9_1, input_9_2, input_9_3]:
        if not p.exists():
            return abort_result(f"required input not found: {p}", output_json)

    p91 = load_json(input_9_1)
    p92 = load_json(input_9_2)
    p93 = load_json(input_9_3)

    err = validate_inputs(p91, p92, p93)
    if err:
        return abort_result(err, output_json)

    report = build_report(
        p91,
        p92,
        p93,
        {
            "phase9_1": input_9_1,
            "phase9_2": input_9_2,
            "phase9_3": input_9_3,
        },
    )

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    result = {
        "package_type": "phase9_4_publish_go_redecision_no_go_maintenance_overall_report_result",
        "phase": "Phase 9-4",
        "status": report["status"],
        "phase9_4_overall_status": report["phase9_4_overall_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": normalize_path(output_json),
        "markdown_output": normalize_path(output_md),
        "phase9_2_decision": report["phase9_2_decision"],
        "publish_candidate_unlocked_for_operator": report["publish_candidate_unlocked_for_operator"],
        "wordpress_publish_execution": report["wordpress_publish_execution"],
        "wordpress_write_executed": report["wordpress_write_executed"],
        "next_step": report["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 9-4 NO_GO maintenance overall report")
    parser.add_argument("--input-9-1", type=Path, default=DEFAULT_INPUT_9_1)
    parser.add_argument("--input-9-2", type=Path, default=DEFAULT_INPUT_9_2)
    parser.add_argument("--input-9-3", type=Path, default=DEFAULT_INPUT_9_3)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_9_1, args.input_9_2, args.input_9_3, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
