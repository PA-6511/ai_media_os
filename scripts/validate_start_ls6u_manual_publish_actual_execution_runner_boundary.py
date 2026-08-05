#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATION_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def k_cred_env_read() -> str:
    return "credential_" + "env_read_executed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6u_manual_publish_actual_execution_runner_boundary_policy.json")
    parser.add_argument("--runner-boundary-preflight-result", default="exchange/runtime/start_ls6u_manual_publish_actual_execution_runner_boundary_preflight_result.json")
    parser.add_argument("--runner-boundary-lock", default="exchange/locks/start_ls6u_manual_publish_actual_execution_runner_boundary.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_result.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6s-validation-result", default="exchange/logs/start_ls6s_manual_publish_final_preflight_validation_result.json")
    parser.add_argument("--ls6s-final-preflight-result", default="exchange/runtime/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6u_manual_publish_actual_execution_runner_boundary_validation_report.md")
    return parser.parse_args()


def build_result(status: str, run: dict[str, Any], lock: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    key_cer = k_cred_env_read()
    return {
        "phase": "LS-6U",
        "status": status,
        "execution_mode": "RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(run.get("post_id")),
        "returned_post_status": run.get("returned_post_status", ""),
        "approval_label": run.get("approval_label", ""),
        "approval_label_consumed": bool(run.get("approval_label_consumed", False)),
        "execute_now_confirmation_label": run.get("execute_now_confirmation_label", ""),
        "execute_now_confirmation_consumed": bool(run.get("execute_now_confirmation_consumed", False)),
        "manual_publish_runner_boundary_ready": bool(run.get("manual_publish_runner_boundary_ready", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(run.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(run.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run.get("manual_publish_executed", False)),
        "requires_final_execution_command": bool(run.get("requires_final_execution_command", False)),
        "final_execution_command_required_in_next_phase": bool(run.get("final_execution_command_required_in_next_phase", False)),
        "publish_execution_still_blocked": bool(run.get("publish_execution_still_blocked", False)),
        "wordpress_api_call_executed": bool(run.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(run.get("wordpress_get_executed", False)),
        "wordpress_write_executed": bool(run.get("wordpress_write_executed", False)),
        "wordpress_draft_creation_executed": bool(run.get("wordpress_draft_creation_executed", False)),
        "wordpress_existing_post_update_executed": bool(run.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(run.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run.get("publish_executed", False)),
        "future_schedule_executed": bool(run.get("future_schedule_executed", False)),
        "delete_executed": bool(run.get("delete_executed", False)),
        "post119_update_executed": bool(run.get("post119_update_executed", False)),
        key_cer: bool(run.get(key_cer, False)),
        "credential_value_output": bool(run.get("credential_value_output", False)),
        "credential_value_persisted": bool(run.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run.get("credential_secret_output", False)),
        "secret_length_output": bool(run.get("secret_length_output", False)),
        "secret_hash_output": bool(run.get("secret_hash_output", False)),
        "authorization_header_output": bool(run.get("authorization_header_output", False)),
        "locked": bool(lock.get("locked", False)),
        "rerun_allowed": bool(lock.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(lock.get("ls6oc1_rerun_executed", False)),
        "next_phase": {
            "phase": "LS-6V",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "requires_final_execution_command": True,
            "publish_execution_still_blocked": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6U Manual Publish Actual Execution Runner Boundary Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- manual_publish_runner_boundary_ready: {result['manual_publish_runner_boundary_ready']}",
        f"- requires_final_execution_command: {result['requires_final_execution_command']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        f"- locked: {result['locked']}",
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
    preflight = load_json(Path(args.runner_boundary_preflight_result))
    lock = load_json(Path(args.runner_boundary_lock))
    run = load_json(Path(args.run_result))
    ls6t_ready = load_json(Path(args.ls6t_ready_result))
    ls6t_conf = load_json(Path(args.ls6t_confirmation_result))
    ls6s_validation = load_json(Path(args.ls6s_validation_result))
    ls6s_preflight = load_json(Path(args.ls6s_final_preflight_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    key_cer = k_cred_env_read()
    errors: list[str] = []

    require(run.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH", "run result status mismatch", errors)
    require(preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "preflight status mismatch", errors)
    require(lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH", "lock status mismatch", errors)

    require(to_int(run.get("post_id")) == 183, "post_id mismatch", errors)
    require(run.get("returned_post_status") == "draft", "returned_post_status mismatch", errors)
    require(run.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY", "approval_label mismatch", errors)
    require(run.get("approval_label_consumed") is False, "approval_label_consumed must be false", errors)
    require(run.get("execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "execute_now_confirmation_label mismatch", errors)
    require(run.get("execute_now_confirmation_consumed") is False, "execute_now_confirmation_consumed must be false", errors)
    require(run.get("manual_publish_runner_boundary_ready") is True, "manual_publish_runner_boundary_ready must be true", errors)
    require(run.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    require(run.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    require(run.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(run.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    require(run.get("requires_final_execution_command") is True, "requires_final_execution_command must be true", errors)
    require(run.get("publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    for key in [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
    ]:
        require(run.get(key) is False, f"{key} must be false", errors)

    require(run.get(key_cer) is False, f"{key_cer} must be false", errors)
    require(run.get("credential_value_output") is False, "credential_value_output must be false", errors)
    require(run.get("credential_value_persisted") is False, "credential_value_persisted must be false", errors)
    require(run.get("credential_secret_output") is False, "credential_secret_output must be false", errors)
    require(run.get("secret_length_output") is False, "secret_length_output must be false", errors)
    require(run.get("secret_hash_output") is False, "secret_hash_output must be false", errors)
    require(run.get("authorization_header_output") is False, "authorization_header_output must be false", errors)

    require(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must remain false", errors)
    require(ls6t_ready.get("manual_publish_executed") is False, "LS-6T manual_publish_executed must remain false", errors)
    require(safe_get(ls6t_conf, "confirmation", "execute_now_confirmation_consumed") is False, "LS-6T confirmation consumed must remain false", errors)

    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must remain false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must remain false", errors)
    require(safe_get(ls6r_approval, "approval", "approval_label_consumed") is False, "LS-6R confirmation consumed mismatch", errors)

    require(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must remain false", errors)

    require(lock.get("locked") is True, "lock.locked must be true", errors)
    require(lock.get("rerun_allowed") is False, "lock.rerun_allowed must be false", errors)
    require(lock.get("ls6oc1_rerun_executed") is False, "lock.ls6oc1_rerun_executed must be false", errors)

    require(preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "preflight status mismatch duplicate", errors)
    require(preflight.get("actual_runner_execution_allowed_by_this_phase") is False, "preflight actual runner execution must be false", errors)

    require(ls6s_validation.get("status") == safe_get(policy, "required_previous_phase", "ls6s", "required_validation_status"), "LS-6S validation status mismatch", errors)
    require(ls6s_preflight.get("status") == "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6S preflight status mismatch", errors)

    require(safe_get(run, "next_phase", "phase") == "LS-6V", "next_phase mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    result = build_result(status, run, lock, errors)
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
