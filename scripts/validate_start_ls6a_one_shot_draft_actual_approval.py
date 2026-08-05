#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_FALSE_POLICY_FLAGS = [
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

REQUIRED_FALSE_CURRENT_PHASE_EXECUTION = [
    "wordpress_api_call_executed",
    "wordpress_write_executed",
    "wordpress_draft_creation_executed",
    "publish_executed",
    "approval_token_consumed",
]

REQUIRED_CONFIRMATION_TEXT = "I explicitly approve LS-6B WordPress one-shot draft creation only."


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6A", "policy phase must be LS-6A", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    require(
        policy.get("required_approval_label") == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "policy required_approval_label mismatch",
        errors,
    )
    require(policy.get("required_approval_status") == "HUMAN_APPROVED", "policy required_approval_status must be HUMAN_APPROVED", errors)

    previous = policy.get("required_previous_phases", {})
    ls3 = previous.get("ls3", {})
    require(ls3.get("required_status") == "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY", "policy ls3 required_status mismatch", errors)
    require(ls3.get("result") == "exchange/logs/start_ls3_wordpress_credential_ready_result.json", "policy ls3 result path mismatch", errors)

    ls4 = previous.get("ls4", {})
    require(ls4.get("required_status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", "policy ls4 required_status mismatch", errors)
    require(ls4.get("payload_preview") == "exchange/logs/start_ls4_wordpress_draft_payload_preview.json", "policy ls4 payload_preview path mismatch", errors)
    require(ls4.get("result") == "exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json", "policy ls4 result path mismatch", errors)

    ls5 = previous.get("ls5", {})
    require(ls5.get("required_status") == "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION", "policy ls5 required_status mismatch", errors)
    require(ls5.get("result") == "exchange/logs/start_ls5_one_shot_draft_approval_result.json", "policy ls5 result path mismatch", errors)

    source = policy.get("approval_source_policy", {})
    require(source.get("human_approval_required") is True, "policy human_approval_required must be true", errors)
    require(source.get("auto_approval_allowed") is False, "policy auto_approval_allowed must be false", errors)
    require(source.get("core_ai_self_approval_allowed") is False, "policy core_ai_self_approval_allowed must be false", errors)
    require(source.get("block_ai_self_approval_allowed") is False, "policy block_ai_self_approval_allowed must be false", errors)
    require(source.get("audit_block_ai_approval_allowed") is False, "policy audit_block_ai_approval_allowed must be false", errors)
    require(source.get("template_must_not_be_treated_as_actual") is True, "policy template_must_not_be_treated_as_actual must be true", errors)

    for key in REQUIRED_FALSE_POLICY_FLAGS:
        require(policy.get("current_phase_safety_flags", {}).get(key) is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_previous_results(ls3_result: dict[str, Any], ls4_result: dict[str, Any], ls5_result: dict[str, Any], errors: list[str]) -> None:
    require(ls3_result.get("status") == "LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY", "LS-3 status must be LS3_WORDPRESS_CREDENTIAL_READY_DRY_RUN_ONLY", errors)
    require(ls4_result.get("status") == "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", "LS-4 status must be LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY", errors)
    require(ls5_result.get("status") == "LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION", "LS-5 status must be LS5_APPROVAL_GATE_EXAMPLE_PASS_NO_EXECUTION", errors)


def validate_ls4_payload(payload: dict[str, Any], errors: list[str]) -> None:
    require(payload.get("phase") == "LS-4", "payload phase must be LS-4", errors)
    require(payload.get("execution_mode") == "DRY_RUN_ONLY", "payload execution_mode must be DRY_RUN_ONLY", errors)
    require(payload.get("production_status") == "NO_GO", "payload production_status must be NO_GO", errors)
    require(payload.get("wordpress_api_call_executed") is False, "payload wordpress_api_call_executed must be false", errors)
    require(payload.get("wordpress_write_executed") is False, "payload wordpress_write_executed must be false", errors)
    require(payload.get("wordpress_draft_creation_executed") is False, "payload wordpress_draft_creation_executed must be false", errors)
    require(payload.get("publish_executed") is False, "payload publish_executed must be false", errors)

    max_items = payload.get("max_items")
    require(isinstance(max_items, int), "payload max_items must be an integer", errors)
    if isinstance(max_items, int):
        require(max_items <= 1, "payload max_items must be <= 1", errors)

    payloads = payload.get("payloads", [])
    require(isinstance(payloads, list), "payload payloads must be a list", errors)
    if isinstance(payloads, list):
        require(len(payloads) <= 1, "payload payloads must contain at most one item", errors)
        for idx, item in enumerate(payloads):
            require(item.get("post_status") == "draft", f"payload[{idx}] post_status must be draft", errors)


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("phase") == "LS-6A", "template phase must be LS-6A", errors)
    require(template.get("approval_label") == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY", "template approval_label mismatch", errors)
    require(template.get("approval_status") == "TEMPLATE_NOT_ACTUAL_APPROVAL", "template approval_status must be TEMPLATE_NOT_ACTUAL_APPROVAL", errors)


def validate_approval_file(approval: dict[str, Any], required_label: str, errors: list[str]) -> None:
    require(approval.get("phase") == "LS-6A", "approval phase must be LS-6A", errors)
    require(approval.get("approval_status") == "HUMAN_APPROVED", "approval_status must be HUMAN_APPROVED", errors)
    require(approval.get("approval_label") == required_label, "approval_label mismatch", errors)
    require(approval.get("human_confirmation_text") == REQUIRED_CONFIRMATION_TEXT, "human_confirmation_text mismatch", errors)

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

    execution = approval.get("current_phase_execution", {})
    for key in REQUIRED_FALSE_CURRENT_PHASE_EXECUTION:
        require(execution.get(key) is False, f"current_phase_execution.{key} must be false", errors)


def build_result(
    policy: dict[str, Any],
    template: dict[str, Any],
    ls3_result: dict[str, Any],
    ls4_result: dict[str, Any],
    ls5_result: dict[str, Any],
    payload: dict[str, Any],
    approval: dict[str, Any] | None,
    approval_path: Path,
    allow_template: bool,
) -> dict[str, Any]:
    errors: list[str] = []

    validate_policy(policy, errors)
    validate_template(template, errors)
    validate_previous_results(ls3_result, ls4_result, ls5_result, errors)
    validate_ls4_payload(payload, errors)

    approval_is_actual = False
    if allow_template:
        status = "LS6A_TEMPLATE_PASS_NO_ACTUAL_APPROVAL" if not errors else "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"
    else:
        if approval is None:
            status = "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"
            errors.append(f"actual approval file not found: {approval_path}")
        else:
            validate_approval_file(approval, policy.get("required_approval_label", ""), errors)
            approval_is_actual = not errors
            status = "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION" if approval_is_actual else "LS6A_ACTUAL_HUMAN_APPROVAL_NOT_READY"

    return {
        "phase": "LS-6A",
        "status": status,
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "approval_label": policy.get("required_approval_label"),
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
            "phase": "LS-6B",
            "execution_allowed": False,
            "requires_actual_human_approval": True,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], output_report: Path) -> None:
    lines = [
        "# LS-6A One-shot Draft Actual Human Approval Gate Report",
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
        "- LS-6B: WordPress One-shot Draft Creation",
        "- execution_allowed: False",
        "- requires_actual_human_approval: True",
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
    parser.add_argument("--policy", default="config/start_ls6a_one_shot_draft_actual_approval_policy.json")
    parser.add_argument("--approval", default="exchange/human_review/start_ls6a_one_shot_draft_actual_approval.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6a_one_shot_draft_actual_approval.template.json")
    parser.add_argument("--ls3-result", default="exchange/logs/start_ls3_wordpress_credential_ready_result.json")
    parser.add_argument("--ls4-result", default="exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json")
    parser.add_argument("--ls5-result", default="exchange/logs/start_ls5_one_shot_draft_approval_result.json")
    parser.add_argument("--payload", default="exchange/logs/start_ls4_wordpress_draft_payload_preview.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6a_one_shot_draft_actual_approval_result.json")
    parser.add_argument("--report", default="reports/start_ls6a_one_shot_draft_actual_approval_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy_path = Path(args.policy)
    approval_path = Path(args.approval)
    template_path = Path(args.template)
    ls3_result_path = Path(args.ls3_result)
    ls4_result_path = Path(args.ls4_result)
    ls5_result_path = Path(args.ls5_result)
    payload_path = Path(args.payload)
    output_path = Path(args.output)
    report_path = Path(args.report)

    policy = load_json(policy_path)
    template = load_json(template_path)
    ls3_result = load_json(ls3_result_path)
    ls4_result = load_json(ls4_result_path)
    ls5_result = load_json(ls5_result_path)
    payload = load_json(payload_path)

    approval: dict[str, Any] | None = None
    if approval_path.exists():
        approval = load_json(approval_path)

    result = build_result(
        policy=policy,
        template=template,
        ls3_result=ls3_result,
        ls4_result=ls4_result,
        ls5_result=ls5_result,
        payload=payload,
        approval=approval,
        approval_path=approval_path,
        allow_template=args.allow_template,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
