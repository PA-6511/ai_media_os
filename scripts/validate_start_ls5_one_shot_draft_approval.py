#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_FALSE_FLAGS = [
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
    "credential_secret_output",
    "approval_token_consumed",
    "phase_forward_execution_executed",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-5", "policy phase must be LS-5", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    require(policy.get("required_approval_label") == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY", "required_approval_label mismatch", errors)

    required_previous = policy.get("required_previous_phase", {})
    require(required_previous.get("phase") == "LS-4", "required_previous_phase.phase must be LS-4", errors)
    require(
        required_previous.get("required_status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY",
        "required_previous_phase.required_status mismatch",
        errors,
    )
    require(
        required_previous.get("payload_preview") == "exchange/logs/start_ls4_wordpress_draft_payload_preview.json",
        "required_previous_phase.payload_preview mismatch",
        errors,
    )
    require(
        required_previous.get("result") == "exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json",
        "required_previous_phase.result mismatch",
        errors,
    )

    approval_scope = policy.get("approval_scope_for_next_phase", {})
    require(approval_scope.get("next_phase") == "LS-6", "approval_scope_for_next_phase.next_phase must be LS-6", errors)
    require(approval_scope.get("wordpress_write_allowed_for_next_phase") is True, "approval_scope_for_next_phase.wordpress_write_allowed_for_next_phase must be true", errors)
    require(approval_scope.get("wordpress_draft_creation_allowed_for_next_phase") is True, "approval_scope_for_next_phase.wordpress_draft_creation_allowed_for_next_phase must be true", errors)
    require(approval_scope.get("max_items") == 1, "approval_scope_for_next_phase.max_items must be 1", errors)
    require(approval_scope.get("post_status") == "draft", "approval_scope_for_next_phase.post_status must be draft", errors)
    require(approval_scope.get("publish_allowed") is False, "approval_scope_for_next_phase.publish_allowed must be false", errors)
    require(approval_scope.get("future_schedule_allowed") is False, "approval_scope_for_next_phase.future_schedule_allowed must be false", errors)
    require(approval_scope.get("existing_post_update_allowed") is False, "approval_scope_for_next_phase.existing_post_update_allowed must be false", errors)
    require(approval_scope.get("delete_allowed") is False, "approval_scope_for_next_phase.delete_allowed must be false", errors)
    require(approval_scope.get("freeze_after_run") is True, "approval_scope_for_next_phase.freeze_after_run must be true", errors)
    require(approval_scope.get("rollback_pointer_required") is True, "approval_scope_for_next_phase.rollback_pointer_required must be true", errors)

    next_phase = policy.get("next_phase", {})
    require(next_phase.get("phase") == "LS-6", "next_phase.phase must be LS-6", errors)
    require(next_phase.get("name") == "WordPress One-shot Draft Creation", "next_phase.name mismatch", errors)
    require(next_phase.get("execution_allowed_by_this_phase") is False, "next_phase.execution_allowed_by_this_phase must be false", errors)
    require(next_phase.get("requires_valid_human_approval") is True, "next_phase.requires_valid_human_approval must be true", errors)

    source_policy = policy.get("approval_source_policy", {})
    require(source_policy.get("human_approval_required") is True, "human_approval_required must be true", errors)
    require(source_policy.get("auto_approval_allowed") is False, "auto_approval_allowed must be false", errors)
    require(source_policy.get("core_ai_self_approval_allowed") is False, "core_ai_self_approval_allowed must be false", errors)
    require(source_policy.get("block_ai_self_approval_allowed") is False, "block_ai_self_approval_allowed must be false", errors)
    require(source_policy.get("audit_block_ai_approval_allowed") is False, "audit_block_ai_approval_allowed must be false", errors)

    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"current_phase_safety_flag {key} must be false", errors)


