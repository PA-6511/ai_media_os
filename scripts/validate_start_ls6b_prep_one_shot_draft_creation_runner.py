#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_FALSE_FLAGS = [
    "wordpress_api_call_executed",
    "wordpress_write_executed",
    "wordpress_draft_creation_executed",
    "publish_executed",
    "future_schedule_executed",
    "existing_post_update_executed",
    "delete_executed",
    "amazon_api_call_executed",
    "x_api_call_executed",
    "x_post_executed",
    "credential_env_read_executed",
    "credential_secret_output",
    "approval_token_consumed",
    "actual_human_approval_file_created",
    "human_approved_status_generated",
    "phase_forward_execution_executed",
]

PLAN_FALSE_FLAGS = [
    "wordpress_api_call_executed",
    "wordpress_write_executed",
    "wordpress_draft_creation_executed",
    "publish_executed",
    "credential_env_read_executed",
    "approval_token_consumed",
]

PLAN_CONTRACT_TRUE_FLAGS = [
    "must_revalidate_actual_human_approval",
    "must_revalidate_payload_preview",
    "must_revalidate_credential_ready",
    "must_reject_multiple_payloads",
    "must_reject_non_draft_status",
    "must_reject_publish_update_delete",
    "must_record_post_id",
    "must_record_rollback_pointer",
    "must_freeze_after_run",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6B-PREP", "policy phase must be LS-6B-PREP", errors)
    require(policy.get("status") == "RUNNER_DESIGN_ONLY_BLOCKED_UNTIL_ACTUAL_HUMAN_APPROVAL", "policy status mismatch", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)

    scope = policy.get("runner_design_scope", {})
    require(scope.get("blocked_until_actual_human_approval") is True, "policy blocked_until_actual_human_approval must be true", errors)
    require(scope.get("required_actual_approval_status") == "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION", "policy required_actual_approval_status mismatch", errors)
    require(scope.get("max_items") == 1, "policy max_items must be 1", errors)
    require(scope.get("post_status") == "draft", "policy post_status must be draft", errors)
    require(scope.get("publish_allowed") is False, "policy publish_allowed must be false", errors)
    require(scope.get("future_schedule_allowed") is False, "policy future_schedule_allowed must be false", errors)
    require(scope.get("existing_post_update_allowed") is False, "policy existing_post_update_allowed must be false", errors)
    require(scope.get("delete_allowed") is False, "policy delete_allowed must be false", errors)
    require(scope.get("freeze_after_run") is True, "policy freeze_after_run must be true", errors)
    require(scope.get("rollback_pointer_required") is True, "policy rollback_pointer_required must be true", errors)

    for key in POLICY_FALSE_FLAGS:
        require(policy.get("current_phase_safety_flags", {}).get(key) is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_previous_results(
    ls3_result: dict[str, Any],
    ls4_result: dict[str, Any],
    ls5_result: dict[str, Any],
    ls6a_template_result: dict[str, Any],
    ls6a_not_ready_result: dict[str, Any],
    errors: list[str],
) -> None:
    require(ls3_result.get("status") == "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY", "LS-3 status mismatch", errors)
    require(ls4_result.get("status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", "LS-4 status mismatch", errors)
    require(ls5_result.get("status") == "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION", "LS-5 status mismatch", errors)
    require(ls6a_template_result.get("status") == "LS6A_TEMPLATE_PASS_NO_ACTUAL_APPROVAL", "LS-6A template result status mismatch", errors)
    require(ls6a_not_ready_result.get("status") == "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY", "LS-6A not-ready result status mismatch", errors)


def validate_payload(payload: dict[str, Any], errors: list[str]) -> None:
    require(payload.get("phase") == "LS-4", "payload phase must be LS-4", errors)
    require(payload.get("execution_mode") == "DRY_RUN_ONLY", "payload execution_mode must be DRY_RUN_ONLY", errors)
    require(payload.get("production_status") == "NO_GO", "payload production_status must be NO_GO", errors)
    require(payload.get("wordpress_api_call_executed") is False, "payload wordpress_api_call_executed must be false", errors)
    require(payload.get("wordpress_write_executed") is False, "payload wordpress_write_executed must be false", errors)
    require(payload.get("wordpress_draft_creation_executed") is False, "payload wordpress_draft_creation_executed must be false", errors)
    require(payload.get("publish_executed") is False, "payload publish_executed must be false", errors)
    require(isinstance(payload.get("max_items"), int), "payload max_items must be integer", errors)
    if isinstance(payload.get("max_items"), int):
        require(payload.get("max_items") <= 1, "payload max_items must be <= 1", errors)

    payloads = payload.get("payloads", [])
    require(isinstance(payloads, list), "payload payloads must be list", errors)
    if isinstance(payloads, list):
        require(len(payloads) <= 1, "payload payloads must contain at most one item", errors)
        for idx, item in enumerate(payloads):
            require(item.get("post_status") == "draft", f"payload[{idx}] post_status must be draft", errors)


def validate_plan(plan: dict[str, Any], errors: list[str]) -> None:
    require(plan.get("phase") == "LS-6B-PREP", "plan phase must be LS-6B-PREP", errors)
    require(plan.get("status") == "LS6B_PREP_RUNNER_PLAN_BLOCKED_NO_EXECUTION", "plan status mismatch", errors)
    require(plan.get("execution_mode") == "DRY_RUN_ONLY", "plan execution_mode must be DRY_RUN_ONLY", errors)
    require(plan.get("production_status") == "NO_GO", "plan production_status must be NO_GO", errors)
    require(plan.get("blocked_until_actual_human_approval") is True, "plan blocked_until_actual_human_approval must be true", errors)
    require(plan.get("required_actual_approval_status") == "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION", "plan required_actual_approval_status mismatch", errors)
    require(plan.get("max_items") == 1, "plan max_items must be 1", errors)
    require(plan.get("post_status") == "draft", "plan post_status must be draft", errors)

    guards = plan.get("guards", {})
    require(guards.get("publish_allowed") is False, "plan guards.publish_allowed must be false", errors)
    require(guards.get("future_schedule_allowed") is False, "plan guards.future_schedule_allowed must be false", errors)
    require(guards.get("existing_post_update_allowed") is False, "plan guards.existing_post_update_allowed must be false", errors)
    require(guards.get("delete_allowed") is False, "plan guards.delete_allowed must be false", errors)
    require(guards.get("freeze_after_run") is True, "plan guards.freeze_after_run must be true", errors)
    require(guards.get("rollback_pointer_required") is True, "plan guards.rollback_pointer_required must be true", errors)
    require(guards.get("post_id_evidence_required_after_execution") is True, "plan guards.post_id_evidence_required_after_execution must be true", errors)

    for key in PLAN_FALSE_FLAGS:
        require(plan.get("current_phase_execution", {}).get(key) is False, f"plan current_phase_execution.{key} must be false", errors)

    for key in PLAN_CONTRACT_TRUE_FLAGS:
        require(plan.get("future_execution_contract", {}).get(key) is True, f"plan future_execution_contract.{key} must be true", errors)

    require(plan.get("next_phase", {}).get("phase") == "LS-6B", "plan next_phase.phase must be LS-6B", errors)
    require(plan.get("next_phase", {}).get("execution_allowed") is False, "plan next_phase.execution_allowed must be false", errors)


def build_result(errors: list[str]) -> dict[str, Any]:
    status = "LS6B_PREP_RUNNER_DESIGN_BLOCKED_PASS_NO_EXECUTION" if not errors else "LS6B_PREP_RUNNER_DESIGN_NOT_READY"
    return {
        "phase": "LS-6B-PREP",
        "status": status,
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "blocked_until_actual_human_approval": True,
        "required_actual_approval_status": "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "actual_human_approval_file_created": False,
        "human_approved_status_generated": False,
        "runner_plan_ready": not errors,
        "errors": errors,
        "next_phase": {
            "phase": "LS-6B",
            "execution_allowed": False,
            "blocked_until": "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], output_report: Path) -> None:
    lines = [
        "# LS-6B-PREP WordPress One-shot Draft Creation Runner Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- blocked_until_actual_human_approval: {result['blocked_until_actual_human_approval']}",
        f"- required_actual_approval_status: {result['required_actual_approval_status']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- actual_human_approval_file_created: {result['actual_human_approval_file_created']}",
        f"- human_approved_status_generated: {result['human_approved_status_generated']}",
        f"- runner_plan_ready: {result['runner_plan_ready']}",
        "",
        "## Next Phase",
        "- LS-6B: WordPress One-shot Draft Creation",
        "- execution_allowed: False",
        "- blocked_until: LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {error}" for error in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    output_report.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6b_prep_one_shot_draft_creation_runner_policy.json")
    parser.add_argument("--plan", default="exchange/logs/start_ls6b_prep_one_shot_draft_creation_runner_plan.json")
    parser.add_argument("--ls3-result", default="exchange/logs/start_ls3_wordpress_credential_ready_result.json")
    parser.add_argument("--ls4-result", default="exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json")
    parser.add_argument("--ls5-result", default="exchange/logs/start_ls5_one_shot_draft_approval_result.json")
    parser.add_argument("--ls6a-template-result", default="exchange/logs/start_ls6a_one_shot_draft_actual_approval_result.json")
    parser.add_argument("--ls6a-not-ready-result", default="exchange/logs/start_ls6a_one_shot_draft_actual_approval_not_ready_result.json")
    parser.add_argument("--payload", default="exchange/logs/start_ls4_wordpress_draft_payload_preview.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6b_prep_one_shot_draft_creation_runner_result.json")
    parser.add_argument("--report", default="reports/start_ls6b_prep_one_shot_draft_creation_runner_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    plan = load_json(Path(args.plan))
    ls3_result = load_json(Path(args.ls3_result))
    ls4_result = load_json(Path(args.ls4_result))
    ls5_result = load_json(Path(args.ls5_result))
    ls6a_template_result = load_json(Path(args.ls6a_template_result))
    ls6a_not_ready_result = load_json(Path(args.ls6a_not_ready_result))
    payload = load_json(Path(args.payload))

    errors: list[str] = []
    validate_policy(policy, errors)
    validate_previous_results(ls3_result, ls4_result, ls5_result, ls6a_template_result, ls6a_not_ready_result, errors)
    validate_payload(payload, errors)
    validate_plan(plan, errors)

    result = build_result(errors)

    output_path = Path(args.output)
    report_path = Path(args.report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
