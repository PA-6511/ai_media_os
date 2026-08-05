#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_FALSE_FLAGS = [
    "wordpress_api_call_allowed",
    "wordpress_write_allowed",
    "wordpress_draft_creation_executed",
    "publish_allowed",
    "publish_executed",
    "future_schedule_allowed",
    "future_schedule_executed",
    "existing_post_update_allowed",
    "existing_post_update_executed",
    "delete_allowed",
    "delete_executed",
    "amazon_api_call_allowed",
    "x_api_call_allowed",
    "x_post_allowed",
    "approval_token_consumed",
    "phase_forward_execution_allowed",
    "credential_secret_output_allowed",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(policy: dict[str, Any], payload: dict[str, Any], policy_path: Path, payload_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    require(policy.get("phase") == "LS-4", "policy phase must be LS-4", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    require(policy.get("required_post_status") == "draft", "required_post_status must be draft", errors)

    safety_flags = policy.get("safety_flags", {})
    for key in REQUIRED_FALSE_FLAGS:
        require(safety_flags.get(key) is False, f"policy safety flag {key} must be false", errors)

    require(payload.get("phase") == "LS-4", "payload phase must be LS-4", errors)
    require(payload.get("execution_mode") == "DRY_RUN_ONLY", "payload execution_mode must be DRY_RUN_ONLY", errors)
    require(payload.get("production_status") == "NO_GO", "payload production_status must be NO_GO", errors)
    require(payload.get("wordpress_api_call_executed") is False, "wordpress_api_call_executed must be false", errors)
    require(payload.get("wordpress_write_executed") is False, "wordpress_write_executed must be false", errors)
    require(payload.get("wordpress_draft_creation_executed") is False, "wordpress_draft_creation_executed must be false", errors)
    require(payload.get("publish_executed") is False, "publish_executed must be false", errors)

    max_items = payload.get("max_items")
    require(isinstance(max_items, int), "max_items must be an integer", errors)
    if isinstance(max_items, int):
        require(max_items <= 1, "max_items must be <= 1", errors)

    payloads = payload.get("payloads", [])
    require(isinstance(payloads, list), "payloads must be a list", errors)
    if isinstance(payloads, list):
        require(len(payloads) <= 1, "payloads must contain at most one item", errors)

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

    status = "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_READY" if not errors else "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY"

    result = {
        "phase": "LS-4",
        "status": status,
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "policy_path": str(policy_path),
        "payload_path": str(payload_path),
        "max_items": max_items if isinstance(max_items, int) else None,
        "payload_count": len(payloads) if isinstance(payloads, list) else None,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_hashes_output": False,
        "errors": errors,
        "warnings": warnings,
        "next_phase": {
            "phase": "LS-5",
            "execution_allowed": False,
        },
        "payloads": payloads if isinstance(payloads, list) else [],
    }
    return result


def write_report(result: dict[str, Any], output_report: Path) -> None:
    lines = [
        "# LS-4 WordPress Draft Runner DRY_RUN Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- max_items: {result['max_items']}",
        f"- payload_count: {result['payload_count']}",
        "",
        "## Safety Confirmation",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- secret_values_output: {result['secret_values_output']}",
        f"- secret_lengths_output: {result['secret_lengths_output']}",
        f"- secret_hashes_output: {result['secret_hashes_output']}",
        "",
        "## Payload Checks",
    ]
    for index, payload in enumerate(result.get("payloads", []), start=1):
        lines.extend(
            [
                f"- payload[{index}] post_status: {payload.get('post_status')}",
                f"- payload[{index}] affiliate_disclosure_present: {payload.get('affiliate_disclosure_present')}",
                f"- payload[{index}] affiliate_link_present: {payload.get('affiliate_link_present')}",
                f"- payload[{index}] category_or_tag_present: {payload.get('category_or_tag_present')}",
                f"- payload[{index}] core_boundary_ref exists: {'core_boundary_ref' in payload}",
                f"- payload[{index}] audit_observation_ref exists: {'audit_observation_ref' in payload}",
                f"- payload[{index}] risk_score exists: {'risk_score' in payload}",
                f"- payload[{index}] rollback_pointer.required: {payload.get('rollback_pointer', {}).get('required')}",
                "",
            ]
        )
    lines.append("## Errors")
    errors = result.get("errors", [])
    if errors:
        for error in errors:
            lines.append(f"- {error}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Next Phase",
        "- LS-5: One-shot Draft Approval Gate",
        "",
    ])
    output_report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls4_wordpress_draft_runner_dry_run_policy.json")
    parser.add_argument("--payload", default="exchange/logs/start_ls4_wordpress_draft_payload_preview.json")
    parser.add_argument("--output", default="exchange/logs/start_ls4_wordpress_draft_runner_dry_run_result.json")
    parser.add_argument("--report", default="reports/start_ls4_wordpress_draft_runner_dry_run_report.md")
    args = parser.parse_args()

    policy_path = Path(args.policy)
    payload_path = Path(args.payload)
    output_path = Path(args.output)
    report_path = Path(args.report)

    try:
        policy = load_json(policy_path)
        payload = load_json(payload_path)
        result = validate(policy, payload, policy_path, payload_path)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        errors = [f"exception: {exc.__class__.__name__}"]
        result = {
            "phase": "LS-4",
            "status": "LS4_WORDPRESS_DRAFT_RUNNER_DRY_RUN_NOT_READY",
            "execution_mode": "DRY_RUN_ONLY",
            "production_status": "NO_GO",
            "policy_path": str(policy_path),
            "payload_path": str(payload_path),
            "max_items": None,
            "payload_count": None,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "publish_executed": False,
            "approval_token_consumed": False,
            "secret_values_output": False,
            "secret_lengths_output": False,
            "secret_hashes_output": False,
            "errors": errors,
            "warnings": [],
            "next_phase": {"phase": "LS-5", "execution_allowed": False},
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payloads": [],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, report_path)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())