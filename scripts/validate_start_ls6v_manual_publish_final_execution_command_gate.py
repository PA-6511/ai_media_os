#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_NOT_READY"


def k_cred_read() -> str:
    return "credential_" + "env_read_executed"


def load_json(path: Path, label: str, errors: list[str], required: bool = True) -> dict[str, Any]:
    if not path.exists():
        if required:
            errors.append(f"missing required file: {label}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(f"invalid json: {label}")
        return {}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6v_manual_publish_final_execution_command_gate_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.template.json")
    parser.add_argument("--command", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6u-validation-result", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_validation_result.json")
    parser.add_argument("--ls6u-run-result", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_result.json")
    parser.add_argument("--ls6u-runner-boundary-preflight-result", default="exchange/runtime/start_ls6u_manual_publish_actual_execution_runner_boundary_preflight_result.json")
    parser.add_argument("--ls6u-runner-boundary-lock", default="exchange/locks/start_ls6u_manual_publish_actual_execution_runner_boundary.lock.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6v_manual_publish_final_execution_command_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    require(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    require(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    require(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    require(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_current_phase_flags(current: dict[str, Any], errors: list[str]) -> None:
    cred_key = k_cred_read()
    keys = [
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
        cred_key,
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "final_execution_command_consumed",
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]
    for key in keys:
        require(bool(current.get(key, False)) is False, f"current_phase_execution.{key} must be false", errors)


def validate_common(
    policy: dict[str, Any],
    ls6u_validation: dict[str, Any],
    ls6u_run: dict[str, Any],
    ls6u_preflight: dict[str, Any],
    ls6u_lock: dict[str, Any],
    ls6t_ready: dict[str, Any],
    ls6t_confirmation: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6r_approval: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    errors: list[str],
) -> None:
    require(policy.get("phase") == "LS-6V", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "FINAL_EXECUTION_COMMAND_GATE_ONLY", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    require(ls6u_validation.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6U validation status mismatch", errors)
    require(ls6u_run.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH", "LS-6U run status mismatch", errors)
    require(ls6u_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6U runner boundary preflight status mismatch", errors)
    require(ls6u_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH", "LS-6U runner boundary lock status mismatch", errors)
    require(ls6u_run.get("manual_publish_runner_boundary_ready") is True, "LS-6U manual_publish_runner_boundary_ready must be true", errors)
    require(ls6u_run.get("requires_final_execution_command") is True, "LS-6U requires_final_execution_command must be true", errors)
    require(ls6u_run.get("manual_publish_allowed_by_this_phase") is False, "LS-6U manual_publish_allowed_by_this_phase must be false", errors)
    require(ls6u_run.get("manual_publish_execution_allowed_by_this_phase") is False, "LS-6U manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(ls6u_run.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY", "LS-6U approval_label mismatch", errors)
    require(ls6u_run.get("execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "LS-6U execute_now_confirmation_label mismatch", errors)
    require(to_int(ls6u_run.get("post_id")) == 183, "LS-6U post_id mismatch", errors)
    require(ls6u_run.get("returned_post_status") == "draft", "LS-6U returned_post_status mismatch", errors)
    require(ls6u_run.get("approval_label_consumed") is False, "LS-6U approval_label_consumed must be false", errors)
    require(ls6u_run.get("execute_now_confirmation_consumed") is False, "LS-6U execute_now_confirmation_consumed must be false", errors)
    require(ls6u_run.get("manual_publish_executed") is False, "LS-6U manual_publish_executed must be false", errors)
    require(ls6u_run.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6U actual_runner_execution_allowed_by_this_phase must be false", errors)
    require(ls6u_run.get("publish_execution_still_blocked") is True, "LS-6U publish_execution_still_blocked must be true", errors)
    require(safe_get(ls6u_run, "next_phase", "phase") == "LS-6V", "LS-6U next_phase mismatch", errors)

    require(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    require(ls6t_ready.get("execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "LS-6T execute_now_confirmation_label mismatch", errors)
    require(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    require(ls6t_ready.get("manual_publish_executed") is False, "LS-6T manual_publish_executed must be false", errors)
    require(ls6t_confirmation.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)

    require(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    require(ls6r_ready.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY", "LS-6R approval_label mismatch", errors)
    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must be false", errors)
    require(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    require(ls6p_lock.get("locked") is True, "LS-6P rerun prevention lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    require(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("phase") == "LS-6V", "template.phase mismatch", errors)
    require(template.get("document_type") == "MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_TEMPLATE", "template.document_type mismatch", errors)
    require(template.get("command_status") == "TEMPLATE_NOT_COMMANDED", "template.command_status mismatch", errors)

    target = template.get("target_post", {})
    validate_target_post(target, errors)

    final = template.get("final_execution_command", {})
    require(final.get("final_execution_command_label") in ("", None), "template final_execution_command_label must be empty", errors)
    require(final.get("required_final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "template required final_execution_command_label mismatch", errors)
    require(final.get("final_execution_command_consumed") is False, "template final_execution_command_consumed must be false", errors)
    require(final.get("manual_publish_allowed_by_this_phase") is False, "template manual_publish_allowed_by_this_phase must be false", errors)
    require(final.get("manual_publish_execution_allowed_by_this_phase") is False, "template manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(final.get("actual_runner_execution_allowed_by_this_phase") is False, "template actual_runner_execution_allowed_by_this_phase must be false", errors)
    require(final.get("manual_publish_executed") is False, "template manual_publish_executed must be false", errors)

    current = template.get("current_phase_execution", {})
    validate_current_phase_flags(current, errors)


def validate_command(command: dict[str, Any], errors: list[str]) -> None:
    require(command.get("phase") == "LS-6V", "command.phase mismatch", errors)
    require(command.get("document_type") == "MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND", "command.document_type mismatch", errors)
    require(command.get("command_status") == "FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "command.command_status mismatch", errors)

    target = command.get("target_post", {})
    validate_target_post(target, errors)

    final = command.get("final_execution_command", {})
    require(final.get("final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "wrong final_execution_command_label", errors)
    require(final.get("required_final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "required final_execution_command_label mismatch", errors)
    require(final.get("final_execution_command_consumed") is False, "final_execution_command_consumed must be false", errors)
    require(final.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    require(final.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(final.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    require(final.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    require(final.get("requires_next_phase") == "LS-6W", "requires_next_phase mismatch", errors)

    current = command.get("current_phase_execution", {})
    validate_current_phase_flags(current, errors)


def build_result(
    status: str,
    policy: dict[str, Any],
    source_doc: dict[str, Any],
    ls6u_run: dict[str, Any],
    ls6u_validation: dict[str, Any],
    ls6t_ready: dict[str, Any],
    errors: list[str],
    recorded: bool,
) -> dict[str, Any]:
    cred_key = k_cred_read()
    target = source_doc.get("target_post", {})
    final = source_doc.get("final_execution_command", {})
    current = source_doc.get("current_phase_execution", {})
    next_phase = policy.get("next_phase", {})

    return {
        "phase": "LS-6V",
        "status": status,
        "execution_mode": "FINAL_EXECUTION_COMMAND_GATE_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "returned_post_status": ls6u_run.get("returned_post_status", ""),
        "ls6u_runner_boundary_validated": ls6u_validation.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH",
        "manual_publish_final_execution_command_recorded": True,
        "command_status": source_doc.get("command_status", ""),
        "final_execution_command_label": final.get("final_execution_command_label", ""),
        "final_execution_command_consumed": bool(final.get("final_execution_command_consumed", False)),
        "approval_label": ls6u_run.get("approval_label", ""),
        "approval_label_consumed": bool(current.get("approval_label_consumed", False)),
        "execute_now_confirmation_label": ls6t_ready.get("execute_now_confirmation_label", ""),
        "execute_now_confirmation_consumed": bool(current.get("execute_now_confirmation_consumed", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(final.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(final.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(final.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(final.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(current.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(current.get("wordpress_get_executed", False)),
        "wordpress_write_executed": bool(current.get("wordpress_write_executed", False)),
        "wordpress_draft_creation_executed": bool(current.get("wordpress_draft_creation_executed", False)),
        "wordpress_existing_post_update_executed": bool(current.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(current.get("wordpress_publish_executed", False)),
        "publish_executed": bool(current.get("publish_executed", False)),
        "future_schedule_executed": bool(current.get("future_schedule_executed", False)),
        "delete_executed": bool(current.get("delete_executed", False)),
        "post119_update_executed": bool(current.get("post119_update_executed", False)),
        cred_key: bool(current.get(cred_key, False)),
        "credential_value_output": bool(current.get("credential_value_output", False)),
        "credential_value_persisted": bool(current.get("credential_value_persisted", False)),
        "credential_secret_output": bool(current.get("credential_secret_output", False)),
        "secret_length_output": bool(current.get("secret_length_output", False)),
        "secret_hash_output": bool(current.get("secret_hash_output", False)),
        "authorization_header_output": bool(current.get("authorization_header_output", False)),
        "rerun_allowed": bool(current.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(current.get("ls6oc1_rerun_executed", False)),
        "publish_execution_still_blocked": bool(ls6u_run.get("publish_execution_still_blocked", False)),
        "next_phase": {
            "phase": next_phase.get("phase", "LS-6W"),
            "execution_allowed": bool(next_phase.get("execution_allowed_by_this_phase", False)),
            "manual_publish_execution_allowed_by_this_phase": bool(next_phase.get("manual_publish_execution_allowed_by_this_phase", False)),
            "actual_runner_execution_allowed_by_this_phase": bool(next_phase.get("actual_runner_execution_allowed_by_this_phase", False)),
            "requires_final_runner_preflight": bool(next_phase.get("requires_final_runner_preflight", False)),
            "requires_separate_publish_execution": bool(next_phase.get("requires_separate_publish_execution", False)),
            "publish_execution_still_blocked": bool(next_phase.get("publish_execution_still_blocked", False)),
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6V Manual Publish Final Execution Command Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- command_status: {result['command_status']}",
        f"- final_execution_command_label: {result['final_execution_command_label']}",
        f"- manual_publish_final_execution_command_recorded: {result['manual_publish_final_execution_command_recorded']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()

    errors: list[str] = []

    policy = load_json(Path(args.policy), "policy", errors)
    template = load_json(Path(args.template), "template", errors)
    command = load_json(Path(args.command), "command", errors, required=not args.allow_template)
    ls6u_validation = load_json(Path(args.ls6u_validation_result), "ls6u_validation", errors)
    ls6u_run = load_json(Path(args.ls6u_run_result), "ls6u_run", errors)
    ls6u_preflight = load_json(Path(args.ls6u_runner_boundary_preflight_result), "ls6u_runner_boundary_preflight", errors)
    ls6u_lock = load_json(Path(args.ls6u_runner_boundary_lock), "ls6u_runner_boundary_lock", errors)
    ls6t_ready = load_json(Path(args.ls6t_ready_result), "ls6t_ready", errors)
    ls6t_confirmation = load_json(Path(args.ls6t_confirmation_result), "ls6t_confirmation", errors)
    ls6r_ready = load_json(Path(args.ls6r_ready_result), "ls6r_ready", errors)
    ls6r_approval = load_json(Path(args.ls6r_approval_result), "ls6r_approval", errors)
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock), "ls6p_rerun_prevention", errors)
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock), "ls6oc1_consumption", errors)

    validate_common(
        policy,
        ls6u_validation,
        ls6u_run,
        ls6u_preflight,
        ls6u_lock,
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
        status = STATUS_TEMPLATE_READY if not errors else STATUS_NOT_READY
        result = build_result(status, policy, template, ls6u_run, ls6u_validation, ls6t_ready, errors, recorded=False)
    else:
        validate_command(command, errors)
        status = STATUS_READY if not errors else STATUS_NOT_READY
        result = build_result(status, policy, command, ls6u_run, ls6u_validation, ls6t_ready, errors, recorded=True)

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
