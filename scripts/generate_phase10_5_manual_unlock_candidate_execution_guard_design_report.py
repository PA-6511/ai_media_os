#!/usr/bin/env python3
"""Generate Phase 10-5 design report for manual unlock candidate execution guard."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_4 = (
    LOG_DIR
    / "phase10_4_manual_unlock_candidate_validation_design_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_5_manual_unlock_candidate_execution_guard_design_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_5_manual_unlock_candidate_execution_guard_design_report.md"
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
        "package_type": "phase10_5_manual_unlock_candidate_execution_guard_design_report",
        "phase": "Phase 10-5",
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


def validate_phase10_4(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-4":
        return "phase10_4 input phase must be Phase 10-4"
    if source.get("status") != "PASS":
        return "phase10_4 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_4 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_4 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_4 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_4 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_4 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_4 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_4 target_draft_status must be draft"

    validation_design = source.get("manual_unlock_candidate_validation_design", {})
    if validation_design.get("validation_checks_count") != 8:
        return "phase10_4 validation_checks_count must be 8"
    if validation_design.get("required_approval_token") != "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY":
        return "phase10_4 required_approval_token mismatch"
    if validation_design.get("token_expiry_minutes") != 30:
        return "phase10_4 token_expiry_minutes must be 30"
    if validation_design.get("max_publish_count") != 1:
        return "phase10_4 max_publish_count must be 1"

    outcomes = source.get("unlock_candidate_validation_outcomes", [])
    has_valid_candidate = any(
        row.get("validation_result") == "VALID_UNLOCK_CANDIDATE"
        and row.get("publish_execution_in_phase10_4") == "NO_GO"
        and row.get("wordpress_write_executed_in_phase10_4") is False
        for row in outcomes
    )
    if not has_valid_candidate:
        return "phase10_4 outcomes must include VALID_UNLOCK_CANDIDATE with NO_GO and write false"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_4_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
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
            "check": "validation_checks_count=8",
            "passed": source.get("manual_unlock_candidate_validation_design", {}).get("validation_checks_count") == 8,
            "actual": source.get("manual_unlock_candidate_validation_design", {}).get("validation_checks_count"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    execution_guard_design = {
        "scope": "manual_unlock_candidate_execution_guard_design_only",
        "prerequisite_phase": "Phase 10-4",
        "required_validation_result": "VALID_UNLOCK_CANDIDATE",
        "required_decision": "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
        "required_token": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
        "token_expiry_minutes": 30,
        "max_publish_count": 1,
        "target_scope": "draft_to_publish_only",
        "required_target_draft_id": 110,
        "required_target_draft_status": "draft",
        "relock_required_after_attempt": True,
        "execution_guard_checks_count": 5,
        "execution_guard_checks": [
            "one_publish_only",
            "draft_to_publish_only",
            "token_exact_and_not_expired",
            "within_30_minutes",
            "relock_mandatory_after_attempt",
        ],
        "publish_execution_in_phase10_5": "NO_GO",
        "wordpress_write_executed_in_phase10_5": False,
    }

    execution_guard_flow = [
        "load_phase10_4_validation_result",
        "verify_guard_checks_5_items",
        "mark_unlock_candidate_as_execution_guard_ready_or_reject",
        "keep_publish_not_executed_in_phase10_5",
    ]

    execution_guard_outcomes = [
        {
            "guard_result": "READY_FOR_FUTURE_MANUAL_EXECUTION_CANDIDATE",
            "publish_execution_in_phase10_5": "NO_GO",
            "wordpress_write_executed_in_phase10_5": False,
            "next_step": "phase10_6_manual_publish_pre_execution_confirmation_design",
        },
        {
            "guard_result": "REJECT_KEEP_LOCKED",
            "publish_execution_in_phase10_5": "NO_GO",
            "wordpress_write_executed_in_phase10_5": False,
            "next_step": "maintain_no_go",
        },
        {
            "guard_result": "REQUEST_FIX_REQUIRED",
            "publish_execution_in_phase10_5": "NO_GO",
            "wordpress_write_executed_in_phase10_5": False,
            "next_step": "apply_requested_fix_before_next_redecision",
        },
        {
            "guard_result": "ABORT",
            "publish_execution_in_phase10_5": "NO_GO",
            "wordpress_write_executed_in_phase10_5": False,
            "next_step": "abort_and_stop",
        },
    ]

    return {
        "package_type": "phase10_5_manual_unlock_candidate_execution_guard_design_report",
        "phase": "Phase 10-5",
        "title": "Phase 10-5 Manual Unlock Candidate Execution Guard Design Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_5_design_status": "PASS" if all_passed else "ABORT",
        "design_scope": "manual_unlock_candidate_execution_guard_design_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "execution_guard_design": execution_guard_design,
        "execution_guard_flow": execution_guard_flow,
        "execution_guard_outcomes": execution_guard_outcomes,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "execution_guard_design_fixed": True,
            "single_publish_and_draft_only_guard_defined": True,
            "publish_still_not_executed_in_phase10_5": True,
            "wordpress_write_still_not_executed_in_phase10_5": True,
        },
        "next_step": "phase10_6_manual_publish_pre_execution_confirmation_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-5 Manual Unlock Candidate Execution Guard Design Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_5_design_status: {report['phase10_5_design_status']}",
        f"- design_scope: {report['design_scope']}",
        "",
        "## Current Confirmed State",
        "",
        f"- current_decision: {report['current_decision']}",
        f"- wordpress_draft_id: {report['wordpress_draft_id']}",
        f"- target_draft_status: {report['target_draft_status']}",
        f"- publish_candidate_unlocked_for_operator: {report['publish_candidate_unlocked_for_operator']}",
        f"- wordpress_publish_execution: {report['wordpress_publish_execution']}",
        f"- wordpress_write_executed: {report['wordpress_write_executed']}",
        f"- production_status: {report['production_status']}",
        "",
        "## Execution Guard Design",
        "",
    ]

    for key, value in report["execution_guard_design"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Execution Guard Flow",
        "",
    ]

    for step in report["execution_guard_flow"]:
        lines.append(f"- {step}")

    lines += [
        "",
        "## Execution Guard Outcomes",
        "",
        "| Guard Result | Publish In Phase 10-5 | WordPress Write In Phase 10-5 | Next Step |",
        "|---|---|---|---|",
    ]

    for row in report["execution_guard_outcomes"]:
        lines.append(
            "| "
            f"{row['guard_result']} | {row['publish_execution_in_phase10_5']} | "
            f"{row['wordpress_write_executed_in_phase10_5']} | {row['next_step']} |"
        )

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
        "## Still Forbidden",
        "",
    ]

    for item in report["still_forbidden"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Next Step",
        "",
        report["next_step"],
        "",
    ]

    return "\n".join(lines)


def generate_report(input_10_4: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_4.exists():
        return abort_result(f"required input not found: {input_10_4}", output_json)

    source = load_json(input_10_4)
    err = validate_phase10_4(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_4)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_5_manual_unlock_candidate_execution_guard_design_report_result",
        "phase": "Phase 10-5",
        "status": report["status"],
        "phase10_5_design_status": report["phase10_5_design_status"],
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
        description="Generate Phase 10-5 manual unlock candidate execution guard design report"
    )
    parser.add_argument("--input-10-4", type=Path, default=DEFAULT_INPUT_10_4)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_4, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
