#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    if "amazon.co.jp/dp/" not in content:
        return ""
    return content.split("amazon.co.jp/dp/")[1].split("?")[0].split('"')[0]


def build_blocked_plan(payload_ready: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": False,
        "runner_execution_allowed": False,
        "payload_ready": payload_ready,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "required_previous_phase": "LS-6E",
        "missing_or_not_ready": "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "runner_executed": False,
        "next_phase": {
            "phase": "LS-6G",
            "execution_allowed": False,
            "requires_ls6e_actual_approval": True,
            "requires_final_preflight": True,
        },
        "errors": errors if errors else ["LS-6E actual approval result not ready"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_ready_plan(payload_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION",
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": True,
        "runner_execution_allowed": False,
        "payload_ready": True,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "payload_title": payload_item.get("title", ""),
        "payload_asin": parse_asin(str(payload_item.get("content", ""))),
        "payload_post_status": payload_item.get("post_status", ""),
        "payload_content_format": payload_item.get("content_format", ""),
        "max_items": 1,
        "future_runner_constraints": {
            "create_new_draft_only": True,
            "post_status": "draft",
            "max_items": 1,
            "target_payload_only": True,
            "update_existing_post_allowed": False,
            "post119_update_allowed": False,
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "delete_allowed": False,
            "freeze_before_execution_required": True,
            "freeze_after_execution_required": True,
            "one_shot_lock_required_before_execution": True,
            "credential_env_read_required_in_future_execution_phase_only": True,
        },
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "runner_executed": False,
        "next_phase": {
            "phase": "LS-6G",
            "execution_allowed": False,
            "requires_final_preflight": True,
        },
        "errors": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6f_real_payload_one_shot_draft_runner_prep_policy.json")
    parser.add_argument("--ls6e-approved-result", default="exchange/logs/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_approved_result.json")
    parser.add_argument("--ls6e-approval", default="exchange/human_review/start_ls6e_real_payload_one_shot_draft_creation_approval.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_plan.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))

    errors: list[str] = []

    require(policy.get("phase") == "LS-6F", "policy phase must be LS-6F", errors)
    require(policy.get("execution_mode") == "PREP_ONLY", "policy execution_mode must be PREP_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)

    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C validator status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_payload.get("payload_ready") is True, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)

    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)

    payload_item = payloads[0] if isinstance(payloads, list) and len(payloads) == 1 else {}
    require(payload_item.get("post_status") == "draft", "LS-6C post_status must be draft", errors)
    require(payload_item.get("content_format") == "html", "LS-6C content_format must be html", errors)

    payload_ready = not any(
        e.startswith("LS-6C")
        for e in errors
    )

    approved_path = Path(args.ls6e_approved_result)
    approval_path = Path(args.ls6e_approval)

    if errors:
        plan = {
            "phase": "LS-6F",
            "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY",
            "execution_mode": "PREP_ONLY",
            "production_status": "NO_GO",
            "runner_plan_ready": False,
            "runner_execution_allowed": False,
            "payload_ready": payload_ready,
            "approval_label_consumed": False,
            "wordpress_write_allowed_by_this_phase": False,
            "wordpress_draft_creation_allowed_by_this_phase": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "post119_update_executed": False,
            "publish_executed": False,
            "credential_env_read_executed": False,
            "approval_token_consumed": False,
            "runner_executed": False,
            "next_phase": {
                "phase": "LS-6G",
                "execution_allowed": False,
                "requires_final_preflight": True,
            },
            "errors": errors,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    elif not approved_path.exists() or not approval_path.exists():
        blocked_errors = []
        if not approved_path.exists():
            blocked_errors.append("LS-6E actual approval result not ready")
        if not approval_path.exists():
            blocked_errors.append("LS-6E actual approval file not found")
        plan = build_blocked_plan(payload_ready=payload_ready, errors=blocked_errors)
    else:
        ls6e_approved = load_json(approved_path)
        ls6e_approval = load_json(approval_path)

        require(
            ls6e_approved.get("status") == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION",
            "LS-6E approved result status mismatch",
            errors,
        )
        require(
            ls6e_approved.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
            "LS-6E approved result approval_label mismatch",
            errors,
        )
        require(ls6e_approved.get("approval_label_consumed") is False, "LS-6E approved result approval_label_consumed must be false", errors)
        require(ls6e_approved.get("wordpress_write_allowed_by_this_phase") is False, "LS-6E approved result wordpress_write_allowed_by_this_phase must be false", errors)
        require(ls6e_approved.get("wordpress_draft_creation_allowed_by_this_phase") is False, "LS-6E approved result wordpress_draft_creation_allowed_by_this_phase must be false", errors)

        require(
            ls6e_approval.get("approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION",
            "LS-6E approval approval_status mismatch",
            errors,
        )
        require(
            ls6e_approval.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY",
            "LS-6E approval approval_label mismatch",
            errors,
        )

        if errors:
            plan = {
                "phase": "LS-6F",
                "status": "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY",
                "execution_mode": "PREP_ONLY",
                "production_status": "NO_GO",
                "runner_plan_ready": False,
                "runner_execution_allowed": False,
                "payload_ready": payload_ready,
                "approval_label_consumed": False,
                "wordpress_write_allowed_by_this_phase": False,
                "wordpress_draft_creation_allowed_by_this_phase": False,
                "wordpress_api_call_executed": False,
                "wordpress_write_executed": False,
                "wordpress_draft_creation_executed": False,
                "post119_update_executed": False,
                "publish_executed": False,
                "credential_env_read_executed": False,
                "approval_token_consumed": False,
                "runner_executed": False,
                "next_phase": {
                    "phase": "LS-6G",
                    "execution_allowed": False,
                    "requires_final_preflight": True,
                },
                "errors": errors,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            plan = build_ready_plan(payload_item)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
