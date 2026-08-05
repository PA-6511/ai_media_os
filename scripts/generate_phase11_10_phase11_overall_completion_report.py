#!/usr/bin/env python3
"""Generate Phase 11-10 report for overall Phase 11 completion."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

INPUT_FILES = {
    "11-1": "phase11_1_publish_redecision_route_restart_design_report.json",
    "11-2": "phase11_2_pre_production_audit_design_report.json",
    "11-3": "phase11_3_single_publish_final_execution_plan_report.json",
    "11-4": "phase11_4_pre_publish_final_no_go_or_go_judgment_design_report.json",
    "11-5": "phase11_5_publish_command_final_dry_run_confirmation_report.json",
    "11-6": "phase11_6_execute_live_authorization_gate_report.json",
    "11-7": "phase11_7_pre_execution_final_freeze_release_judgment_report.json",
    "11-8": "phase11_8_post_execution_evidence_and_relock_final_confirmation_report.json",
    "11-9": "phase11_9_pre_publish_no_go_maintenance_report.json",
}

DEFAULT_OUTPUT_JSON = LOG_DIR / "phase11_10_phase11_overall_completion_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase11_10_phase11_overall_completion_report.md"

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
        "package_type": "phase11_10_phase11_overall_completion_report",
        "phase": "Phase 11-10",
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

    for phase in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]:
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


def build_checks(reports: dict[str, dict]) -> list[dict]:
    checks = []
    for phase in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]:
        checks.append(
            {
                "check": f"phase{phase}_status=PASS",
                "passed": reports[phase].get("status") == "PASS",
                "actual": reports[phase].get("status"),
            }
        )

    checks.extend(
        [
            {
                "check": "current_decision=KEEP_NO_GO_in_11_1_to_11_9",
                "passed": all(
                    reports[p].get("current_decision") == "KEEP_NO_GO"
                    for p in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]
                ),
                "actual": {
                    p: reports[p].get("current_decision")
                    for p in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]
                },
            },
            {
                "check": "publish_candidate_unlocked_for_operator=false_in_11_1_to_11_9",
                "passed": all(
                    reports[p].get("publish_candidate_unlocked_for_operator") is False
                    for p in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]
                ),
                "actual": {
                    p: reports[p].get("publish_candidate_unlocked_for_operator")
                    for p in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]
                },
            },
        ]
    )
    return checks


def build_report(reports: dict[str, dict]) -> dict:
    checks = build_checks(reports)
    all_passed = all(c["passed"] for c in checks)

    return {
        "package_type": "phase11_10_phase11_overall_completion_report",
        "phase": "Phase 11-10",
        "title": "Phase 11-10 Phase 11 Overall Completion Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase11_overall_status": "PASS" if all_passed else "ABORT",
        "phase_range": "Phase 11-1 through Phase 11-9",
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "phase_statuses": {
            phase: reports[phase].get("status")
            for phase in ["11-1", "11-2", "11-3", "11-4", "11-5", "11-6", "11-7", "11-8", "11-9"]
        },
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "all_checks_passed": all_passed,
        "summary": {
            "phase11_completed_without_publish_execution": True,
            "phase11_no_go_boundary_maintained": True,
            "phase12_start_gate_can_be_designed": True,
        },
        "next_step": "phase11_11_phase12_start_conditions_check_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 11-10 Phase 11 Overall Completion Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase11_overall_status: {report['phase11_overall_status']}",
        f"- phase_range: {report['phase_range']}",
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
        "package_type": "phase11_10_phase11_overall_completion_report_result",
        "phase": "Phase 11-10",
        "status": report["status"],
        "phase11_overall_status": report["phase11_overall_status"],
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
        description="Generate Phase 11-10 overall completion report"
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
