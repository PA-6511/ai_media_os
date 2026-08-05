#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY"
STATUS_NOT_READY_MISSING_BOUNDARY_FLAG = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY_MISSING_BOUNDARY_FLAG"
STATUS_NOT_READY_MISSING_FINAL_COMMAND_SEPARATION_FLAG = "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_NOT_READY_MISSING_FINAL_COMMAND_SEPARATION_FLAG"


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
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6s-final-preflight-result", default="exchange/runtime/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--ls6s-final-preflight-lock", default="exchange/locks/start_ls6s_manual_publish_final_preflight.lock.json")
    parser.add_argument("--ls6s-run-result", default="exchange/logs/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--ls6s-validation-result", default="exchange/logs/start_ls6s_manual_publish_final_preflight_validation_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-execution-result", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--runner-boundary-preflight-output", default="exchange/runtime/start_ls6u_manual_publish_actual_execution_runner_boundary_preflight_result.json")
    parser.add_argument("--runner-boundary-lock-output", default="exchange/locks/start_ls6u_manual_publish_actual_execution_runner_boundary.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_result.json")
    parser.add_argument("--report", default="reports/start_ls6u_manual_publish_actual_execution_runner_boundary_report.md")
    parser.add_argument("--record-runner-boundary", action="store_true")
    parser.add_argument("--require-final-execution-command-separation", action="store_true")
    return parser.parse_args()


def build_preflight_result(post_id: int, returned_status: str, approval_label: str, execute_label: str, errors: list[str]) -> dict[str, Any]:
    key_cer = k_cred_env_read()
    return {
        "phase": "LS-6U",
        "document_type": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_FAILED_NO_PUBLISH",
        "post_id": post_id,
        "returned_post_status": returned_status,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "execute_now_confirmation_label": execute_label,
        "execute_now_confirmation_consumed": False,
        "manual_publish_runner_boundary_ready": True,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_final_execution_command": True,
        "final_execution_command_required_in_next_phase": True,
        "publish_execution_still_blocked": True,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        key_cer: False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": errors,
    }


def build_lock(post_id: int, returned_status: str, approval_label: str, execute_label: str) -> dict[str, Any]:
    return {
        "phase": "LS-6U",
        "document_type": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": returned_status,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "execute_now_confirmation_label": execute_label,
        "execute_now_confirmation_consumed": False,
        "manual_publish_runner_boundary_ready": True,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6V",
        "requires_final_execution_command": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, post_id: int, returned_status: str, approval_label: str, execute_label: str, errors: list[str]) -> dict[str, Any]:
    key_cer = k_cred_env_read()
    return {
        "phase": "LS-6U",
        "status": status,
        "execution_mode": "RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "returned_post_status": returned_status,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "execute_now_confirmation_label": execute_label,
        "execute_now_confirmation_consumed": False,
        "manual_publish_runner_boundary_ready": True,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_final_execution_command": True,
        "final_execution_command_required_in_next_phase": True,
        "publish_execution_still_blocked": True,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        key_cer: False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
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
        "# LS-6U Manual Publish Actual Execution Runner Boundary Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- approval_label: {result['approval_label']}",
        f"- execute_now_confirmation_label: {result['execute_now_confirmation_label']}",
        f"- manual_publish_runner_boundary_ready: {result['manual_publish_runner_boundary_ready']}",
        f"- actual_runner_execution_allowed_by_this_phase: {result['actual_runner_execution_allowed_by_this_phase']}",
        f"- manual_publish_executed: {result['manual_publish_executed']}",
        f"- requires_final_execution_command: {result['requires_final_execution_command']}",
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
    target_post = policy.get("target_post", {})
    post_id = to_int(target_post.get("post_id"))

    if not args.record_runner_boundary:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_BOUNDARY_FLAG,
            post_id=post_id,
            returned_status="",
            approval_label=str(safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label") or ""),
            execute_label=str(safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label") or ""),
            errors=["--record-runner-boundary is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.require_final_execution_command_separation:
        result = build_run_result(
            status=STATUS_NOT_READY_MISSING_FINAL_COMMAND_SEPARATION_FLAG,
            post_id=post_id,
            returned_status="",
            approval_label=str(safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label") or ""),
            execute_label=str(safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label") or ""),
            errors=["--require-final-execution-command-separation is required"],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    required_paths = [
        Path(args.policy),
        Path(args.ls6t_ready_result),
        Path(args.ls6t_confirmation_result),
        Path(args.ls6s_final_preflight_result),
        Path(args.ls6s_final_preflight_lock),
        Path(args.ls6s_run_result),
        Path(args.ls6s_validation_result),
        Path(args.ls6r_ready_result),
        Path(args.ls6r_approval_result),
        Path(args.ls6p_rerun_prevention_lock),
        Path(args.ls6oc1_execution_result),
        Path(args.ls6oc1_consumption_lock),
    ]
    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        result = build_run_result(
            status=STATUS_NOT_READY,
            post_id=post_id,
            returned_status="",
            approval_label=str(safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label") or ""),
            execute_label=str(safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label") or ""),
            errors=[f"missing required input: {m}" for m in missing],
        )
        write_json(Path(args.output), result)
        write_report(result, Path(args.report))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    ls6t_ready = load_json(Path(args.ls6t_ready_result))
    ls6t_conf = load_json(Path(args.ls6t_confirmation_result))
    ls6s_preflight = load_json(Path(args.ls6s_final_preflight_result))
    ls6s_lock = load_json(Path(args.ls6s_final_preflight_lock))
    ls6s_run = load_json(Path(args.ls6s_run_result))
    ls6s_validation = load_json(Path(args.ls6s_validation_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6oc1_exec = load_json(Path(args.ls6oc1_execution_result))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    errors: list[str] = []

    require(ls6t_ready.get("status") == safe_get(policy, "required_previous_phase", "ls6t", "required_ready_status"), "LS-6T ready status mismatch", errors)
    require(ls6t_ready.get("confirmation_status") == safe_get(policy, "required_previous_phase", "ls6t", "required_confirmation_status"), "LS-6T confirmation status mismatch", errors)
    require(ls6t_ready.get("execute_now_confirmation_label") == safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label"), "LS-6T execute label mismatch", errors)
    require(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    require(ls6t_ready.get("manual_publish_executed") is False, "LS-6T manual_publish_executed must be false", errors)
    require(ls6t_ready.get("publish_execution_still_blocked") is True, "LS-6T publish_execution_still_blocked must be true", errors)

    require(ls6t_conf.get("confirmation_status") == safe_get(policy, "required_previous_phase", "ls6t", "required_confirmation_status"), "LS-6T confirmation result status mismatch", errors)
    require(safe_get(ls6t_conf, "confirmation", "execute_now_confirmation_label") == safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label"), "LS-6T confirmation result label mismatch", errors)
    require(safe_get(ls6t_conf, "confirmation", "execute_now_confirmation_consumed") is False, "LS-6T confirmation result consumed mismatch", errors)
    require(safe_get(ls6t_conf, "confirmation", "manual_publish_executed") is False, "LS-6T confirmation result manual publish executed mismatch", errors)

    require(ls6s_run.get("status") == safe_get(policy, "required_previous_phase", "ls6s", "required_run_status"), "LS-6S run status mismatch", errors)
    require(ls6s_validation.get("status") == safe_get(policy, "required_previous_phase", "ls6s", "required_validation_status"), "LS-6S validation status mismatch", errors)
    require(ls6s_validation.get("approval_label_consumed") is False, "LS-6S approval_label_consumed must be false", errors)
    require(ls6s_validation.get("manual_publish_executed") is False, "LS-6S manual_publish_executed must be false", errors)
    require(ls6s_validation.get("publish_execution_still_blocked") is True, "LS-6S publish_execution_still_blocked must be true", errors)
    require(ls6s_preflight.get("returned_post_status") == "draft", "LS-6S returned_post_status mismatch", errors)
    require(ls6s_lock.get("status") == "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6S lock status mismatch", errors)

    require(ls6r_ready.get("status") == safe_get(policy, "required_previous_phase", "ls6r", "required_ready_status"), "LS-6R ready status mismatch", errors)
    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must be false", errors)
    require(safe_get(ls6r_approval, "approval", "approval_label_consumed") is False, "LS-6R approval result consumed mismatch", errors)

    require(ls6p_lock.get("locked") is True, "LS-6P lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)

    require(to_int(ls6oc1_exec.get("new_post_id", ls6oc1_exec.get("post_id"))) == post_id, "LS-6O-C-1 post_id mismatch", errors)
    require(ls6oc1_exec.get("returned_post_status") == safe_get(policy, "required_previous_phase", "ls6oc1", "required_returned_post_status"), "LS-6O-C-1 returned_post_status mismatch", errors)
    require(to_int(ls6oc1_exec.get("created_count")) == to_int(safe_get(policy, "required_previous_phase", "ls6oc1", "required_created_count")), "LS-6O-C-1 created_count mismatch", errors)
    require(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    approval_label = str(safe_get(policy, "required_previous_phase", "ls6r", "required_approval_label") or "")
    execute_label = str(safe_get(policy, "required_previous_phase", "ls6t", "required_execute_now_confirmation_label") or "")

    if errors:
        preflight = build_preflight_result(post_id, "", approval_label, execute_label, errors)
        run_result = build_run_result(STATUS_NOT_READY, post_id, "", approval_label, execute_label, errors)
        write_json(Path(args.runner_boundary_preflight_output), preflight)
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    returned_status = "draft"
    preflight = build_preflight_result(post_id, returned_status, approval_label, execute_label, [])
    lock = build_lock(post_id, returned_status, approval_label, execute_label)
    run_result = build_run_result(STATUS_PASSED, post_id, returned_status, approval_label, execute_label, [])

    write_json(Path(args.runner_boundary_preflight_output), preflight)
    write_json(Path(args.runner_boundary_lock_output), lock)
    write_json(Path(args.output), run_result)
    write_report(run_result, Path(args.report))
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
