#!/usr/bin/env python3
"""Generate Phase 15-9 report for overall Phase 15 completion."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUT_FILES = {
    "15-1": "phase15_1_execute_live_resume_conditions_actual_value_check_report.json",
    "15-2": "phase15_2_human_final_go_input_record_file_design_report.json",
    "15-3": "phase15_3_execute_live_final_stop_gate_implementation_report.json",
    "15-4": "phase15_4_human_final_go_record_file_read_gate_report.json",
    "15-5": "phase15_5_execute_live_candidate_unlock_judgment_report.json",
    "15-6": "phase15_6_pre_execute_live_no_go_maintenance_report.json",
    "15-7": "phase15_7_execute_live_candidate_final_confirmation_report.json",
    "15-8": "phase15_8_pre_execute_live_no_go_maintenance_report.json",
}

DEFAULT_OUTPUT_JSON = LOG_DIR / "phase15_9_phase15_overall_completion_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase15_9_phase15_overall_completion_report.md"

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


def build_input_paths(log_dir: Path) -> dict[str, Path]:
    return {phase: log_dir / fname for phase, fname in INPUT_FILES.items()}


def abort_result(reason: str, output_json: Path) -> dict:
    result = {
        "package_type": "phase15_9_phase15_overall_completion_report",
        "phase": "Phase 15-9",
        "status": "ABORT",
        "reason": reason,
        "overall_report_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_inputs(reports: dict[str, dict]) -> str | None:
    for phase, data in reports.items():
        if data.get("status") != "PASS":
            return f"phase{phase} status must be PASS"

    for phase in ["15-1", "15-2", "15-3", "15-4", "15-5", "15-6", "15-7", "15-8"]:
        data = reports[phase]
        if data.get("current_decision") != "KEEP_NO_GO":
            return f"phase{phase} current_decision must be KEEP_NO_GO"
        if data.get("publish_candidate_unlocked_for_operator") is not False:
            return f"phase{phase} publish_candidate_unlocked_for_operator must be false"
        if data.get("wordpress_publish_execution") != "NO_GO":
            return f"phase{phase} wordpress_publish_execution must be NO_GO"
        if data.get("wordpress_write_executed") is not False:
            return f"phase{phase} wordpress_write_executed must be false"
        if data.get("production_status") != "NO_GO":
            return f"phase{phase} production_status must be NO_GO"
        if data.get("target_draft_status") != "draft":
            return f"phase{phase} target_draft_status must be draft"
    return None


def build_report(reports: dict[str, dict]) -> dict:
    return {
        "package_type": "phase15_9_phase15_overall_completion_report",
        "phase": "Phase 15-9",
        "title": "Phase 15-9 Phase 15 Overall Completion Report",
        "status": "PASS",
        "phase15_overall_status": "PASS",
        "phase_range": "Phase 15-1 through Phase 15-8",
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "phase_statuses": {
            phase: reports[phase].get("status")
            for phase in ["15-1", "15-2", "15-3", "15-4", "15-5", "15-6", "15-7", "15-8"]
        },
        "still_forbidden": STILL_FORBIDDEN,
        "summary": {
            "phase15_completed_without_execute_live": True,
            "phase15_no_go_boundary_maintained": True,
            "phase16_start_conditions_can_be_designed": True,
        },
        "next_step": "phase16_1_start_conditions_check_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 15-9 Phase 15 Overall Completion Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"- status: {report['status']}",
        f"- phase15_overall_status: {report['phase15_overall_status']}",
        f"- phase_range: {report['phase_range']}",
        f"- next_step: {report['next_step']}",
        "",
    ]
    return "\n".join(lines)


def generate_report(logs_dir: Path, output_json: Path, output_md: Path) -> dict:
    input_paths = build_input_paths(logs_dir)
    for _, path in input_paths.items():
        if not path.exists():
            return abort_result(f"required input not found: {path}", output_json)

    reports = {phase: load_json(path) for phase, path in input_paths.items()}
    err = validate_inputs(reports)
    if err:
        return abort_result(err, output_json)

    report = build_report(reports)
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase15_9_phase15_overall_completion_report_result",
        "phase": "Phase 15-9",
        "status": report["status"],
        "phase15_overall_status": report["phase15_overall_status"],
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
        description="Generate Phase 15-9 overall completion report"
    )
    parser.add_argument("--logs-dir", type=Path, default=LOG_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.logs_dir, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
