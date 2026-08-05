#!/usr/bin/env python3
"""Generate Phase 24-3 report for continued KEEP_NO_GO fixation."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_24_2 = LOG_DIR / "phase24_2_execute_live_final_stop_decision_report.json"
DEFAULT_OUTPUT_JSON = LOG_DIR / "phase24_3_continued_keep_no_go_fixation_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase24_3_continued_keep_no_go_fixation_report.md"

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


def abort_result(reason: str, output_json: Path) -> dict:
    result = {
        "package_type": "phase24_3_continued_keep_no_go_fixation_report",
        "phase": "Phase 24-3",
        "status": "ABORT",
        "reason": reason,
        "phase24_3_fixation_status": "ABORT",
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


def validate_phase24_2(source: dict) -> str | None:
    if source.get("phase") != "Phase 24-2":
        return "phase24_2 input phase must be Phase 24-2"
    if source.get("status") != "PASS":
        return "phase24_2 status must be PASS"
    if source.get("phase24_2_stop_decision_status") != "PASS":
        return "phase24_2_stop_decision_status must be PASS"
    if source.get("execute_live_executed") is not False:
        return "execute_live_executed must be false"
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
    return None


def build_report(source: dict, input_path: Path) -> dict:
    return {
        "package_type": "phase24_3_continued_keep_no_go_fixation_report",
        "phase": "Phase 24-3",
        "title": "Phase 24-3 Continued KEEP_NO_GO Fixation Report",
        "status": "PASS",
        "phase24_3_fixation_status": "PASS",
        "source_report": normalize_path(input_path),
        "execute_live_executed": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "target_draft_status": source.get("target_draft_status"),
        "continued_keep_no_go_fixation": {
            "final_stop_decision_verified": True,
            "keep_no_go_locked": True,
            "execute_live_still_not_executed": True,
            "publish_and_write_paths_still_blocked": True,
        },
        "still_forbidden": STILL_FORBIDDEN,
        "summary": {
            "continued_keep_no_go_fixed": True,
            "execute_live_still_not_executed": True,
            "no_go_boundary_maintained": True,
        },
        "next_step": "phase24_closure_or_future_readiness_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 24-3 Continued KEEP_NO_GO Fixation Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        f"- status: {report['status']}",
        f"- phase24_3_fixation_status: {report['phase24_3_fixation_status']}",
        f"- next_step: {report['next_step']}",
        "",
    ]
    return "\n".join(lines)


def generate_report(input_24_2: Path, output_json: Path, output_md: Path) -> dict:
    if not input_24_2.exists():
        return abort_result(f"required input not found: {input_24_2}", output_json)

    source = load_json(input_24_2)
    err = validate_phase24_2(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_24_2)
    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase24_3_continued_keep_no_go_fixation_report_result",
        "phase": "Phase 24-3",
        "status": report["status"],
        "phase24_3_fixation_status": report["phase24_3_fixation_status"],
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
    parser = argparse.ArgumentParser(description="Generate Phase 24-3 continued KEEP_NO_GO fixation report")
    parser.add_argument("--input-24-2", type=Path, default=DEFAULT_INPUT_24_2)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_24_2, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())