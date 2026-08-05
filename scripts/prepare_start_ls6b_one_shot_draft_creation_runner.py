#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    "credential_env_read_executed",
    "credential_secret_output",
    "approval_token_consumed",
    "actual_human_approval_file_created",
    "human_approved_status_generated",
    "phase_forward_execution_executed",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6B-PREP", "policy phase must be LS-6B-PREP", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    for key in REQUIRED_FALSE_FLAGS:
        require(policy.get("current_phase_safety_flags", {}).get(key) is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def build_plan(policy: dict[str, Any]) -> dict[str, Any]:
    scope = policy.get("runner_design_scope", {})
    contract = policy.get("future_execution_contract", {})

    return {
        "phase": "LS-6B-PREP",
        "status": "LS6B_PREP_RUNNER_PLAN_BLOCKED_NO_EXECUTION",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "target_next_phase": scope.get("target_next_phase"),
        "blocked_until_actual_human_approval": True,
        "required_actual_approval_status": "LS6A_ACTUAL_HUMAN_APPROVAL_READY_NO_EXECUTION",
        "approval_label": scope.get("approval_label"),
        "payload_preview": policy.get("required_previous_phases", {}).get("ls4", {}).get("payload_preview"),
        "max_items": 1,
        "post_status": "draft",
        "guards": {
            "publish_allowed": False,
            "future_schedule_allowed": False,
            "existing_post_update_allowed": False,
            "delete_allowed": False,
            "freeze_after_run": bool(scope.get("freeze_after_run")),
            "rollback_pointer_required": bool(scope.get("rollback_pointer_required")),
            "post_id_evidence_required_after_execution": bool(scope.get("post_id_evidence_required_after_execution")),
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "publish_executed": False,
            "credential_env_read_executed": False,
            "approval_token_consumed": False,
        },
        "future_execution_contract": {
            "must_revalidate_actual_human_approval": bool(contract.get("future_runner_must_revalidate_actual_human_approval")),
            "must_revalidate_payload_preview": bool(contract.get("future_runner_must_revalidate_payload_preview")),
            "must_revalidate_credential_ready": bool(contract.get("future_runner_must_revalidate_credential_ready")),
            "must_reject_multiple_payloads": bool(contract.get("future_runner_must_reject_multiple_payloads")),
            "must_reject_non_draft_status": bool(contract.get("future_runner_must_reject_non_draft_status")),
            "must_reject_publish_update_delete": bool(contract.get("future_runner_must_reject_publish_update_delete")),
            "must_record_post_id": bool(contract.get("future_runner_must_record_post_id")),
            "must_record_rollback_pointer": bool(contract.get("future_runner_must_record_rollback_pointer")),
            "must_freeze_after_run": bool(contract.get("future_runner_must_freeze_after_run")),
        },
        "next_phase": {
            "phase": "LS-6B",
            "execution_allowed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6b_prep_one_shot_draft_creation_runner_policy.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6b_prep_one_shot_draft_creation_runner_plan.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy_path = Path(args.policy)
    output_path = Path(args.output)

    policy = load_json(policy_path)
    errors: list[str] = []
    validate_policy(policy, errors)
    if errors:
        raise SystemExit("; ".join(errors))

    plan = build_plan(policy)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"status": "PASS", "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
