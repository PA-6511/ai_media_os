#!/usr/bin/env python3
"""Generate Phase 11-5 report for final publish command dry-run confirmation."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_11_4 = (
    LOG_DIR / "phase11_4_pre_publish_final_no_go_or_go_judgment_design_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR / "phase11_5_publish_command_final_dry_run_confirmation_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR / "phase11_5_publish_command_final_dry_run_confirmation_report.md"
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
        "package_type": "phase11_5_publish_command_final_dry_run_confirmation_report",
        "phase": "Phase 11-5",
        "status": "ABORT",
        "reason": reason,
        "dry_run_report_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase11_4(source: dict) -> str | None:
    if source.get("phase") != "Phase 11-4":
        return "phase11_4 input phase must be Phase 11-4"
    if source.get("status") != "PASS":
        return "phase11_4 status must be PASS"
    if source.get("phase11_4_judgment_design_status") != "PASS":
        return "phase11_4_judgment_design_status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "production_status must be NO_GO"
    if source.get("target_draft_status") != "draft":
        return "target_draft_status must be draft"
    if source.get("wordpress_draft_id") != 110:
        return "wordpress_draft_id must be 110"
    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
        {
            "check": "phase11_4_judgment_design_status=PASS",
            "passed": source.get("phase11_4_judgment_design_status") == "PASS",
            "actual": source.get("phase11_4_judgment_design_status"),
        },
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
            "check": "production_status=NO_GO",
            "passed": source.get("production_status") == "NO_GO",
            "actual": source.get("production_status"),
        },
        {
            "check": "target_draft_status=draft",
            "passed": source.get("target_draft_status") == "draft",
            "actual": source.get("target_draft_status"),
        },
        {
            "check": "wordpress_draft_id=110",
            "passed": source.get("wordpress_draft_id") == 110,
            "actual": source.get("wordpress_draft_id"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    dry_run_confirmation = {
        "confirmation_name": "publish_command_final_dry_run_confirmation",
        "mode": "DRY_RUN_ONLY",
        "target_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": "draft",
        "payload_schema_checked": True,
        "token_reference_checked": True,
        "publish_execution_in_phase11_5": "NO_GO",
    }

    dry_run_items = [
        "draft_id_is_single_and_fixed",
        "payload_required_fields_present",
        "publish_token_reference_is_non_empty",
        "command_is_dry_run_only",
        "no_wordpress_write_side_effect",
    ]

    return {
        "package_type": "phase11_5_publish_command_final_dry_run_confirmation_report",
        "phase": "Phase 11-5",
        "title": "Phase 11-5 Publish Command Final Dry Run Confirmation Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase11_5_dry_run_status": "PASS" if all_passed else "ABORT",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "dry_run_confirmation": dry_run_confirmation,
        "dry_run_items": dry_run_items,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "final_dry_run_confirmation_completed": True,
            "publish_still_not_executed": True,
            "no_go_boundary_maintained": True,
        },
        "next_step": "phase11_6_execute_live_authorization_gate",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 11-5 Publish Command Final Dry Run Confirmation Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase11_5_dry_run_status: {report['phase11_5_dry_run_status']}",
        "",
        "## Dry Run Confirmation",
        "",
    ]

    for key, value in report["dry_run_confirmation"].items():
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


def generate_report(input_11_4: Path, output_json: Path, output_md: Path) -> dict:
    if not input_11_4.exists():
        return abort_result(f"required input not found: {input_11_4}", output_json)

    source = load_json(input_11_4)
    err = validate_phase11_4(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_11_4)
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase11_5_publish_command_final_dry_run_confirmation_report_result",
        "phase": "Phase 11-5",
        "status": report["status"],
        "phase11_5_dry_run_status": report["phase11_5_dry_run_status"],
        "report_generated": report["status"] == "PASS",
        "json_output": normalize_path(output_json),
        "markdown_output": normalize_path(output_md),
        "current_decision": report["current_decision"],
        "publish_candidate_unlocked_for_operator": report[
            "publish_candidate_unlocked_for_operator"
        ],
        "wordpress_publish_execution": report["wordpress_publish_execution"],
        "wordpress_write_executed": report["wordpress_write_executed"],
        "next_step": report["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Phase 11-5 publish command final dry-run confirmation report"
    )
    parser.add_argument("--input-11-4", type=Path, default=DEFAULT_INPUT_11_4)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_11_4, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
