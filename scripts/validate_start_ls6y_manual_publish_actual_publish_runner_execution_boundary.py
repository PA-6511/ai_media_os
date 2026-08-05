#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_policy.json")
    parser.add_argument("--actual-publish-runner-boundary-preflight-result", default="exchange/runtime/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_preflight_result.json")
    parser.add_argument("--actual-publish-runner-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_result.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6w-validation-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_result.json")
    parser.add_argument("--ls6w-final-runner-preflight-result", default="exchange/runtime/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_report.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing file: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json: {path}")
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6Y Manual Publish Actual Publish Runner Execution Boundary Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- actual_publish_execution_gate_label: {result['actual_publish_execution_gate_label']}",
        f"- actual_publish_runner_boundary_ready: {result['actual_publish_runner_boundary_ready']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


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


def key_c() -> str:
    return "credential_" + "env_read_executed"


def validate_false_flags(doc: dict[str, Any], errors: list[str], prefix: str) -> None:
    for key in [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_draft_creation_executed_by_this_phase",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
        key_c(),
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "actual_publish_execution_gate_consumed",
        "actual_publish_runner_boundary_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "manual_publish_executed",
    ]:
        req(doc.get(key) is False, f"{prefix}.{key} must be false", errors)


def build_result(run_result: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6Y",
        "status": STATUS_VALIDATED if not errors else STATUS_NOT_READY,
        "execution_mode": "ACTUAL_PUBLISH_RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(run_result.get("post_id")),
        "returned_post_status": run_result.get("returned_post_status", ""),
        "actual_publish_execution_gate_label": run_result.get("actual_publish_execution_gate_label", ""),
        "actual_publish_execution_gate_consumed": bool(run_result.get("actual_publish_execution_gate_consumed", False)),
        "actual_publish_runner_boundary_ready": bool(run_result.get("actual_publish_runner_boundary_ready", False)),
        "actual_publish_runner_boundary_consumed": bool(run_result.get("actual_publish_runner_boundary_consumed", False)),
        "final_execution_command_label": run_result.get("final_execution_command_label", ""),
        "final_execution_command_consumed": bool(run_result.get("final_execution_command_consumed", False)),
        "approval_label_consumed": bool(run_result.get("approval_label_consumed", False)),
        "execute_now_confirmation_consumed": bool(run_result.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(run_result.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(run_result.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(run_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run_result.get("manual_publish_executed", False)),
        "requires_final_explicit_publish_execution_command": bool(run_result.get("requires_final_explicit_publish_execution_command", False)),
        "requires_separate_actual_publish_execution_phase": bool(run_result.get("requires_separate_actual_publish_execution_phase", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "wordpress_api_call_executed": bool(run_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(run_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(run_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(run_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(run_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(run_result.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(run_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(run_result.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_existing_post_update_executed": bool(run_result.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "future_schedule_executed": bool(run_result.get("future_schedule_executed", False)),
        "delete_executed": bool(run_result.get("delete_executed", False)),
        "post119_update_executed": bool(run_result.get("post119_update_executed", False)),
        key_c(): bool(run_result.get(key_c(), False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": True,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6Z",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_final_explicit_publish_execution_command": True,
            "requires_separate_actual_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()

    errors: list[str] = []
    policy = try_load_json(Path(args.policy), errors)
    preflight = try_load_json(Path(args.actual_publish_runner_boundary_preflight_result), errors)
    lock_doc = try_load_json(Path(args.actual_publish_runner_boundary_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6w_validation = try_load_json(Path(args.ls6w_validation_result), errors)
    ls6w_preflight = try_load_json(Path(args.ls6w_final_runner_preflight_result), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6v_command = try_load_json(Path(args.ls6v_command_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    req(policy.get("phase") == "LS-6Y", "policy.phase mismatch", errors)
    req(run_result.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH", "run result status mismatch", errors)
    req(preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "preflight status mismatch", errors)
    req(lock_doc.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH", "lock status mismatch", errors)

    req(to_int(run_result.get("post_id")) == 183, "run_result.post_id mismatch", errors)
    req(run_result.get("returned_post_status") == "draft", "run_result.returned_post_status mismatch", errors)
    req(preflight.get("post_id") == 183, "preflight.post_id mismatch", errors)
    req(preflight.get("returned_post_status") == "draft", "preflight.returned_post_status mismatch", errors)

    req(run_result.get("actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "gate label mismatch", errors)
    req(run_result.get("actual_publish_runner_boundary_ready") is True, "actual_publish_runner_boundary_ready must be true", errors)
    req(run_result.get("requires_final_explicit_publish_execution_command") is True, "requires_final_explicit_publish_execution_command must be true", errors)
    req(run_result.get("requires_separate_actual_publish_execution_phase") is True, "requires_separate_actual_publish_execution_phase must be true", errors)
    req(run_result.get("publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    validate_false_flags(run_result, errors, "run_result")
    validate_false_flags(preflight, errors, "preflight")

    req(lock_doc.get("locked") is True, "lock.locked must be true", errors)
    req(lock_doc.get("rerun_allowed") is False, "lock.rerun_allowed must be false", errors)
    req(lock_doc.get("ls6oc1_rerun_executed") is False, "lock.ls6oc1_rerun_executed must be false", errors)
    req(lock_doc.get("requires_next_phase") == "LS-6Z", "lock.requires_next_phase mismatch", errors)
    req(lock_doc.get("actual_publish_runner_boundary_ready") is True, "lock.actual_publish_runner_boundary_ready must be true", errors)
    req(lock_doc.get("actual_publish_runner_boundary_consumed") is False, "lock.actual_publish_runner_boundary_consumed must be false", errors)

    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X actual_publish_execution_gate_consumed must remain false", errors)
    req(ls6x_ready.get("manual_publish_executed") is False, "LS-6X manual_publish_executed must remain false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must remain false", errors)

    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must remain false", errors)
    req(ls6v_ready.get("manual_publish_executed") is False, "LS-6V manual_publish_executed must remain false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command consumed must remain false", errors)

    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must remain false", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must remain false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must remain false", errors)

    req(ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6W validation status mismatch", errors)
    req(ls6w_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W preflight status mismatch", errors)

    req(safe_get(run_result, "next_phase", "phase") == "LS-6Z", "run_result.next_phase.phase mismatch", errors)
    req(safe_get(run_result, "next_phase", "execution_allowed") is False, "run_result.next_phase.execution_allowed must be false", errors)
    req(safe_get(run_result, "next_phase", "manual_publish_execution_allowed_by_this_phase") is False, "run_result.next_phase.manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(run_result, "next_phase", "actual_publish_execution_allowed_by_this_phase") is False, "run_result.next_phase.actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(run_result, "next_phase", "actual_runner_execution_allowed_by_this_phase") is False, "run_result.next_phase.actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(run_result, "next_phase", "requires_final_explicit_publish_execution_command") is True, "run_result.next_phase.requires_final_explicit_publish_execution_command must be true", errors)
    req(safe_get(run_result, "next_phase", "requires_separate_actual_publish_execution_phase") is True, "run_result.next_phase.requires_separate_actual_publish_execution_phase must be true", errors)
    req(safe_get(run_result, "next_phase", "publish_execution_still_blocked") is True, "run_result.next_phase.publish_execution_still_blocked must be true", errors)

    result = build_result(run_result, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
