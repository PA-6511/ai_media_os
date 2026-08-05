#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATION_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6w_manual_publish_actual_execution_final_runner_preflight_policy.json")
    parser.add_argument("--wordpress-current-draft-status-result", default="exchange/runtime/start_ls6w_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--final-runner-preflight-result", default="exchange/runtime/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--final-runner-preflight-lock", default="exchange/locks/start_ls6w_manual_publish_actual_execution_final_runner_preflight.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6u-validation-result", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_validation_result.json")
    parser.add_argument("--ls6u-runner-boundary-lock", default="exchange/locks/start_ls6u_manual_publish_actual_execution_runner_boundary.lock.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_report.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_result(status: str, run_result: dict[str, Any], lock: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6W",
        "status": status,
        "execution_mode": "FINAL_RUNNER_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": run_result.get("post_id", 0),
        "draft_verified": bool(run_result.get("draft_verified", False)),
        "returned_post_status": run_result.get("returned_post_status", ""),
        "wordpress_get_executed": bool(run_result.get("wordpress_get_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(run_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(run_result.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_publish_executed": bool(run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "future_schedule_executed": bool(run_result.get("future_schedule_executed", False)),
        "delete_executed": bool(run_result.get("delete_executed", False)),
        "post119_update_executed": bool(run_result.get("post119_update_executed", False)),
        "final_execution_command_label": run_result.get("final_execution_command_label", ""),
        "final_execution_command_consumed": bool(run_result.get("final_execution_command_consumed", False)),
        "approval_label_consumed": bool(run_result.get("approval_label_consumed", False)),
        "execute_now_confirmation_consumed": bool(run_result.get("execute_now_confirmation_consumed", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(run_result.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(run_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run_result.get("manual_publish_executed", False)),
        "requires_separate_publish_execution": bool(run_result.get("requires_separate_publish_execution", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": bool(lock.get("locked", False)),
        "rerun_allowed": bool(lock.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(lock.get("ls6oc1_rerun_executed", False)),
        "next_phase": {
            "phase": "LS-6X",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_separate_publish_execution": True,
            "publish_execution_still_blocked": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6W Manual Publish Actual Execution Final Runner Preflight Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- final_execution_command_label: {result['final_execution_command_label']}",
        f"- requires_separate_publish_execution: {result['requires_separate_publish_execution']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    wp_result = load_json(Path(args.wordpress_current_draft_status_result))
    final_preflight = load_json(Path(args.final_runner_preflight_result))
    lock = load_json(Path(args.final_runner_preflight_lock))
    run_result = load_json(Path(args.run_result))
    ls6v_ready = load_json(Path(args.ls6v_ready_result))
    ls6v_command = load_json(Path(args.ls6v_command_result))
    ls6u_validation = load_json(Path(args.ls6u_validation_result))
    ls6u_lock = load_json(Path(args.ls6u_runner_boundary_lock))
    ls6t_ready = load_json(Path(args.ls6t_ready_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    errors: list[str] = []

    req(policy.get("phase") == "LS-6W", "policy phase mismatch", errors)
    req(run_result.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "run status mismatch", errors)
    req(run_result.get("returned_post_status") == "draft", "run returned_post_status mismatch", errors)
    req(run_result.get("wordpress_write_executed_by_this_phase") is False, "run wordpress_write_executed_by_this_phase must be false", errors)
    req(run_result.get("wordpress_publish_executed") is False, "run wordpress_publish_executed must be false", errors)
    req(run_result.get("publish_executed") is False, "run publish_executed must be false", errors)
    req(run_result.get("manual_publish_executed") is False, "run manual_publish_executed must be false", errors)
    req(run_result.get("final_execution_command_consumed") is False, "run final_execution_command_consumed must be false", errors)
    req(run_result.get("approval_label_consumed") is False, "run approval_label_consumed must be false", errors)
    req(run_result.get("execute_now_confirmation_consumed") is False, "run execute_now_confirmation_consumed must be false", errors)
    req(run_result.get("actual_runner_execution_allowed_by_this_phase") is False, "run actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(run_result.get("credential_value_output") is False, "run credential_value_output must be false", errors)
    req(run_result.get("authorization_header_output") is False, "run authorization_header_output must be false", errors)

    req(wp_result.get("status") == "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED", "wordpress current draft verification status mismatch", errors)
    req(wp_result.get("post_id") == 183, "wp post_id mismatch", errors)
    req(wp_result.get("returned_post_status") == "draft", "wp returned_post_status mismatch", errors)
    req(wp_result.get("wordpress_get_executed") is True, "wordpress_get_executed must be true", errors)
    req(wp_result.get("wordpress_get_post_id") == 183, "wordpress_get_post_id mismatch", errors)
    for key in [
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_draft_creation_executed_by_this_phase",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
    ]:
        req(wp_result.get(key) is False, f"{key} must be false", errors)

    req(final_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "final preflight status mismatch", errors)
    req(final_preflight.get("current_post_status_verified") is True, "current_post_status_verified must be true", errors)
    req(final_preflight.get("returned_post_status") == "draft", "final preflight returned_post_status mismatch", errors)
    req(final_preflight.get("final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "final_execution_command_label mismatch", errors)
    req(final_preflight.get("final_execution_command_consumed") is False, "final_execution_command_consumed must be false", errors)
    req(final_preflight.get("approval_label_consumed") is False, "approval_label_consumed must be false", errors)
    req(final_preflight.get("execute_now_confirmation_consumed") is False, "execute_now_confirmation_consumed must be false", errors)
    req(final_preflight.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(final_preflight.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    req(final_preflight.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(final_preflight.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    req(final_preflight.get("requires_separate_publish_execution") is True, "requires_separate_publish_execution must be true", errors)
    req(final_preflight.get("publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    req(lock.get("locked") is True, "lock locked must be true", errors)
    req(lock.get("rerun_allowed") is False, "lock rerun_allowed must be false", errors)
    req(lock.get("ls6oc1_rerun_executed") is False, "lock ls6oc1_rerun_executed must be false", errors)
    req(lock.get("requires_next_phase") == "LS-6X", "lock requires_next_phase mismatch", errors)

    req(final_preflight.get("credential_env_read_executed") is True, "credential_env_read_executed must be true", errors)
    for key in [
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
    ]:
        req(final_preflight.get(key) is False, f"{key} must be false", errors)

    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed changed", errors)
    req(safe_get(ls6v_command, "final_execution_command", "manual_publish_executed") is False, "LS-6V manual_publish_executed changed", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed changed", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed changed", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed changed", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V status mismatch", errors)
    req(ls6u_validation.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6U validation mismatch", errors)
    req(ls6u_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH", "LS-6U lock mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    result = build_result(status, run_result, lock, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
