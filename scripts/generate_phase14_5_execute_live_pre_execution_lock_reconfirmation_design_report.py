#!/usr/bin/env python3
"""Generate Phase 14-5 report for execute-live pre-execution lock reconfirmation design."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_14_4 = (
    LOG_DIR / "phase14_4_execute_live_candidate_unlock_judgment_record_design_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR / "phase14_5_execute_live_pre_execution_lock_reconfirmation_design_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR / "phase14_5_execute_live_pre_execution_lock_reconfirmation_design_report.md"
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
        "package_type": "phase14_5_execute_live_pre_execution_lock_reconfirmation_design_report",
        "phase": "Phase 14-5",
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


def validate_phase14_4(source: dict) -> str | None:
    if source.get("phase") != "Phase 14-4":
        return "phase14_4 input phase must be Phase 14-4"
    if source.get("status") != "PASS":
        return "phase14_4 status must be PASS"
    if source.get("phase14_4_design_status") != "PASS":
        return "phase14_4_design_status must be PASS"
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
        "package_type": "phase14_5_execute_live_pre_execution_lock_reconfirmation_design_report",
        "phase": "Phase 14-5",
        "title": "Phase 14-5 Execute Live Pre Execution Lock Reconfirmation Design Report",
        "status": "PASS",
        "phase14_5_design_status": "PASS",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "pre_execution_lock_reconfirmation_design": {
            "recheck_items_defined": True,
            "lock_state_must_be_false_for_unlock": True,
            "default_locked_state": True,
            "design_only": True,
        },
        "still_forbidden": STILL_FORBIDDEN,
        "summary": {
            "pre_execution_lock_reconfirmation_design_completed": True,
            "publish_still_not_executed": True,
            "no_go_boundary_maintained": True,
        },
        "next_step": "phase14_6_execute_live_pre_command_final_dry_run_audit",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 14-5 Execute Live Pre Execution Lock Reconfirmation Design Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"- status: {report['status']}",
        f"- phase14_5_design_status: {report['phase14_5_design_status']}",
        f"- next_step: {report['next_step']}",
        "",
    ]
    return "\n".join(lines)


def generate_report(input_14_4: Path, output_json: Path, output_md: Path) -> dict:
    if not input_14_4.exists():
        return abort_result(f"required input not found: {input_14_4}", output_json)

    source = load_json(input_14_4)
    err = validate_phase14_4(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_14_4)
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase14_5_execute_live_pre_execution_lock_reconfirmation_design_report_result",
        "phase": "Phase 14-5",
        "status": report["status"],
        "phase14_5_design_status": report["phase14_5_design_status"],
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
        description="Generate Phase 14-5 execute-live pre-execution lock reconfirmation design report"
    )
    parser.add_argument("--input-14-4", type=Path, default=DEFAULT_INPUT_14_4)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_14_4, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
