#!/usr/bin/env python3
"""Generate Phase 24-4 report for overall Phase 24 closure."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUT_FILES = {
    "24-1": "phase24_1_phase23_closure_evidence_reconfirmation_report.json",
    "24-2": "phase24_2_execute_live_final_stop_decision_report.json",
    "24-3": "phase24_3_continued_keep_no_go_fixation_report.json",
}

DEFAULT_OUTPUT_JSON = LOG_DIR / "phase24_4_phase24_overall_closure_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase24_4_phase24_overall_closure_report.md"

STILL_FORBIDDEN = [
    "execute_live",
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
        "package_type": "phase24_4_phase24_overall_closure_report",
        "phase": "Phase 24-4",
        "status": "ABORT",
        "reason": reason,
        "phase24_overall_closure_status": "ABORT",
        "overall_report_generated": False,
        "execute_live_executed": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "target_draft_status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_inputs(reports: dict[str, dict]) -> str | None:
    for phase, data in reports.items():
        if data.get("status") != "PASS":
            return f"phase{phase} status must be PASS"

    for phase in ["24-1", "24-2", "24-3"]:
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
        if data.get("execute_live_executed") is not False:
            return f"phase{phase} execute_live_executed must be false"
    return None


def build_report(reports: dict[str, dict]) -> dict:
    return {
        "package_type": "phase24_4_phase24_overall_closure_report",
        "phase": "Phase 24-4",
        "title": "Phase 24-4 Phase 24 Overall Closure Report",
        "status": "PASS",
        "phase24_overall_closure_status": "PASS",
        "phase24_overall_status": "PASS",
        "phase_range": "Phase 24-1 through Phase 24-3",
        "execute_live_executed": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "target_draft_status": "draft",
        "phase_statuses": {
            phase: reports[phase].get("status") for phase in ["24-1", "24-2", "24-3"]
        },
        "still_forbidden": STILL_FORBIDDEN,
        "summary": {
            "phase24_closed_without_execute_live": True,
            "phase24_no_go_boundary_maintained": True,
            "phase25_can_start_from_formal_closure": True,
        },
        "next_step": "phase25_readiness_review_or_start_conditions",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 24-4 Phase 24 Overall Closure Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"- status: {report['status']}",
        f"- phase24_overall_closure_status: {report['phase24_overall_closure_status']}",
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
        "package_type": "phase24_4_phase24_overall_closure_report_result",
        "phase": "Phase 24-4",
        "status": report["status"],
        "phase24_overall_closure_status": report["phase24_overall_closure_status"],
        "phase24_overall_status": report["phase24_overall_status"],
        "report_generated": True,
        "json_output": normalize_path(output_json),
        "markdown_output": normalize_path(output_md),
        "execute_live_executed": report["execute_live_executed"],
        "current_decision": report["current_decision"],
        "publish_candidate_unlocked_for_operator": report["publish_candidate_unlocked_for_operator"],
        "wordpress_publish_execution": report["wordpress_publish_execution"],
        "wordpress_write_executed": report["wordpress_write_executed"],
        "production_status": report["production_status"],
        "target_draft_status": report["target_draft_status"],
        "next_step": report["next_step"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 24-4 overall closure report")
    parser.add_argument("--logs-dir", type=Path, default=LOG_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.logs_dir, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())