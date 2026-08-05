#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_RECORD_FLAG"
STATUS_NOT_READY_MISSING_FINAL_EXECUTION_COMMAND_FLAG = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_FINAL_EXECUTION_COMMAND_FLAG"
STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6af_manual_publish_actual_publish_runner_final_gate_policy.json")
    parser.add_argument("--ls6ae-run-result", default="exchange/logs/start_ls6ae_manual_publish_actual_publish_final_preflight_result.json")
    parser.add_argument("--ls6ae-validation-result", default="exchange/logs/start_ls6ae_manual_publish_actual_publish_final_preflight_validation_result.json")
    parser.add_argument("--ls6ae-wordpress-current-draft-status-result", default="exchange/runtime/start_ls6ae_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--ls6ae-final-preflight-result", default="exchange/runtime/start_ls6ae_manual_publish_actual_publish_final_preflight_result.json")
    parser.add_argument("--ls6ae-final-preflight-lock", default="exchange/locks/start_ls6ae_manual_publish_actual_publish_final_preflight.lock.json")
    parser.add_argument("--ls6ad-validation-result", default="exchange/logs/start_ls6ad_manual_publish_actual_publish_execution_boundary_validation_result.json")
    parser.add_argument("--ls6ad-boundary-result", default="exchange/runtime/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
    parser.add_argument("--ls6ad-boundary-lock", default="exchange/locks/start_ls6ad_manual_publish_actual_publish_execution_boundary.lock.json")
    parser.add_argument("--ls6ac-ready-result", default="exchange/logs/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation_ready_result.json")
    parser.add_argument("--ls6ac-confirmation-result", default="exchange/human_review/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation.json")
    parser.add_argument("--ls6ab-validation-result", default="exchange/logs/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_validation_result.json")
    parser.add_argument("--ls6ab-blocked-runner-result", default="exchange/runtime/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_blocked_result.json")
    parser.add_argument("--ls6ab-blocked-runner-lock", default="exchange/locks/start_ls6ab_manual_publish_separated_actual_publish_execution_runner.lock.json")
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
    parser.add_argument("--actual-publish-runner-final-gate-output", default="exchange/runtime/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
    parser.add_argument("--actual-publish-runner-final-gate-lock-output", default="exchange/locks/start_ls6af_manual_publish_actual_publish_runner_final_gate.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6af_manual_publish_actual_publish_runner_final_gate_report.md")
    parser.add_argument("--record-actual-publish-runner-final-gate", action="store_true")
    parser.add_argument("--require-actual-publish-final-execution-command", action="store_true")
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
        "# LS-6AF Manual Publish Actual Publish Runner Final Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- actual_publish_runner_final_gate_ready: {result['actual_publish_runner_final_gate_ready']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        f"- requires_actual_publish_final_execution_command: {result['requires_actual_publish_final_execution_command']}",
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


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def false_in(doc: dict[str, Any], key: str) -> bool:
    return doc.get(key, False) is False


def build_runtime_result(errors: list[str], returned_post_status: str) -> dict[str, Any]:
    return {
        "phase": "LS-6AF",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_READY_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY_NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "ls6ae_final_preflight_validated": not errors,
        "ls6ae_draft_verified": not errors,
        "returned_post_status": returned_post_status,
        "actual_publish_runner_final_gate_ready": not errors,
        "actual_publish_runner_final_gate_consumed": False,
        "actual_publish_final_preflight_ready": True,
        "actual_publish_final_preflight_consumed": False,
        "actual_publish_execution_boundary_ready": True,
        "actual_publish_execution_boundary_consumed": False,
        "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
        "actual_publish_execute_now_final_confirmation_consumed": False,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": True,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
        "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
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
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_actual_publish_final_execution_command": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "errors": list(errors),
    }


def build_lock() -> dict[str, Any]:
    return {
        "phase": "LS-6AF",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": 183,
        "target_post_status": "draft",
        "actual_publish_runner_final_gate_ready": True,
        "actual_publish_runner_final_gate_consumed": False,
        "actual_publish_final_preflight_ready": True,
        "actual_publish_final_preflight_consumed": False,
        "actual_publish_execution_boundary_ready": True,
        "actual_publish_execution_boundary_consumed": False,
        "actual_publish_execute_now_final_confirmation_consumed": False,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": True,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "actual_publish_execution_runner_ready": True,
        "actual_publish_execution_runner_executed": False,
        "actual_publish_execution_runner_blocked": True,
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
        "requires_next_phase": "LS-6AG",
        "requires_actual_publish_final_execution_command": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, errors: list[str], returned_post_status: str) -> dict[str, Any]:
    runtime_result = build_runtime_result(errors, returned_post_status)
    return {
        "phase": "LS-6AF",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_RUNNER_FINAL_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": runtime_result["post_id"],
        "post_link": runtime_result["post_link"],
        "payload_title": runtime_result["payload_title"],
        "payload_asin": runtime_result["payload_asin"],
        "ls6ae_final_preflight_validated": runtime_result["ls6ae_final_preflight_validated"],
        "ls6ae_draft_verified": runtime_result["ls6ae_draft_verified"],
        "returned_post_status": runtime_result["returned_post_status"],
        "actual_publish_runner_final_gate_ready": runtime_result["actual_publish_runner_final_gate_ready"],
        "actual_publish_runner_final_gate_consumed": runtime_result["actual_publish_runner_final_gate_consumed"],
        "actual_publish_final_preflight_ready": runtime_result["actual_publish_final_preflight_ready"],
        "actual_publish_final_preflight_consumed": runtime_result["actual_publish_final_preflight_consumed"],
        "actual_publish_execution_boundary_ready": runtime_result["actual_publish_execution_boundary_ready"],
        "actual_publish_execution_boundary_consumed": runtime_result["actual_publish_execution_boundary_consumed"],
        "actual_publish_execute_now_final_confirmation_label": runtime_result["actual_publish_execute_now_final_confirmation_label"],
        "actual_publish_execute_now_final_confirmation_consumed": runtime_result["actual_publish_execute_now_final_confirmation_consumed"],
        "explicit_execute_now_for_actual_publish_required": runtime_result["explicit_execute_now_for_actual_publish_required"],
        "explicit_execute_now_for_actual_publish_received": runtime_result["explicit_execute_now_for_actual_publish_received"],
        "explicit_execute_now_for_actual_publish_consumed": runtime_result["explicit_execute_now_for_actual_publish_consumed"],
        "actual_publish_execution_runner_ready": runtime_result["actual_publish_execution_runner_ready"],
        "actual_publish_execution_runner_executed": runtime_result["actual_publish_execution_runner_executed"],
        "actual_publish_execution_runner_blocked": runtime_result["actual_publish_execution_runner_blocked"],
        "final_explicit_publish_execution_command_label": runtime_result["final_explicit_publish_execution_command_label"],
        "final_explicit_publish_execution_command_consumed": runtime_result["final_explicit_publish_execution_command_consumed"],
        "actual_publish_execution_final_preflight_ready": runtime_result["actual_publish_execution_final_preflight_ready"],
        "actual_publish_execution_final_preflight_consumed": runtime_result["actual_publish_execution_final_preflight_consumed"],
        "actual_publish_runner_boundary_consumed": runtime_result["actual_publish_runner_boundary_consumed"],
        "actual_publish_execution_gate_consumed": runtime_result["actual_publish_execution_gate_consumed"],
        "final_execution_command_consumed": runtime_result["final_execution_command_consumed"],
        "approval_label_consumed": runtime_result["approval_label_consumed"],
        "execute_now_confirmation_consumed": runtime_result["execute_now_confirmation_consumed"],
        "actual_publish_execution_allowed_by_this_phase": runtime_result["actual_publish_execution_allowed_by_this_phase"],
        "actual_runner_execution_allowed_by_this_phase": runtime_result["actual_runner_execution_allowed_by_this_phase"],
        "manual_publish_allowed_by_this_phase": runtime_result["manual_publish_allowed_by_this_phase"],
        "manual_publish_execution_allowed_by_this_phase": runtime_result["manual_publish_execution_allowed_by_this_phase"],
        "manual_publish_executed": runtime_result["manual_publish_executed"],
        "wordpress_api_call_executed": runtime_result["wordpress_api_call_executed"],
        "wordpress_get_executed": runtime_result["wordpress_get_executed"],
        "wordpress_post_executed": runtime_result["wordpress_post_executed"],
        "wordpress_put_executed": runtime_result["wordpress_put_executed"],
        "wordpress_patch_executed": runtime_result["wordpress_patch_executed"],
        "wordpress_delete_executed": runtime_result["wordpress_delete_executed"],
        "wordpress_write_executed_by_this_phase": runtime_result["wordpress_write_executed_by_this_phase"],
        "wordpress_draft_creation_executed_by_this_phase": runtime_result["wordpress_draft_creation_executed_by_this_phase"],
        "wordpress_existing_post_update_executed": runtime_result["wordpress_existing_post_update_executed"],
        "wordpress_publish_executed": runtime_result["wordpress_publish_executed"],
        "publish_executed": runtime_result["publish_executed"],
        "future_schedule_executed": runtime_result["future_schedule_executed"],
        "delete_executed": runtime_result["delete_executed"],
        "post119_update_executed": runtime_result["post119_update_executed"],
        "credential_env_read_executed": runtime_result["credential_env_read_executed"],
        "credential_value_output": runtime_result["credential_value_output"],
        "credential_value_persisted": runtime_result["credential_value_persisted"],
        "credential_secret_output": runtime_result["credential_secret_output"],
        "secret_length_output": runtime_result["secret_length_output"],
        "secret_hash_output": runtime_result["secret_hash_output"],
        "authorization_header_output": runtime_result["authorization_header_output"],
        "locked": status == STATUS_PASSED,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_final_execution_command": runtime_result["requires_actual_publish_final_execution_command"],
        "requires_separate_publish_execution_phase": runtime_result["requires_separate_publish_execution_phase"],
        "publish_execution_still_blocked": runtime_result["publish_execution_still_blocked"],
        "next_phase": {
            "phase": "LS-6AG",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_final_execution_command": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_ls6ac_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("actual_publish_execute_now_final_confirmation_consumed", safe_get(doc, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed"))


def get_ls6ac_explicit_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("explicit_execute_now_for_actual_publish_consumed", safe_get(doc, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_consumed"))


def get_ls6t_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("execute_now_confirmation_consumed", safe_get(doc, "confirmation", "execute_now_confirmation_consumed"))


def get_ls6r_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("approval_label_consumed", safe_get(doc, "approval", "approval_label_consumed"))


def get_ls6z_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("final_explicit_publish_execution_command_consumed", safe_get(doc, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed"))


def get_ls6x_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("actual_publish_execution_gate_consumed", safe_get(doc, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed"))


def get_ls6v_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("final_execution_command_consumed", safe_get(doc, "final_execution_command", "final_execution_command_consumed"))


def write_not_ready(output: Path, report: Path, status: str, message: str) -> int:
    result = build_run_result(status, [message], "")
    write_json(output, result)
    write_report(report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not args.record_actual_publish_runner_final_gate:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_RECORD_FLAG, "missing --record-actual-publish-runner-final-gate")
    if not args.require_actual_publish_final_execution_command:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_FINAL_EXECUTION_COMMAND_FLAG, "missing --require-actual-publish-final-execution-command")
    if not args.require_separate_publish_execution_phase:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG, "missing --require-separate-publish-execution-phase")

    errors: list[str] = []
    policy = try_load_json(Path(args.policy), errors)
    ls6ae_run = try_load_json(Path(args.ls6ae_run_result), errors)
    ls6ae_validation = try_load_json(Path(args.ls6ae_validation_result), errors)
    ls6ae_wp = try_load_json(Path(args.ls6ae_wordpress_current_draft_status_result), errors)
    ls6ae_final = try_load_json(Path(args.ls6ae_final_preflight_result), errors)
    ls6ae_lock = try_load_json(Path(args.ls6ae_final_preflight_lock), errors)
    ls6ad_validation = try_load_json(Path(args.ls6ad_validation_result), errors)
    ls6ad_boundary = try_load_json(Path(args.ls6ad_boundary_result), errors)
    ls6ad_lock = try_load_json(Path(args.ls6ad_boundary_lock), errors)
    ls6ac_ready = try_load_json(Path(args.ls6ac_ready_result), errors)
    ls6ac_confirmation = try_load_json(Path(args.ls6ac_confirmation_result), errors)
    ls6ab_validation = try_load_json(Path(args.ls6ab_validation_result), errors)
    ls6ab_blocked = try_load_json(Path(args.ls6ab_blocked_runner_result), errors)
    ls6ab_lock = try_load_json(Path(args.ls6ab_blocked_runner_lock), errors)
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

    req(policy.get("phase") == "LS-6AF", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_RUNNER_FINAL_GATE_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6ae_run.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6AE run status mismatch", errors)
    req(ls6ae_validation.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AE validation status mismatch", errors)
    req(ls6ae_run.get("post_id") == 183, "LS-6AE post_id mismatch", errors)
    req(ls6ae_run.get("returned_post_status") == "draft", "LS-6AE returned_post_status mismatch", errors)
    req(ls6ae_run.get("draft_verified") is True, "LS-6AE draft_verified must be true", errors)
    req(ls6ae_run.get("wordpress_get_executed") is True, "LS-6AE wordpress_get_executed must be true", errors)
    req(ls6ae_run.get("wordpress_get_post_id") == 183, "LS-6AE wordpress_get_post_id mismatch", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_ready") is True, "LS-6AE final preflight ready must be true", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_consumed") is False, "LS-6AE final preflight consumed must be false", errors)
    req(ls6ae_lock.get("actual_publish_final_preflight_consumed") is False, "LS-6AE lock final preflight consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_execution_boundary_ready") is True, "LS-6AE boundary ready must be true", errors)
    req(ls6ae_run.get("actual_publish_execution_boundary_consumed") is False, "LS-6AE boundary consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AE execute-now final confirmation consumed must be false", errors)
    req(ls6ae_run.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AE explicit execute-now required must be true", errors)
    req(ls6ae_run.get("explicit_execute_now_for_actual_publish_received") is True, "LS-6AE explicit execute-now received must be true", errors)
    req(ls6ae_run.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AE explicit execute-now consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_execution_runner_ready") is True, "LS-6AE runner ready must be true", errors)
    req(ls6ae_run.get("actual_publish_execution_runner_executed") is False, "LS-6AE runner executed must be false", errors)
    req(ls6ae_run.get("actual_publish_execution_runner_blocked") is True, "LS-6AE runner blocked must be true", errors)
    req(ls6ae_run.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AE execution final preflight consumed must be false", errors)
    req(ls6ae_run.get("final_explicit_publish_execution_command_consumed") is False, "LS-6AE final explicit command consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_runner_boundary_consumed") is False, "LS-6AE runner boundary consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_execution_gate_consumed") is False, "LS-6AE execution gate consumed must be false", errors)
    req(ls6ae_run.get("final_execution_command_consumed") is False, "LS-6AE final execution command consumed must be false", errors)
    req(ls6ae_run.get("approval_label_consumed") is False, "LS-6AE approval consumed must be false", errors)
    req(ls6ae_run.get("execute_now_confirmation_consumed") is False, "LS-6AE execute-now consumed must be false", errors)
    req(ls6ae_run.get("actual_publish_execution_allowed_by_this_phase") is False, "LS-6AE actual publish execution allowed must be false", errors)
    req(ls6ae_run.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6AE actual runner execution allowed must be false", errors)
    req(ls6ae_run.get("manual_publish_allowed_by_this_phase") is False, "LS-6AE manual publish allowed must be false", errors)
    req(ls6ae_run.get("manual_publish_execution_allowed_by_this_phase") is False, "LS-6AE manual publish execution allowed must be false", errors)
    req(ls6ae_run.get("manual_publish_executed") is False, "LS-6AE manual publish executed must be false", errors)
    req(ls6ae_run.get("publish_execution_still_blocked") is True, "LS-6AE publish_execution_still_blocked must be true", errors)
    req(ls6ae_run.get("requires_actual_publish_runner_final_gate") is True, "LS-6AE requires_actual_publish_runner_final_gate must be true", errors)
    req(ls6ae_run.get("requires_separate_publish_execution_phase") is True, "LS-6AE requires_separate_publish_execution_phase must be true", errors)
    req(safe_get(ls6ae_run, "next_phase", "phase") == "LS-6AF", "LS-6AE next_phase mismatch", errors)

    req(ls6ae_wp.get("returned_post_status") == "draft", "LS-6AE wordpress verification returned status mismatch", errors)
    req(ls6ae_wp.get("wordpress_get_executed") is True, "LS-6AE wordpress verification get flag mismatch", errors)

    req(ls6ad_validation.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AD validation status mismatch", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_ready") is True, "LS-6AD boundary ready must be true", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD boundary consumed must be false", errors)
    req(ls6ad_lock.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD lock boundary consumed must be false", errors)

    req(ls6ac_ready.get("status") == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "LS-6AC status mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "LS-6AC label mismatch", errors)
    req(get_ls6ac_consumed(ls6ac_ready) is False, "LS-6AC ready consumed must be false", errors)
    req(get_ls6ac_consumed(ls6ac_confirmation) is False, "LS-6AC confirmation consumed must be false", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AC explicit required must be true", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_received") is True, "LS-6AC explicit received must be true", errors)
    req(get_ls6ac_explicit_consumed(ls6ac_ready) is False, "LS-6AC explicit consumed must be false", errors)

    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_ready") is True, "LS-6AB runner ready must be true", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner executed must be false", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_blocked") is True, "LS-6AB runner blocked must be true", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must be false", errors)

    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_ready") is True, "LS-6AA preflight ready must be true", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock preflight consumed must be false", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z status mismatch", errors)
    req(get_ls6z_consumed(ls6z_ready) is False, "LS-6Z ready consumed must be false", errors)
    req(get_ls6z_consumed(ls6z_command) is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X status mismatch", errors)
    req(get_ls6x_consumed(ls6x_ready) is False, "LS-6X ready consumed must be false", errors)
    req(get_ls6x_consumed(ls6x_gate) is False, "LS-6X gate consumed must be false", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V status mismatch", errors)
    req(get_ls6v_consumed(ls6v_ready) is False, "LS-6V ready consumed must be false", errors)
    req(get_ls6v_consumed(ls6v_command) is False, "LS-6V command consumed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T status mismatch", errors)
    req(get_ls6t_consumed(ls6t_ready) is False, "LS-6T ready consumed must be false", errors)
    req(get_ls6t_consumed(ls6t_confirmation) is False, "LS-6T confirmation consumed must be false", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R status mismatch", errors)
    req(get_ls6r_consumed(ls6r_ready) is False, "LS-6R ready consumed must be false", errors)
    req(get_ls6r_consumed(ls6r_approval) is False, "LS-6R approval consumed must be false", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6OC1 rerun_allowed must be false", errors)

    returned_post_status = str(ls6ae_run.get("returned_post_status", ""))

    if errors:
        run_result = build_run_result(STATUS_NOT_READY, errors, returned_post_status)
        write_json(output_path, run_result)
        write_report(report_path, run_result)
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    runtime_result = build_runtime_result([], returned_post_status)
    lock = build_lock()
    run_result = build_run_result(STATUS_PASSED, [], returned_post_status)

    write_json(Path(args.actual_publish_runner_final_gate_output), runtime_result)
    write_json(Path(args.actual_publish_runner_final_gate_lock_output), lock)
    write_json(output_path, run_result)
    write_report(report_path, run_result)
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
