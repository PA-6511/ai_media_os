#!/usr/bin/env python3
"""Generate Phase 10-16 report for overall Phase 10 completion with NO_GO maintained."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

PHASE_INPUT_FILENAMES = {
    "10-1": "phase10_1_publish_go_redecision_reopen_conditions_and_manual_pre_publish_final_lock_design_report.json",
    "10-2": "phase10_2_manual_redecision_input_and_final_lock_validation_design_report.json",
    "10-3": "phase10_3_manual_redecision_record_and_final_lock_gate_design_report.json",
    "10-4": "phase10_4_manual_unlock_candidate_validation_design_report.json",
    "10-5": "phase10_5_manual_unlock_candidate_execution_guard_design_report.json",
    "10-6": "phase10_6_manual_publish_pre_execution_confirmation_design_report.json",
    "10-7": "phase10_7_manual_publish_immediate_pre_execution_go_freeze_decision_design_report.json",
    "10-8": "phase10_8_manual_publish_command_dry_run_payload_validation_report.json",
    "10-9": "phase10_9_single_publish_manual_execution_script_implementation_report.json",
    "10-10": "phase10_10_default_stop_guard_confirmation_report.json",
    "10-11": "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.json",
    "10-12": "phase10_12_manual_live_execution_readiness_review_report.json",
    "10-13": "phase10_13_execute_live_final_human_authorization_gate_report.json",
    "10-14": "phase10_14_pre_execution_final_freeze_release_judgment_report.json",
    "10-15": "phase10_15_pre_publish_no_go_maintenance_completion_report.json",
}

DEFAULT_OUTPUT_JSON = LOG_DIR / "phase10_16_phase10_overall_completion_report.json"
DEFAULT_OUTPUT_MD = LOG_DIR / "phase10_16_phase10_overall_completion_report.md"

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


def build_phase_inputs(logs_dir: Path) -> dict[str, Path]:
    return {
        phase: logs_dir / filename
        for phase, filename in PHASE_INPUT_FILENAMES.items()
    }


def abort_result(reason: str, output_json: Path) -> dict:
    result = {
        "package_type": "phase10_16_phase10_overall_completion_report",
        "phase": "Phase 10-16",
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


def validate_inputs(all_reports: dict[str, dict]) -> str | None:
    for key, report in all_reports.items():
        if report.get("status") != "PASS":
            return f"phase{key} status must be PASS"

    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]:
        report = all_reports[key]
        if report.get("current_decision") != "KEEP_NO_GO":
            return f"phase{key} current_decision must be KEEP_NO_GO"
        if report.get("publish_candidate_unlocked_for_operator") is not False:
            return f"phase{key} publish_candidate_unlocked_for_operator must be false"
        if report.get("wordpress_publish_execution") != "NO_GO":
            return f"phase{key} wordpress_publish_execution must be NO_GO"
        if report.get("wordpress_write_executed") is not False:
            return f"phase{key} wordpress_write_executed must be false"
        if report.get("production_status") != "NO_GO":
            return f"phase{key} production_status must be NO_GO"

    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]:
        report = all_reports[key]
        if report.get("wordpress_draft_id") != 110:
            return f"phase{key} wordpress_draft_id must be 110"
        if report.get("target_draft_status") != "draft":
            return f"phase{key} target_draft_status must be draft"

    return None


def build_checks(all_reports: dict[str, dict]) -> list[dict]:
    checks: list[dict] = []

    for key in [
        "10-1",
        "10-2",
        "10-3",
        "10-4",
        "10-5",
        "10-6",
        "10-7",
        "10-8",
        "10-9",
        "10-10",
        "10-11",
        "10-12",
        "10-13",
        "10-14",
        "10-15",
    ]:
        checks.append(
            {
                "check": f"phase{key}_status=PASS",
                "passed": all_reports[key].get("status") == "PASS",
                "actual": all_reports[key].get("status"),
            }
        )

    checks.extend(
        [
            {
                "check": "phase10_12_13_14_15_pass",
                "passed": all(
                    all_reports[key].get("status") == "PASS"
                    for key in ["10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {key: all_reports[key].get("status") for key in ["10-12", "10-13", "10-14", "10-15"]},
            },
            {
                "check": "current_decision=KEEP_NO_GO_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("current_decision") == "KEEP_NO_GO"
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("current_decision")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
            {
                "check": "publish_candidate_unlocked_for_operator=false_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("publish_candidate_unlocked_for_operator") is False
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("publish_candidate_unlocked_for_operator")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
            {
                "check": "wordpress_publish_execution=NO_GO_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("wordpress_publish_execution") == "NO_GO"
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("wordpress_publish_execution")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
            {
                "check": "wordpress_write_executed=false_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("wordpress_write_executed") is False
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("wordpress_write_executed")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
            {
                "check": "production_status=NO_GO_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("production_status") == "NO_GO"
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("production_status")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
            {
                "check": "target_draft_status=draft_in_10_9_to_10_15",
                "passed": all(
                    all_reports[key].get("target_draft_status") == "draft"
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                ),
                "actual": {
                    key: all_reports[key].get("target_draft_status")
                    for key in ["10-9", "10-10", "10-11", "10-12", "10-13", "10-14", "10-15"]
                },
            },
        ]
    )

    return checks


def build_report(all_reports: dict[str, dict]) -> dict:
    checks = build_checks(all_reports)
    all_passed = all(c["passed"] for c in checks)

    phase_statuses = {
        phase: all_reports[phase].get("status")
        for phase in [
            "10-1",
            "10-2",
            "10-3",
            "10-4",
            "10-5",
            "10-6",
            "10-7",
            "10-8",
            "10-9",
            "10-10",
            "10-11",
            "10-12",
            "10-13",
            "10-14",
            "10-15",
        ]
    }

    return {
        "package_type": "phase10_16_phase10_overall_completion_report",
        "phase": "Phase 10-16",
        "title": "Phase 10-16 Phase 10 Overall Completion Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_overall_status": "PASS" if all_passed else "ABORT",
        "phase_range": "Phase 10-1 through Phase 10-15",
        "reason": (
            "phase10-1 through phase10-15 completed; publish route prepared while KEEP_NO_GO and NO_GO are maintained"
            if all_passed
            else "phase10 overall verification failed"
        ),
        "phase_statuses": phase_statuses,
        "current_decision": "KEEP_NO_GO",
        "phase10_14_final_judgment": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "all_checks_passed": all_passed,
        "summary": {
            "phase10_12_to_10_14_passed": all(
                all_reports[key].get("status") == "PASS"
                for key in ["10-12", "10-13", "10-14"]
            ),
            "phase10_15_no_go_maintenance_passed": all_reports["10-15"].get("status") == "PASS",
            "publish_still_not_executed": True,
            "publish_candidate_still_locked": True,
        },
        "next_step": "maintain_no_go_until_separate_manual_execute_live_authorization",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-16 Phase 10 Overall Completion Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_overall_status: {report['phase10_overall_status']}",
        f"- phase_range: {report['phase_range']}",
        "",
        "## Confirmed Final State",
        "",
        f"- current_decision: {report['current_decision']}",
        f"- publish_candidate_unlocked_for_operator: {report['publish_candidate_unlocked_for_operator']}",
        f"- wordpress_publish_execution: {report['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- production_status: {report['production_status']}",
        f"- target_draft_status: {report['target_draft_status']}",
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


def generate_report(phase_inputs: dict[str, Path], output_json: Path, output_md: Path) -> dict:
    for _, path in phase_inputs.items():
        if not path.exists():
            return abort_result(f"required input not found: {path}", output_json)

    all_reports = {phase: load_json(path) for phase, path in phase_inputs.items()}

    err = validate_inputs(all_reports)
    if err:
        return abort_result(err, output_json)

    report = build_report(all_reports)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_16_phase10_overall_completion_report_result",
        "phase": "Phase 10-16",
        "status": report["status"],
        "phase10_overall_status": report["phase10_overall_status"],
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
        description="Generate Phase 10-16 overall completion report"
    )
    parser.add_argument("--logs-dir", type=Path, default=LOG_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(
        build_phase_inputs(args.logs_dir),
        args.output_json,
        args.output_md,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
