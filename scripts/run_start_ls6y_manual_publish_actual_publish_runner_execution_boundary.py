#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY"
STATUS_NOT_READY_MISSING_BOUNDARY_FLAG = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_BOUNDARY_FLAG"
STATUS_NOT_READY_MISSING_FINAL_EXPLICIT_COMMAND_FLAG = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_FINAL_EXPLICIT_COMMAND_FLAG"
STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_PHASE_FLAG = "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_NOT_READY_MISSING_SEPARATED_EXECUTION_PHASE_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_policy.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6w-validation-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_result.json")
    parser.add_argument("--ls6w-final-runner-preflight-result", default="exchange/runtime/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--ls6w-final-runner-preflight-lock", default="exchange/locks/start_ls6w_manual_publish_actual_execution_final_runner_preflight.lock.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--actual-publish-runner-boundary-preflight-output", default="exchange/runtime/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_preflight_result.json")
    parser.add_argument("--actual-publish-runner-boundary-lock-output", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_result.json")
    parser.add_argument("--report", default="reports/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_report.md")
    parser.add_argument("--record-actual-publish-runner-boundary", action="store_true")
    parser.add_argument("--require-final-explicit-publish-execution-command", action="store_true")
    parser.add_argument("--require-separated-actual-publish-execution-phase", action="store_true")
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
        "# LS-6Y Manual Publish Actual Publish Runner Execution Boundary Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- actual_publish_execution_gate_label: {result['actual_publish_execution_gate_label']}",
        f"- actual_publish_runner_boundary_ready: {result['actual_publish_runner_boundary_ready']}",
        f"- actual_publish_runner_boundary_consumed: {result['actual_publish_runner_boundary_consumed']}",
        f"- requires_final_explicit_publish_execution_command: {result['requires_final_explicit_publish_execution_command']}",
        f"- requires_separate_actual_publish_execution_phase: {result['requires_separate_actual_publish_execution_phase']}",
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


def get_gate_label(gate_doc: dict[str, Any], ready_doc: dict[str, Any]) -> str:
    nested = safe_get(gate_doc, "actual_publish_execution_gate", "actual_publish_execution_gate_label")
    if isinstance(nested, str) and nested:
        return nested
    top = ready_doc.get("actual_publish_execution_gate_label")
    if isinstance(top, str):
        return top
    return ""


def get_final_command_label(ls6v_ready: dict[str, Any], ls6v_command: dict[str, Any]) -> str:
    nested = safe_get(ls6v_command, "final_execution_command", "final_execution_command_label")
    if isinstance(nested, str) and nested:
        return nested
    top = ls6v_ready.get("final_execution_command_label")
    if isinstance(top, str):
        return top
    return ""


def bool_from_sources(*values: Any) -> bool:
    for v in values:
        if isinstance(v, bool):
            return v
    return False


def build_preflight_result(post_id: int, returned_status: str, gate_label: str, final_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6Y",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_FAILED_NO_PUBLISH",
        "post_id": post_id,
        "returned_post_status": returned_status,
        "actual_publish_execution_gate_label": gate_label,
        "actual_publish_execution_gate_consumed": False,
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_final_explicit_publish_execution_command": True,
        "requires_separate_actual_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        key_c(): False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": list(errors),
    }


def build_lock(post_id: int, gate_label: str, final_label: str) -> dict[str, Any]:
    return {
        "phase": "LS-6Y",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": "draft",
        "actual_publish_execution_gate_label": gate_label,
        "actual_publish_execution_gate_consumed": False,
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6Z",
        "requires_final_explicit_publish_execution_command": True,
        "requires_separate_actual_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, post_id: int, returned_status: str, gate_label: str, final_label: str, approval_label: str, execute_now_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6Y",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "returned_post_status": returned_status,
        "actual_publish_execution_gate_label": gate_label,
        "actual_publish_execution_gate_consumed": False,
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": False,
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "execute_now_confirmation_label": execute_now_label,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_final_explicit_publish_execution_command": True,
        "requires_separate_actual_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        key_c(): False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
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


def write_final_outputs(
    *,
    output_path: Path,
    report_path: Path,
    preflight_path: Path,
    lock_path: Path,
    status: str,
    post_id: int,
    returned_status: str,
    gate_label: str,
    final_label: str,
    approval_label: str,
    execute_now_label: str,
    errors: list[str],
) -> dict[str, Any]:
    preflight = build_preflight_result(post_id, returned_status, gate_label, final_label, errors if status != STATUS_PASSED else [])
    lock = build_lock(post_id, gate_label, final_label)
    result = build_run_result(status, post_id, returned_status, gate_label, final_label, approval_label, execute_now_label, errors)
    write_json(preflight_path, preflight)
    write_json(lock_path, lock)
    write_json(output_path, result)
    write_report(report_path, result)
    return result


def main() -> int:
    args = parse_args()

    if not args.record_actual_publish_runner_boundary:
        result = build_run_result(
            STATUS_NOT_READY_MISSING_BOUNDARY_FLAG,
            183,
            "",
            "",
            "",
            "",
            "",
            ["missing --record-actual-publish-runner-boundary"],
        )
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.require_final_explicit_publish_execution_command:
        result = build_run_result(
            STATUS_NOT_READY_MISSING_FINAL_EXPLICIT_COMMAND_FLAG,
            183,
            "",
            "",
            "",
            "",
            "",
            ["missing --require-final-explicit-publish-execution-command"],
        )
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.require_separated_actual_publish_execution_phase:
        result = build_run_result(
            STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_PHASE_FLAG,
            183,
            "",
            "",
            "",
            "",
            "",
            ["missing --require-separated-actual-publish-execution-phase"],
        )
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6w_validation = try_load_json(Path(args.ls6w_validation_result), errors)
    ls6w_preflight = try_load_json(Path(args.ls6w_final_runner_preflight_result), errors)
    ls6w_lock = try_load_json(Path(args.ls6w_final_runner_preflight_lock), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6v_command = try_load_json(Path(args.ls6v_command_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6t_confirmation = try_load_json(Path(args.ls6t_confirmation_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6r_approval = try_load_json(Path(args.ls6r_approval_result), errors)
    ls6p_lock = try_load_json(Path(args.ls6p_rerun_prevention_lock), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    target = policy.get("target_post", {})
    post_id = to_int(target.get("post_id"), 183)

    req(policy.get("phase") == "LS-6Y", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)
    req(post_id == 183, "target_post.post_id mismatch", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X ready status mismatch", errors)
    req(ls6x_ready.get("gate_status") == "ACTUAL_PUBLISH_EXECUTION_GATE_RECORDED_NO_PUBLISH_EXECUTION", "LS-6X gate_status mismatch", errors)
    req(ls6x_ready.get("returned_post_status") == "draft", "LS-6X returned_post_status mismatch", errors)
    req(to_int(ls6x_ready.get("post_id")) == 183, "LS-6X post_id mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6X gate label mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X actual_publish_execution_gate_consumed must be false", errors)
    req(ls6x_ready.get("final_execution_command_consumed") is False, "LS-6X final_execution_command_consumed must be false", errors)
    req(ls6x_ready.get("approval_label_consumed") is False, "LS-6X approval_label_consumed must be false", errors)
    req(ls6x_ready.get("execute_now_confirmation_consumed") is False, "LS-6X execute_now_confirmation_consumed must be false", errors)
    req(ls6x_ready.get("actual_publish_execution_allowed_by_this_phase") is False, "LS-6X actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(ls6x_ready.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6X actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(ls6x_ready.get("manual_publish_allowed_by_this_phase") is False, "LS-6X manual_publish_allowed_by_this_phase must be false", errors)
    req(ls6x_ready.get("manual_publish_execution_allowed_by_this_phase") is False, "LS-6X manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(ls6x_ready.get("manual_publish_executed") is False, "LS-6X manual_publish_executed must be false", errors)
    req(ls6x_ready.get("requires_next_actual_publish_runner_phase") is True, "LS-6X requires_next_actual_publish_runner_phase must be true", errors)
    req(ls6x_ready.get("publish_execution_still_blocked") is True, "LS-6X publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6x_ready, "next_phase", "phase") == "LS-6Y", "LS-6X next_phase mismatch", errors)

    req(ls6x_gate.get("gate_status") == "ACTUAL_PUBLISH_EXECUTION_GATE_RECORDED_NO_PUBLISH_EXECUTION", "LS-6X gate result status mismatch", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6X gate result label mismatch", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate result consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "manual_publish_executed") is False, "LS-6X gate result manual_publish_executed must be false", errors)

    req(ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6W validation status mismatch", errors)
    req(ls6w_validation.get("returned_post_status") == "draft", "LS-6W returned_post_status mismatch", errors)
    req(ls6w_validation.get("draft_verified") is True, "LS-6W draft_verified must be true", errors)
    req(ls6w_validation.get("final_execution_command_consumed") is False, "LS-6W final_execution_command_consumed must be false", errors)
    req(ls6w_validation.get("requires_separate_publish_execution") is True, "LS-6W requires_separate_publish_execution must be true", errors)
    req(ls6w_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W preflight status mismatch", errors)
    req(ls6w_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6W lock status mismatch", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("command_status") == "FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6V command_status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6V final_execution_command_label mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must be false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command final_execution_command_consumed must be false", errors)
    req(ls6v_ready.get("manual_publish_executed") is False, "LS-6V manual_publish_executed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    req(ls6t_confirmation.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    req(ls6r_ready.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY", "LS-6R approval_label mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    req(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    gate_label = get_gate_label(ls6x_gate, ls6x_ready)
    final_label = get_final_command_label(ls6v_ready, ls6v_command)
    approval_label = str(ls6r_ready.get("approval_label", ""))
    execute_now_label = str(ls6t_ready.get("execute_now_confirmation_label", ""))
    returned_status = str(ls6x_ready.get("returned_post_status", ""))

    preflight_output = Path(args.actual_publish_runner_boundary_preflight_output)
    lock_output = Path(args.actual_publish_runner_boundary_lock_output)
    result_output = Path(args.output)
    report_output = Path(args.report)

    status = STATUS_PASSED if not errors else STATUS_NOT_READY
    result = write_final_outputs(
        output_path=result_output,
        report_path=report_output,
        preflight_path=preflight_output,
        lock_path=lock_output,
        status=status,
        post_id=post_id,
        returned_status=returned_status,
        gate_label=gate_label,
        final_label=final_label,
        approval_label=approval_label,
        execute_now_label=execute_now_label,
        errors=errors,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        fallback = {
            "phase": "LS-6Y",
            "status": STATUS_FAILED,
            "execution_mode": "ACTUAL_PUBLISH_RUNNER_BOUNDARY_PREFLIGHT_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "post_id": 183,
            "returned_post_status": "",
            "actual_publish_execution_gate_label": "",
            "actual_publish_execution_gate_consumed": False,
            "actual_publish_runner_boundary_ready": False,
            "actual_publish_runner_boundary_consumed": False,
            "final_execution_command_label": "",
            "final_execution_command_consumed": False,
            "approval_label_consumed": False,
            "execute_now_confirmation_consumed": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "manual_publish_allowed_by_this_phase": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "manual_publish_executed": False,
            "requires_final_explicit_publish_execution_command": True,
            "requires_separate_actual_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
            "wordpress_api_call_executed": False,
            "wordpress_get_executed": False,
            "wordpress_post_executed": False,
            "wordpress_put_executed": False,
            "wordpress_patch_executed": False,
            "wordpress_delete_executed": False,
            "wordpress_write_executed_by_this_phase": False,
            "wordpress_draft_creation_executed_by_this_phase": False,
            "wordpress_existing_post_update_executed": False,
            "wordpress_publish_executed": False,
            "publish_executed": False,
            "future_schedule_executed": False,
            "delete_executed": False,
            "post119_update_executed": False,
            key_c(): False,
            "credential_value_output": False,
            "credential_value_persisted": False,
            "credential_secret_output": False,
            "secret_length_output": False,
            "secret_hash_output": False,
            "authorization_header_output": False,
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
            "errors": [f"unexpected_exception: {exc.__class__.__name__}"]
        }
        print(json.dumps(fallback, ensure_ascii=False, indent=2))
        raise
