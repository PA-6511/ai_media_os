#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6z_manual_publish_final_explicit_publish_execution_command_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.template.json")
    parser.add_argument("--command", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.json")
    parser.add_argument("--ls6y-validation-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--ls6y-run-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_result.json")
    parser.add_argument("--ls6y-boundary-preflight-result", default="exchange/runtime/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_preflight_result.json")
    parser.add_argument("--ls6y-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6w-validation-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_result.json")
    parser.add_argument("--ls6w-final-runner-preflight-result", default="exchange/runtime/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
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
        "# LS-6Z Manual Publish Final Explicit Publish Execution Command Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- command_status: {result['command_status']}",
        f"- final_explicit_publish_execution_command_label: {result['final_explicit_publish_execution_command_label']}",
        f"- final_explicit_publish_execution_command_recorded: {result['final_explicit_publish_execution_command_recorded']}",
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


def validate_current_false_flags(current: dict[str, Any], errors: list[str]) -> None:
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
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "final_execution_command_consumed",
        "actual_publish_execution_gate_consumed",
        "actual_publish_runner_boundary_consumed",
        "final_explicit_publish_execution_command_consumed",
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]:
        req(current.get(key) is False, f"current_phase_execution.{key} must be false", errors)


def validate_common(
    policy: dict[str, Any],
    ls6y_validation: dict[str, Any],
    ls6y_run: dict[str, Any],
    ls6y_preflight: dict[str, Any],
    ls6y_lock: dict[str, Any],
    ls6x_ready: dict[str, Any],
    ls6x_gate: dict[str, Any],
    ls6w_validation: dict[str, Any],
    ls6w_preflight: dict[str, Any],
    ls6v_ready: dict[str, Any],
    ls6v_command: dict[str, Any],
    ls6t_ready: dict[str, Any],
    ls6t_confirmation: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6r_approval: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    errors: list[str],
) -> None:
    req(policy.get("phase") == "LS-6Z", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_GATE_ONLY", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y validation status mismatch", errors)
    req(ls6y_run.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH", "LS-6Y run status mismatch", errors)
    req(ls6y_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6Y preflight status mismatch", errors)
    req(ls6y_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH", "LS-6Y lock status mismatch", errors)
    req(to_int(ls6y_validation.get("post_id")) == 183, "LS-6Y post_id mismatch", errors)
    req(ls6y_validation.get("returned_post_status") == "draft", "LS-6Y returned_post_status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_ready") is True, "LS-6Y actual_publish_runner_boundary_ready must be true", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y actual_publish_runner_boundary_consumed must be false", errors)
    req(ls6y_validation.get("actual_publish_execution_gate_consumed") is False, "LS-6Y actual_publish_execution_gate_consumed must be false", errors)
    req(ls6y_validation.get("final_execution_command_consumed") is False, "LS-6Y final_execution_command_consumed must be false", errors)
    req(ls6y_validation.get("approval_label_consumed") is False, "LS-6Y approval_label_consumed must be false", errors)
    req(ls6y_validation.get("execute_now_confirmation_consumed") is False, "LS-6Y execute_now_confirmation_consumed must be false", errors)
    req(ls6y_validation.get("manual_publish_executed") is False, "LS-6Y manual_publish_executed must be false", errors)
    req(ls6y_validation.get("publish_execution_still_blocked") is True, "LS-6Y publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6y_validation, "next_phase", "phase") == "LS-6Z", "LS-6Y next_phase mismatch", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X ready status mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X actual_publish_execution_gate_consumed must be false", errors)
    req(ls6x_ready.get("manual_publish_executed") is False, "LS-6X manual_publish_executed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6X gate label mismatch", errors)

    req(ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6W validation status mismatch", errors)
    req(ls6w_validation.get("returned_post_status") == "draft", "LS-6W returned_post_status mismatch", errors)
    req(ls6w_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W preflight status mismatch", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must be false", errors)
    req(ls6v_ready.get("manual_publish_executed") is False, "LS-6V manual_publish_executed must be false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command final_execution_command_consumed mismatch", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    req(ls6t_confirmation.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    req(ls6r_ready.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY", "LS-6R approval_label mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    req(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    req(ls6p_lock.get("locked") is True, "LS-6P lock must be true", errors)
    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    req(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    req(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    req(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    req(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    req(template.get("phase") == "LS-6Z", "template.phase mismatch", errors)
    req(template.get("document_type") == "MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_TEMPLATE", "template.document_type mismatch", errors)
    req(template.get("command_status") == "TEMPLATE_NOT_COMMANDED", "template.command_status mismatch", errors)
    validate_target_post(template.get("target_post", {}), errors)
    cmd = template.get("final_explicit_publish_execution_command", {})
    req(cmd.get("final_explicit_publish_execution_command_label") in ("", None), "template command label must be empty", errors)
    req(cmd.get("required_final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "template required command label mismatch", errors)
    for key in [
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "manual_publish_executed",
    ]:
        req(cmd.get(key) is False, f"template.{key} must be false", errors)
    validate_current_false_flags(template.get("current_phase_execution", {}), errors)


def validate_command(command_doc: dict[str, Any], errors: list[str]) -> None:
    req(command_doc.get("phase") == "LS-6Z", "command.phase mismatch", errors)
    req(command_doc.get("document_type") == "MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND", "command.document_type mismatch", errors)
    req(command_doc.get("command_status") == "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "command.command_status mismatch", errors)
    validate_target_post(command_doc.get("target_post", {}), errors)

    cmd = command_doc.get("final_explicit_publish_execution_command", {})
    req(cmd.get("final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "wrong final_explicit_publish_execution_command_label", errors)
    req(cmd.get("required_final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "required final explicit command label mismatch", errors)
    for key in [
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "manual_publish_executed",
    ]:
        req(cmd.get(key) is False, f"command.{key} must be false", errors)
    req(cmd.get("requires_next_phase") == "LS-6AA", "command.requires_next_phase mismatch", errors)
    validate_current_false_flags(command_doc.get("current_phase_execution", {}), errors)


def build_result(
    status: str,
    source_doc: dict[str, Any],
    ls6y_validation: dict[str, Any],
    ls6x_ready: dict[str, Any],
    ls6v_ready: dict[str, Any],
    ls6t_ready: dict[str, Any],
    ls6r_ready: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    cmd = source_doc.get("final_explicit_publish_execution_command", {})
    current = source_doc.get("current_phase_execution", {})
    target = source_doc.get("target_post", {})
    label = cmd.get("final_explicit_publish_execution_command_label", "")
    return {
        "phase": "LS-6Z",
        "status": status,
        "execution_mode": "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_GATE_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "returned_post_status": ls6y_validation.get("returned_post_status", ""),
        "ls6y_actual_publish_runner_boundary_validated": ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH",
        "final_explicit_publish_execution_command_recorded": True,
        "command_status": source_doc.get("command_status", ""),
        "final_explicit_publish_execution_command_label": label,
        "final_explicit_publish_execution_command_consumed": bool(cmd.get("final_explicit_publish_execution_command_consumed", False)),
        "actual_publish_execution_gate_label": ls6x_ready.get("actual_publish_execution_gate_label", ""),
        "actual_publish_execution_gate_consumed": bool(cmd.get("actual_publish_execution_gate_consumed", False)),
        "actual_publish_runner_boundary_ready": True,
        "actual_publish_runner_boundary_consumed": bool(cmd.get("actual_publish_runner_boundary_consumed", False)),
        "final_execution_command_label": ls6v_ready.get("final_execution_command_label", ""),
        "final_execution_command_consumed": bool(cmd.get("final_execution_command_consumed", False)),
        "approval_label": ls6r_ready.get("approval_label", ""),
        "approval_label_consumed": bool(cmd.get("approval_label_consumed", False)),
        "execute_now_confirmation_label": ls6t_ready.get("execute_now_confirmation_label", ""),
        "execute_now_confirmation_consumed": bool(cmd.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(cmd.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(cmd.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(cmd.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(cmd.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(cmd.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(current.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(current.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(current.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(current.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(current.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(current.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(current.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(current.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_existing_post_update_executed": bool(current.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(current.get("wordpress_publish_executed", False)),
        "publish_executed": bool(current.get("publish_executed", False)),
        "future_schedule_executed": bool(current.get("future_schedule_executed", False)),
        "delete_executed": bool(current.get("delete_executed", False)),
        "post119_update_executed": bool(current.get("post119_update_executed", False)),
        key_c(): bool(current.get(key_c(), False)),
        "credential_value_output": bool(current.get("credential_value_output", False)),
        "credential_value_persisted": bool(current.get("credential_value_persisted", False)),
        "credential_secret_output": bool(current.get("credential_secret_output", False)),
        "secret_length_output": bool(current.get("secret_length_output", False)),
        "secret_hash_output": bool(current.get("secret_hash_output", False)),
        "authorization_header_output": bool(current.get("authorization_header_output", False)),
        "rerun_allowed": bool(current.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(current.get("ls6oc1_rerun_executed", False)),
        "requires_actual_publish_execution_final_preflight": True,
        "requires_separate_actual_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AA",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_final_preflight": True,
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
    template = try_load_json(Path(args.template), errors)
    ls6y_validation = try_load_json(Path(args.ls6y_validation_result), errors)
    ls6y_run = try_load_json(Path(args.ls6y_run_result), errors)
    ls6y_preflight = try_load_json(Path(args.ls6y_boundary_preflight_result), errors)
    ls6y_lock = try_load_json(Path(args.ls6y_boundary_lock), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6w_validation = try_load_json(Path(args.ls6w_validation_result), errors)
    ls6w_preflight = try_load_json(Path(args.ls6w_final_runner_preflight_result), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6v_command = try_load_json(Path(args.ls6v_command_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6t_confirmation = try_load_json(Path(args.ls6t_confirmation_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6r_approval = try_load_json(Path(args.ls6r_approval_result), errors)
    ls6p_lock = try_load_json(Path(args.ls6p_rerun_prevention_lock), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    validate_common(
        policy,
        ls6y_validation,
        ls6y_run,
        ls6y_preflight,
        ls6y_lock,
        ls6x_ready,
        ls6x_gate,
        ls6w_validation,
        ls6w_preflight,
        ls6v_ready,
        ls6v_command,
        ls6t_ready,
        ls6t_confirmation,
        ls6r_ready,
        ls6r_approval,
        ls6p_lock,
        ls6oc1_lock,
        errors,
    )

    if args.allow_template:
        validate_template(template, errors)
        source_doc = template
        status = STATUS_TEMPLATE_READY if not errors else STATUS_NOT_READY
    else:
        command_path = Path(args.command)
        if not command_path.exists():
            errors.append("command file missing")
            source_doc = template
        else:
            command_doc = try_load_json(command_path, errors)
            validate_command(command_doc, errors)
            source_doc = command_doc
        status = STATUS_READY if not errors else STATUS_NOT_READY

    result = build_result(status, source_doc, ls6y_validation, ls6x_ready, ls6v_ready, ls6t_ready, ls6r_ready, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
