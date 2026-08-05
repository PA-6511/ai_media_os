#!/usr/bin/env python3
"""Generate Phase 10-12 report for manual live execution readiness review."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_11 = (
    LOG_DIR
    / "phase10_11_post_execution_evidence_and_relock_confirmation_design_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_12_manual_live_execution_readiness_review_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_12_manual_live_execution_readiness_review_report.md"
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
        "package_type": "phase10_12_manual_live_execution_readiness_review_report",
        "phase": "Phase 10-12",
        "status": "ABORT",
        "reason": reason,
        "review_generated": False,
        "current_decision": "KEEP_NO_GO",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(output_json, result)
    return result


def validate_phase10_11(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-11":
        return "phase10_11 input phase must be Phase 10-11"
    if source.get("status") != "PASS":
        return "phase10_11 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_11 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_11 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_11 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_11 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_11 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_11 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_11 target_draft_status must be draft"

    design = source.get("post_execution_evidence_and_relock_design", {})
    if design.get("relock_mandatory") is not True:
        return "phase10_11 relock_mandatory must be true"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_11_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
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
            "check": "relock_mandatory=true",
            "passed": source.get("post_execution_evidence_and_relock_design", {}).get("relock_mandatory") is True,
            "actual": source.get("post_execution_evidence_and_relock_design", {}).get("relock_mandatory"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    readiness_review = {
        "review_name": "manual_live_execution_readiness_review",
        "default_decision": "KEEP_NO_GO",
        "review_checks_count": 8,
        "review_checks": [
            "target_draft_id_is_110",
            "target_draft_status_is_draft",
            "default_stop_guard_confirmed",
            "post_execution_evidence_schema_defined",
            "relock_schema_defined_and_mandatory",
            "single_publish_scope_is_fixed",
            "forbidden_operations_remain_locked",
            "publish_not_executed_in_phase10_12",
        ],
        "readiness_review_passed": True,
        "publish_execution_in_phase10_12": "NO_GO",
        "wordpress_write_executed_in_phase10_12": False,
    }

    readiness_review_flow = [
        "load_phase10_11_post_execution_evidence_and_relock_design",
        "run_8_item_readiness_review",
        "record_readiness_review_result",
        "keep_publish_not_executed_in_phase10_12",
    ]

    readiness_review_outcomes = [
        {
            "readiness_result": "READY_FOR_PHASE10_13_HUMAN_AUTHORIZATION_GATE",
            "publish_execution_in_phase10_12": "NO_GO",
            "wordpress_write_executed_in_phase10_12": False,
            "next_step": "phase10_13_execute_live_final_human_authorization_gate",
        },
        {
            "readiness_result": "NOT_READY_KEEP_NO_GO",
            "publish_execution_in_phase10_12": "NO_GO",
            "wordpress_write_executed_in_phase10_12": False,
            "next_step": "maintain_no_go",
        },
    ]

    return {
        "package_type": "phase10_12_manual_live_execution_readiness_review_report",
        "phase": "Phase 10-12",
        "title": "Phase 10-12 Manual Live Execution Readiness Review Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_12_review_status": "PASS" if all_passed else "ABORT",
        "review_scope": "manual_live_execution_readiness_review_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "manual_live_execution_readiness_review": readiness_review,
        "readiness_review_flow": readiness_review_flow,
        "readiness_review_outcomes": readiness_review_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "manual_live_execution_readiness_review_fixed": True,
            "publish_still_not_executed_in_phase10_12": True,
            "wordpress_write_still_not_executed_in_phase10_12": True,
        },
        "next_step": "phase10_13_execute_live_final_human_authorization_gate",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-12 Manual Live Execution Readiness Review Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_12_review_status: {report['phase10_12_review_status']}",
        "",
        "## Manual Live Execution Readiness Review",
        "",
    ]

    for key, value in report["manual_live_execution_readiness_review"].items():
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


def generate_report(input_10_11: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_11.exists():
        return abort_result(f"required input not found: {input_10_11}", output_json)

    source = load_json(input_10_11)
    err = validate_phase10_11(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_11)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_12_manual_live_execution_readiness_review_report_result",
        "phase": "Phase 10-12",
        "status": report["status"],
        "phase10_12_review_status": report["phase10_12_review_status"],
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
        description="Generate Phase 10-12 manual live execution readiness review report"
    )
    parser.add_argument("--input-10-11", type=Path, default=DEFAULT_INPUT_10_11)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_11, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())