def validate_ls4_inputs(ls4_result: dict[str, Any], payload: dict[str, Any], errors: list[str]) -> None:
    require(ls4_result.get("status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", "LS-4 result must be READY", errors)
    require(ls4_result.get("execution_mode") == "DRY_RUN_ONLY", "LS-4 result execution_mode must be DRY_RUN_ONLY", errors)
    require(ls4_result.get("production_status") == "NO_GO", "LS-4 result production_status must be NO_GO", errors)

    require(payload.get("phase") == "LS-4", "payload phase must be LS-4", errors)
    require(payload.get("execution_mode") == "DRY_RUN_ONLY", "payload execution_mode must be DRY_RUN_ONLY", errors)
    require(payload.get("production_status") == "NO_GO", "payload production_status must be NO_GO", errors)
    require(payload.get("wordpress_api_call_executed") is False, "payload wordpress_api_call_executed must be false", errors)
    require(payload.get("wordpress_write_executed") is False, "payload wordpress_write_executed must be false", errors)
    require(payload.get("wordpress_draft_creation_executed") is False, "payload wordpress_draft_creation_executed must be false", errors)
    require(payload.get("publish_executed") is False, "payload publish_executed must be false", errors)
    require(isinstance(payload.get("max_items"), int), "payload max_items must be an integer", errors)
    if isinstance(payload.get("max_items"), int):
        require(payload.get("max_items") <= 1, "payload max_items must be <= 1", errors)
    payloads = payload.get("payloads", [])
    require(isinstance(payloads, list), "payload payloads must be a list", errors)
    if isinstance(payloads, list):
        require(len(payloads) <= 1, "payload payloads must contain at most one item", errors)
        for index, item in enumerate(payloads):
            require(item.get("post_status") == "draft", f"payload[{index}] post_status must be draft", errors)
            require(bool(item.get("title")), f"payload[{index}] title must not be empty", errors)
            require(bool(item.get("content")), f"payload[{index}] content must not be empty", errors)
            require(item.get("affiliate_disclosure_present") is True, f"payload[{index}] affiliate_disclosure_present must be true", errors)
            require(item.get("affiliate_link_present") is True, f"payload[{index}] affiliate_link_present must be true", errors)
            require(item.get("category_or_tag_present") is True, f"payload[{index}] category_or_tag_present must be true", errors)
            require("core_boundary_ref" in item, f"payload[{index}] core_boundary_ref must exist", errors)
            require("audit_observation_ref" in item, f"payload[{index}] audit_observation_ref must exist", errors)
            require("risk_score" in item, f"payload[{index}] risk_score must exist", errors)
            rollback_pointer = item.get("rollback_pointer")
            require(isinstance(rollback_pointer, dict), f"payload[{index}] rollback_pointer must be a dict", errors)
            if isinstance(rollback_pointer, dict):
                require(rollback_pointer.get("required") is True, f"payload[{index}] rollback_pointer.required must be true", errors)


def validate_approval(policy: dict[str, Any], approval: dict[str, Any], allow_example: bool, errors: list[str]) -> bool:
    approval_is_actual = False
    require(approval.get("phase") == "LS-5", "approval phase must be LS-5", errors)
    require(approval.get("approval_label") == policy.get("required_approval_label"), "approval_label mismatch", errors)

    approval_status = approval.get("approval_status")
    if approval_status == "EXAMPLE_NOT_ACTUAL_APPROVAL":
        approval_is_actual = False
        if not allow_example:
            errors.append("example approval requires --allow-example")
    elif approval_status == "HUMAN_APPROVED":
        approval_is_actual = True
    else:
        errors.append("approval_status must be EXAMPLE_NOT_ACTUAL_APPROVAL or HUMAN_APPROVED")

    if approval.get("approved_by") != "HUMAN_REQUIRED":
        errors.append("approved_by must be HUMAN_REQUIRED")

    target = approval.get("approval_target", {})
    require(target.get("next_phase") == "LS-6", "approval_target.next_phase must be LS-6", errors)
    require(target.get("max_items") == 1, "approval_target.max_items must be 1", errors)
    require(target.get("post_status") == "draft", "approval_target.post_status must be draft", errors)

    scope = approval.get("approved_scope", {})
    require(scope.get("wordpress_write_allowed") is True, "approved_scope.wordpress_write_allowed must be true", errors)
    require(scope.get("wordpress_draft_creation_allowed") is True, "approved_scope.wordpress_draft_creation_allowed must be true", errors)
    require(scope.get("publish_allowed") is False, "approved_scope.publish_allowed must be false", errors)
    require(scope.get("future_schedule_allowed") is False, "approved_scope.future_schedule_allowed must be false", errors)
    require(scope.get("existing_post_update_allowed") is False, "approved_scope.existing_post_update_allowed must be false", errors)
    require(scope.get("delete_allowed") is False, "approved_scope.delete_allowed must be false", errors)
    require(scope.get("amazon_api_call_allowed") is False, "approved_scope.amazon_api_call_allowed must be false", errors)
    require(scope.get("x_api_call_allowed") is False, "approved_scope.x_api_call_allowed must be false", errors)
    require(scope.get("x_post_allowed") is False, "approved_scope.x_post_allowed must be false", errors)
    require(scope.get("freeze_after_run") is True, "approved_scope.freeze_after_run must be true", errors)
    require(scope.get("rollback_pointer_required") is True, "approved_scope.rollback_pointer_required must be true", errors)

    for key, value in approval.get("current_phase_execution", {}).items():
        require(value is False, f"current_phase_execution.{key} must be false", errors)

    return approval_is_actual


def build_result(policy: dict[str, Any], approval: dict[str, Any], ls4_result: dict[str, Any], payload: dict[str, Any], allow_example: bool) -> dict[str, Any]:
    errors: list[str] = []

    validate_policy(policy, errors)
    validate_ls4_inputs(ls4_result, payload, errors)
    approval_is_actual = validate_approval(policy, approval, allow_example, errors)

    if approval.get("approval_status") == "EXAMPLE_NOT_ACTUAL_APPROVAL" and not allow_example:
        status = "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"
    elif errors:
        status = "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION" if (approval.get("approval_status") == "EXAMPLE_NOT_ACTUAL_APPROVAL" and allow_example and not errors) else "LS5_APPROVAL_NOT_ACTUAL_NOT_READY"
    else:
        status = "LS5_ONE_SHOT_DRAFT_APPROVAL_READY" if approval_is_actual else "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION"

    return {
        "phase": "LS-5",
        "status": status,
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "approval_label": approval.get("approval_label"),
        "approval_is_actual": approval_is_actual,
        "human_approval_required": True,
        "auto_approval_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "errors": errors,
        "next_phase": {
            "phase": "LS-6",
            "execution_allowed": False,
            "requires_actual_human_approval": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], output_report: Path) -> None:
    lines = [
        "# LS-5 One-shot Draft Approval Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_is_actual: {result['approval_is_actual']}",
        f"- human_approval_required: {result['human_approval_required']}",
        f"- auto_approval_allowed: {result['auto_approval_allowed']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        "",
        "## Next Phase",
        "- LS-6: WordPress One-shot Draft Creation",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {error}" for error in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    output_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls5_one_shot_draft_approval_policy.json")
    parser.add_argument("--approval", default="exchange/human_review/start_ls5_one_shot_draft_approval.example.json")
    parser.add_argument("--ls4-result", default="exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json")
    parser.add_argument("--payload", default="exchange/logs/start_ls4_wordpress_draft_payload_preview.json")
    parser.add_argument("--output", default="exchange/logs/start_ls5_one_shot_draft_approval_result.json")
    parser.add_argument("--report", default="reports/start_ls5_one_shot_draft_approval_report.md")
    parser.add_argument("--allow-example", action="store_true")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    approval_path = Path(args.approval)
    ls4_result_path = Path(args.ls4_result)
    payload_path = Path(args.payload)
    output_path = Path(args.output)
    report_path = Path(args.report)

    policy = load_json(policy_path)
    approval = load_json(approval_path)
    ls4_result = load_json(ls4_result_path)
    payload = load_json(payload_path)

    result = build_result(policy, approval, ls4_result, payload, args.allow_example)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())