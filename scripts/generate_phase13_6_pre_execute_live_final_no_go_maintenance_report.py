#!/usr/bin/env python3
"""Generate Phase 13-6 report for pre execute-live final NO_GO maintenance."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_13_5 = (
    LOG_DIR / "phase13_5_unlock_candidate_judgment_on_go_conditions_design_report.json"
)
DEFAULT_OUTPUT_JSON = LOG_DIR / "phase13_6_pre_execute_live_final_no_go_maintenance_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase13_6_pre_execute_live_final_no_go_maintenance_report.md"

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
        "package_type": "phase13_6_pre_execute_live_final_no_go_maintenance_report",
        "phase": "Phase 13-6",
        "status": "ABORT",
        "reason": reason,
        "maintenance_report_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase13_5(source: dict) -> str | None:
    if source.get("phase") != "Phase 13-5":
        return "phase13_5 input phase must be Phase 13-5"
    if source.get("status") != "PASS":
        return "phase13_5 status must be PASS"
    if source.get("phase13_5_judgment_design_status") != "PASS":
        return "phase13_5_judgment_design_status must be PASS"
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


def build_report(source: dict, input_path: Path) -> dict:
    return {
        "package_type": "phase13_6_pre_execute_live_final_no_go_maintenance_report",
        "phase": "Phase 13-6",
        "title": "Phase 13-6 Pre Execute Live Final NO-GO Maintenance Report",
        "status": "PASS",
        "phase13_6_maintenance_status": "PASS",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "still_forbidden": STILL_FORBIDDEN,
        "summary": {
            "phase13_pre_execute_live_no_go_maintenance_completed": True,
            "publish_still_not_executed": True,
            "no_go_boundary_maintained": True,
        },
        "next_step": "phase13_7_phase13_mid_block_overall_check",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 13-6 Pre Execute Live Final NO-GO Maintenance Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"- status: {report['status']}",
        f"- phase13_6_maintenance_status: {report['phase13_6_maintenance_status']}",
        f"- next_step: {report['next_step']}",
        "",
    ]
    return "\n".join(lines)


def generate_report(input_13_5: Path, output_json: Path, output_md: Path) -> dict:
    if not input_13_5.exists():
        return abort_result(f"required input not found: {input_13_5}", output_json)

    source = load_json(input_13_5)
    err = validate_phase13_5(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_13_5)
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase13_6_pre_execute_live_final_no_go_maintenance_report_result",
        "phase": "Phase 13-6",
        "status": report["status"],
        "phase13_6_maintenance_status": report["phase13_6_maintenance_status"],
        "report_generated": True,
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
        description="Generate Phase 13-6 pre execute-live final NO-GO maintenance report"
    )
    parser.add_argument("--input-13-5", type=Path, default=DEFAULT_INPUT_13_5)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_13_5, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
