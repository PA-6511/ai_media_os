#!/usr/bin/env python3
"""Generate Phase 10-3 design report for manual redecision record and final lock gate."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "exchange" / "logs"

DEFAULT_INPUT_10_2 = (
    LOG_DIR
    / "phase10_2_manual_redecision_input_and_final_lock_validation_design_report.json"
)
DEFAULT_OUTPUT_JSON = (
    LOG_DIR
    / "phase10_3_manual_redecision_record_and_final_lock_gate_design_report.json"
)
DEFAULT_OUTPUT_MD = (
    LOG_DIR
    / "phase10_3_manual_redecision_record_and_final_lock_gate_design_report.md"
)

ALLOWED_MANUAL_DECISIONS = [
    "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
    "KEEP_NO_GO",
    "REQUEST_FIX",
    "ABORT",
]

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
        "package_type": "phase10_3_manual_redecision_record_and_final_lock_gate_design_report",
        "phase": "Phase 10-3",
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


def validate_phase10_2(source: dict) -> str | None:
    if source.get("phase") != "Phase 10-2":
        return "phase10_2 input phase must be Phase 10-2"
    if source.get("status") != "PASS":
        return "phase10_2 input status must be PASS"
    if source.get("current_decision") != "KEEP_NO_GO":
        return "phase10_2 current_decision must be KEEP_NO_GO"
    if source.get("publish_candidate_unlocked_for_operator") is not False:
        return "phase10_2 publish_candidate_unlocked_for_operator must be false"
    if source.get("wordpress_publish_execution") != "NO_GO":
        return "phase10_2 wordpress_publish_execution must be NO_GO"
    if source.get("wordpress_write_executed") is not False:
        return "phase10_2 wordpress_write_executed must be false"
    if source.get("production_status") != "NO_GO":
        return "phase10_2 production_status must be NO_GO"
    if source.get("wordpress_draft_id") != 110:
        return "phase10_2 wordpress_draft_id must be 110"
    if source.get("target_draft_status") != "draft":
        return "phase10_2 target_draft_status must be draft"

    manual_input = source.get("manual_redecision_input_design", {})
    if manual_input.get("allowed_decisions") != ALLOWED_MANUAL_DECISIONS:
        return "phase10_2 allowed_decisions mismatch"

    lock_design = source.get("final_lock_validation_design", {})
    if lock_design.get("wordpress_publish_execution_in_phase10_2") != "NO_GO":
        return "phase10_2 final lock design must keep publish NO_GO"
    if lock_design.get("wordpress_write_executed_in_phase10_2") is not False:
        return "phase10_2 final lock design must keep write false"

    return None


def build_checks(source: dict) -> list[dict]:
    return [
        {"check": "phase10_2_status=PASS", "passed": source.get("status") == "PASS", "actual": source.get("status")},
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
            "check": "wordpress_draft_id=110",
            "passed": source.get("wordpress_draft_id") == 110,
            "actual": source.get("wordpress_draft_id"),
        },
        {
            "check": "target_draft_status=draft",
            "passed": source.get("target_draft_status") == "draft",
            "actual": source.get("target_draft_status"),
        },
    ]


def build_report(source: dict, input_path: Path) -> dict:
    checks = build_checks(source)
    all_passed = all(c["passed"] for c in checks)

    manual_redecision_record_design = {
        "record_file_path": "exchange/human_review/phase10_3_manual_redecision_record.json",
        "required_fields": [
            "phase",
            "mode",
            "execution",
            "decision",
            "reviewer",
            "reviewer_is_human",
            "reviewed_at",
            "reason",
            "target_draft_id",
            "target_draft_status",
            "approval_token",
            "token_constraints",
            "safety_flags",
        ],
        "allowed_decisions": ALLOWED_MANUAL_DECISIONS,
        "target_draft_id_required": 110,
        "target_draft_status_required": "draft",
    }

    final_lock_gate_design = {
        "default_lock_state": "LOCKED",
        "gate_result_values": [
            "UNLOCK_CANDIDATE",
            "KEEP_LOCKED",
            "REQUEST_FIX_REQUIRED",
            "ABORT",
        ],
        "unlock_candidate_condition": "decision_is_GO_PUBLISH_ONE_TIME_MANUAL_ONLY_and_token_valid_and_scope_valid",
        "unlock_candidate_execution_scope": "manual_one_time_publish_only_future_phase",
        "required_token": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
        "token_expiry_minutes": 30,
        "max_publish_count": 1,
        "relock_required_after_attempt": True,
        "publish_execution_in_phase10_3": "NO_GO",
        "wordpress_write_executed_in_phase10_3": False,
    }

    decision_gate_matrix = [
        {
            "decision": "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
            "gate_result": "UNLOCK_CANDIDATE",
            "publish_execution_in_phase10_3": "NO_GO",
            "next_step": "phase10_4_manual_unlock_candidate_validation_design",
        },
        {
            "decision": "KEEP_NO_GO",
            "gate_result": "KEEP_LOCKED",
            "publish_execution_in_phase10_3": "NO_GO",
            "next_step": "maintain_no_go",
        },
        {
            "decision": "REQUEST_FIX",
            "gate_result": "REQUEST_FIX_REQUIRED",
            "publish_execution_in_phase10_3": "NO_GO",
            "next_step": "apply_requested_fix_before_next_redecision",
        },
        {
            "decision": "ABORT",
            "gate_result": "ABORT",
            "publish_execution_in_phase10_3": "NO_GO",
            "next_step": "abort_and_stop",
        },
    ]

    return {
        "package_type": "phase10_3_manual_redecision_record_and_final_lock_gate_design_report",
        "phase": "Phase 10-3",
        "title": "Phase 10-3 Manual Redecision Record and Final Lock Gate Design Report",
        "status": "PASS" if all_passed else "ABORT",
        "phase10_3_design_status": "PASS" if all_passed else "ABORT",
        "design_scope": "manual_redecision_record_and_final_lock_gate_design_only",
        "source_report": normalize_path(input_path),
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": source.get("wordpress_draft_id"),
        "target_draft_status": source.get("target_draft_status"),
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "manual_redecision_record_design": manual_redecision_record_design,
        "final_lock_gate_design": final_lock_gate_design,
        "decision_gate_matrix": decision_gate_matrix,
        "still_forbidden": STILL_FORBIDDEN,
        "validation_checks": checks,
        "validation_passed": all_passed,
        "summary": {
            "manual_redecision_record_design_fixed": True,
            "final_lock_gate_design_fixed": True,
            "go_can_be_unlock_candidate_but_not_executed_in_phase10_3": True,
            "publish_still_not_executed": True,
        },
        "next_step": "phase10_4_manual_unlock_candidate_validation_design",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_markdown(report: dict) -> str:
    lines = [
        "# Phase 10-3 Manual Redecision Record and Final Lock Gate Design Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "## Overall Result",
        "",
        f"- status: {report['status']}",
        f"- phase10_3_design_status: {report['phase10_3_design_status']}",
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
        "## Manual Redecision Record Design",
        "",
        f"- record_file_path: {report['manual_redecision_record_design']['record_file_path']}",
        f"- allowed_decisions: {', '.join(report['manual_redecision_record_design']['allowed_decisions'])}",
        f"- target_draft_id_required: {report['manual_redecision_record_design']['target_draft_id_required']}",
        f"- target_draft_status_required: {report['manual_redecision_record_design']['target_draft_status_required']}",
        "",
        "## Final Lock Gate Design",
        "",
    ]

    for key, value in report["final_lock_gate_design"].items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Decision Gate Matrix",
        "",
        "| Decision | Gate Result | Publish In Phase 10-3 | Next Step |",
        "|---|---|---|---|",
    ]

    for row in report["decision_gate_matrix"]:
        lines.append(
            "| "
            f"{row['decision']} | {row['gate_result']} | {row['publish_execution_in_phase10_3']} | {row['next_step']}"
            " |"
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


def generate_report(input_10_2: Path, output_json: Path, output_md: Path) -> dict:
    if not input_10_2.exists():
        return abort_result(f"required input not found: {input_10_2}", output_json)

    source = load_json(input_10_2)
    err = validate_phase10_2(source)
    if err:
        return abort_result(err, output_json)

    report = build_report(source, input_10_2)

    write_json(output_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase10_3_manual_redecision_record_and_final_lock_gate_design_report_result",
        "phase": "Phase 10-3",
        "status": report["status"],
        "phase10_3_design_status": report["phase10_3_design_status"],
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
        description="Generate Phase 10-3 manual redecision record and final lock gate design report"
    )
    parser.add_argument("--input-10-2", type=Path, default=DEFAULT_INPUT_10_2)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()

    result = generate_report(args.input_10_2, args.output_json, args.output_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
