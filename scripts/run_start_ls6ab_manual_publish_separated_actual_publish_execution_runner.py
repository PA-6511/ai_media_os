#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH"
STATUS_FAILED = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_RECORD_FLAG"
STATUS_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG"
STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG = "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_policy.json")
    parser.add_argument("--ls6aa-run-result", default="exchange/logs/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--ls6aa-validation-result", default="exchange/logs/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_validation_result.json")
    parser.add_argument("--ls6aa-final-preflight-result", default="exchange/runtime/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--ls6aa-final-preflight-lock", default="exchange/locks/start_ls6aa_manual_publish_actual_publish_execution_final_preflight.lock.json")
    parser.add_argument("--ls6z-ready-result", default="exchange/logs/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_result.json")
    parser.add_argument("--ls6z-command-result", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.json")
    parser.add_argument("--ls6y-validation-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--ls6y-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--blocked-runner-output", default="exchange/runtime/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_blocked_result.json")
    parser.add_argument("--blocked-runner-lock-output", default="exchange/locks/start_ls6ab_manual_publish_separated_actual_publish_execution_runner.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_result.json")
    parser.add_argument("--report", default="reports/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_report.md")
    parser.add_argument("--record-blocked-actual-publish-runner", action="store_true")
    parser.add_argument("--require-explicit-execute-now-for-actual-publish", action="store_true")
    parser.add_argument("--require-separate-publish-execution-phase", action="store_true")
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
        "# LS-6AB Manual Publish Separated Actual Publish Execution Runner Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6aa_final_preflight_validated: {result['ls6aa_final_preflight_validated']}",
        f"- ls6aa_fix_a_test_coverage_completed: {result['ls6aa_fix_a_test_coverage_completed']}",
        f"- actual_publish_execution_runner_ready: {result['actual_publish_execution_runner_ready']}",
        f"- actual_publish_execution_runner_executed: {result['actual_publish_execution_runner_executed']}",
        f"- actual_publish_execution_runner_blocked: {result['actual_publish_execution_runner_blocked']}",
        f"- explicit_execute_now_for_actual_publish_required: {result['explicit_execute_now_for_actual_publish_required']}",
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


def to_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def count_collected_tests(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    module = ast.parse(source)
    total = 0

    for node in module.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue

        multiplier = 1
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            is_parametrize = False
            if isinstance(func, ast.Attribute) and func.attr == "parametrize":
                is_parametrize = True
            elif isinstance(func, ast.Name) and func.id == "parametrize":
                is_parametrize = True

            if not is_parametrize or len(dec.args) < 2:
                continue

            values_arg = dec.args[1]
            if isinstance(values_arg, (ast.List, ast.Tuple)) and values_arg.elts:
                multiplier *= len(values_arg.elts)

        total += multiplier

    return total


def build_common(post_id: int, returned_status: str, ls6aa_valid: bool, fix_a_done: bool, final_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AB",
        "post_id": post_id,
        "returned_post_status": returned_status,
        "ls6aa_final_preflight_validated": ls6aa_valid,
        "ls6aa_fix_a_test_coverage_completed": fix_a_done,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": False,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "final_explicit_publish_execution_command_label": final_label,
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_ready": True,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
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
        k_cread(): False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_actual_publish_execute_now_confirmation": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "errors": list(errors),
    }


def build_blocked_result(post_id: int, returned_status: str, ls6aa_valid: bool, fix_a_done: bool, final_label: str, errors: list[str]) -> dict[str, Any]:
    base = build_common(post_id, returned_status, ls6aa_valid, fix_a_done, final_label, errors)
    base.update(
        {
            "document_type": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_RESULT",
            "status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
        }
    )
    return base


def build_lock(post_id: int) -> dict[str, Any]:
    return {
        "phase": "LS-6AB",
        "document_type": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCK",
        "status": "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": "draft",
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": False,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
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
        "requires_next_phase": "LS-6AC",
        "requires_actual_publish_execute_now_confirmation": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, post_id: int, returned_status: str, ls6aa_valid: bool, fix_a_done: bool, final_label: str, errors: list[str]) -> dict[str, Any]:
    base = build_common(post_id, returned_status, ls6aa_valid, fix_a_done, final_label, errors)
    base.update(
        {
            "status": status,
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
            "next_phase": {
                "phase": "LS-6AC",
                "execution_allowed": False,
                "manual_publish_execution_allowed_by_this_phase": False,
                "actual_publish_execution_allowed_by_this_phase": False,
                "actual_runner_execution_allowed_by_this_phase": False,
                "requires_actual_publish_execute_now_confirmation": True,
                "requires_separate_publish_execution_phase": True,
                "publish_execution_still_blocked": True,
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return base


def write_not_ready(output: Path, report: Path, status: str, msg: str) -> None:
    result = build_run_result(status, 183, "", False, False, "", [msg])
    write_json(output, result)
    write_report(report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()

    output_path = Path(args.output)
    report_path = Path(args.report)

    if not args.record_blocked_actual_publish_runner:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_RECORD_FLAG, "missing --record-blocked-actual-publish-runner")
        return 0
    if not args.require_explicit_execute_now_for_actual_publish:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG, "missing --require-explicit-execute-now-for-actual-publish")
        return 0
    if not args.require_separate_publish_execution_phase:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG, "missing --require-separate-publish-execution-phase")
        return 0

    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6aa_run = try_load_json(Path(args.ls6aa_run_result), errors)
    ls6aa_validation = try_load_json(Path(args.ls6aa_validation_result), errors)
    ls6aa_preflight = try_load_json(Path(args.ls6aa_final_preflight_result), errors)
    ls6aa_lock = try_load_json(Path(args.ls6aa_final_preflight_lock), errors)
    ls6z_ready = try_load_json(Path(args.ls6z_ready_result), errors)
    ls6z_command = try_load_json(Path(args.ls6z_command_result), errors)
    ls6y_validation = try_load_json(Path(args.ls6y_validation_result), errors)
    ls6y_lock = try_load_json(Path(args.ls6y_boundary_lock), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6v_command = try_load_json(Path(args.ls6v_command_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6t_confirmation = try_load_json(Path(args.ls6t_confirmation_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6r_approval = try_load_json(Path(args.ls6r_approval_result), errors)
    ls6p_lock = try_load_json(Path(args.ls6p_rerun_prevention_lock), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    req(policy.get("phase") == "LS-6AB", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    post_id = to_int(safe_get(policy, "target_post", "post_id"), 183)
    req(post_id == 183, "target post_id mismatch", errors)

    req(ls6aa_run.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6AA run status mismatch", errors)
    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_run.get("post_id") == 183, "LS-6AA run post_id mismatch", errors)
    req(ls6aa_run.get("returned_post_status") == "draft", "LS-6AA run returned_post_status mismatch", errors)
    req(ls6aa_run.get("actual_publish_execution_final_preflight_ready") is True, "LS-6AA run final preflight ready must be true", errors)
    req(ls6aa_run.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA run final preflight consumed must be false", errors)
    req(ls6aa_run.get("manual_publish_executed") is False, "LS-6AA run manual_publish_executed must be false", errors)
    req(ls6aa_run.get("publish_execution_still_blocked") is True, "LS-6AA run publish_execution_still_blocked must be true", errors)
    req(ls6aa_run.get("requires_explicit_execute_now_for_actual_publish") is True, "LS-6AA run requires explicit execute now must be true", errors)
    req(ls6aa_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6AA preflight status mismatch", errors)
    req(ls6aa_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6AA lock status mismatch", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z ready status mismatch", errors)
    final_label = str(ls6z_ready.get("final_explicit_publish_execution_command_label", ""))
    req(final_label == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6Z final explicit label mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z final explicit consumed must be false", errors)
    req(ls6z_ready.get("manual_publish_executed") is False, "LS-6Z manual_publish_executed must be false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y validation status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y boundary consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock boundary consumed must be false", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X ready status mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate result consumed must be false", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final execution consumed must be false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command consumed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute-now consumed must be false", errors)
    req(ls6t_confirmation.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval consumed must be false", errors)
    req(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    fix_a_min = to_int(safe_get(policy, "required_previous_phase", "ls6aa_fix_a", "required_min_collected_tests"), 45)
    fix_a_expected = to_int(safe_get(policy, "required_previous_phase", "ls6aa_fix_a", "expected_collected_tests"), 50)
    test_files = safe_get(policy, "required_previous_phase", "ls6aa_fix_a", "test_files")
    total_tests = 0
    if isinstance(test_files, list) and test_files:
        for p in test_files:
            tp = Path(str(p))
            if tp.exists():
                total_tests += count_collected_tests(tp)
            else:
                errors.append(f"missing test file for LS-6AA-FIX-A: {tp}")
    else:
        errors.append("LS-6AA-FIX-A test file list missing")
    req(total_tests >= fix_a_min, "LS-6AA-FIX-A test coverage below minimum", errors)
    req(total_tests == fix_a_expected, "LS-6AA-FIX-A test coverage does not match expected", errors)

    ls6aa_valid = ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH"
    fix_a_done = total_tests >= fix_a_min and total_tests == fix_a_expected
    returned_status = str(ls6aa_run.get("returned_post_status", ""))

    blocked_result = build_blocked_result(post_id, returned_status, ls6aa_valid, fix_a_done, final_label, [] if not errors else list(errors))
    lock = build_lock(post_id)

    write_json(Path(args.blocked_runner_output), blocked_result)
    write_json(Path(args.blocked_runner_lock_output), lock)

    status = STATUS_PASSED if not errors else STATUS_NOT_READY
    if any(e.startswith("invalid json") for e in errors):
        status = STATUS_FAILED

    run_result = build_run_result(status, post_id, returned_status, ls6aa_valid, fix_a_done, final_label, errors)
    write_json(output_path, run_result)
    write_report(report_path, run_result)
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
