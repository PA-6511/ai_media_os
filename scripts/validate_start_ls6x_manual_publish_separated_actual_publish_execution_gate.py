#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6x_manual_publish_separated_actual_publish_execution_gate_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.template.json")
    parser.add_argument("--gate", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6w-validation-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_validation_result.json")
    parser.add_argument("--ls6w-run-result", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
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
    parser.add_argument("--output", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    req(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    req(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    req(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    req(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_current_flags(current: dict[str, Any], errors: list[str]) -> None:
    key_c = k_cread()
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
        key_c,
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
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]:
        req(current.get(key) is False, f"current_phase_execution.{key} must be false", errors)


def validate_common(
    policy: dict[str, Any],
    ls6w_validation: dict[str, Any],
    ls6w_run: dict[str, Any],
    ls6w_preflight: dict[str, Any],
    ls6w_lock: dict[str, Any],
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
    req(policy.get("phase") == "LS-6X", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6W validation status mismatch", errors)
    req(ls6w_run.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W run status mismatch", errors)
    req(ls6w_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W final runner preflight status mismatch", errors)
    req(ls6w_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6W final runner preflight lock status mismatch", errors)
    req(to_int(ls6w_validation.get("post_id")) == 183, "LS-6W post_id mismatch", errors)
    req(ls6w_validation.get("draft_verified") is True, "LS-6W draft_verified must be true", errors)
    req(ls6w_validation.get("returned_post_status") == "draft", "LS-6W returned_post_status mismatch", errors)
    req(ls6w_validation.get("final_execution_command_consumed") is False, "LS-6W final_execution_command_consumed must be false", errors)
    req(ls6w_validation.get("approval_label_consumed") is False, "LS-6W approval_label_consumed must be false", errors)
    req(ls6w_validation.get("execute_now_confirmation_consumed") is False, "LS-6W execute_now_confirmation_consumed must be false", errors)
    req(ls6w_validation.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6W actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(ls6w_validation.get("manual_publish_executed") is False, "LS-6W manual_publish_executed must be false", errors)
    req(ls6w_validation.get("requires_separate_publish_execution") is True, "LS-6W requires_separate_publish_execution must be true", errors)
    req(ls6w_validation.get("publish_execution_still_blocked") is True, "LS-6W publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6w_validation, "next_phase", "phase") == "LS-6X", "LS-6W next_phase mismatch", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must be false", errors)
    req(ls6v_ready.get("manual_publish_executed") is False, "LS-6V manual_publish_executed must be false", errors)
    req(ls6v_ready.get("final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6V final_execution_command_label mismatch", errors)
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


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    req(template.get("phase") == "LS-6X", "template.phase mismatch", errors)
    req(template.get("document_type") == "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_TEMPLATE", "template.document_type mismatch", errors)
    req(template.get("gate_status") == "TEMPLATE_NOT_APPROVED", "template.gate_status mismatch", errors)
    validate_target_post(template.get("target_post", {}), errors)
    gate = template.get("actual_publish_execution_gate", {})
    req(gate.get("actual_publish_execution_gate_label") in ("", None), "template gate label must be empty", errors)
    req(gate.get("required_actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "template required gate label mismatch", errors)
    req(gate.get("actual_publish_execution_gate_consumed") is False, "template actual_publish_execution_gate_consumed must be false", errors)
    req(gate.get("actual_publish_execution_allowed_by_this_phase") is False, "template actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("actual_runner_execution_allowed_by_this_phase") is False, "template actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_allowed_by_this_phase") is False, "template manual_publish_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_execution_allowed_by_this_phase") is False, "template manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_executed") is False, "template manual_publish_executed must be false", errors)
    validate_current_flags(template.get("current_phase_execution", {}), errors)


def validate_gate(gate_doc: dict[str, Any], errors: list[str]) -> None:
    req(gate_doc.get("phase") == "LS-6X", "gate.phase mismatch", errors)
    req(gate_doc.get("document_type") == "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE", "gate.document_type mismatch", errors)
    req(gate_doc.get("gate_status") == "ACTUAL_PUBLISH_EXECUTION_GATE_RECORDED_NO_PUBLISH_EXECUTION", "gate.gate_status mismatch", errors)
    validate_target_post(gate_doc.get("target_post", {}), errors)
    gate = gate_doc.get("actual_publish_execution_gate", {})
    req(gate.get("actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "wrong actual_publish_execution_gate_label", errors)
    req(gate.get("required_actual_publish_execution_gate_label") == "APPROVED_FOR_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "required actual_publish_execution_gate_label mismatch", errors)
    req(gate.get("actual_publish_execution_gate_consumed") is False, "actual_publish_execution_gate_consumed must be false", errors)
    req(gate.get("actual_publish_execution_allowed_by_this_phase") is False, "actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    req(gate.get("requires_next_phase") == "LS-6Y", "requires_next_phase mismatch", errors)
    validate_current_flags(gate_doc.get("current_phase_execution", {}), errors)


def build_result(
    status: str,
    policy: dict[str, Any],
    source_doc: dict[str, Any],
    ls6w_validation: dict[str, Any],
    ls6v_ready: dict[str, Any],
    ls6t_ready: dict[str, Any],
    ls6r_ready: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    key_c = k_cread()
    target = source_doc.get("target_post", {})
    gate = source_doc.get("actual_publish_execution_gate", {})
    cur = source_doc.get("current_phase_execution", {})
    nxt = policy.get("next_phase", {})
    return {
        "phase": "LS-6X",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "returned_post_status": ls6w_validation.get("returned_post_status", ""),
        "ls6w_final_runner_preflight_validated": ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH",
        "separated_actual_publish_execution_gate_recorded": True,
        "gate_status": source_doc.get("gate_status", ""),
        "actual_publish_execution_gate_label": gate.get("actual_publish_execution_gate_label", ""),
        "actual_publish_execution_gate_consumed": bool(gate.get("actual_publish_execution_gate_consumed", False)),
        "final_execution_command_label": ls6v_ready.get("final_execution_command_label", ""),
        "final_execution_command_consumed": bool(cur.get("final_execution_command_consumed", False)),
        "approval_label": ls6r_ready.get("approval_label", ""),
        "approval_label_consumed": bool(cur.get("approval_label_consumed", False)),
        "execute_now_confirmation_label": ls6t_ready.get("execute_now_confirmation_label", ""),
        "execute_now_confirmation_consumed": bool(cur.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(gate.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(gate.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(gate.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(gate.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(gate.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(cur.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(cur.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(cur.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(cur.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(cur.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(cur.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(cur.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(cur.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_existing_post_update_executed": bool(cur.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(cur.get("wordpress_publish_executed", False)),
        "publish_executed": bool(cur.get("publish_executed", False)),
        "future_schedule_executed": bool(cur.get("future_schedule_executed", False)),
        "delete_executed": bool(cur.get("delete_executed", False)),
        "post119_update_executed": bool(cur.get("post119_update_executed", False)),
        key_c: bool(cur.get(key_c, False)),
        "credential_value_output": bool(cur.get("credential_value_output", False)),
        "credential_value_persisted": bool(cur.get("credential_value_persisted", False)),
        "credential_secret_output": bool(cur.get("credential_secret_output", False)),
        "secret_length_output": bool(cur.get("secret_length_output", False)),
        "secret_hash_output": bool(cur.get("secret_hash_output", False)),
        "authorization_header_output": bool(cur.get("authorization_header_output", False)),
        "rerun_allowed": bool(cur.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(cur.get("ls6oc1_rerun_executed", False)),
        "requires_next_actual_publish_runner_phase": True,
        "requires_separate_publish_execution": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": nxt.get("phase", "LS-6Y"),
            "execution_allowed": bool(nxt.get("execution_allowed_by_this_phase", False)),
            "manual_publish_execution_allowed_by_this_phase": bool(nxt.get("manual_publish_execution_allowed_by_this_phase", False)),
            "actual_publish_execution_allowed_by_this_phase": bool(nxt.get("actual_publish_execution_allowed_by_this_phase", False)),
            "actual_runner_execution_allowed_by_this_phase": bool(nxt.get("actual_runner_execution_allowed_by_this_phase", False)),
            "requires_actual_publish_runner_boundary": bool(nxt.get("requires_actual_publish_runner_boundary", False)),
            "requires_final_explicit_publish_execution_command": bool(nxt.get("requires_final_explicit_publish_execution_command", False)),
            "publish_execution_still_blocked": bool(nxt.get("publish_execution_still_blocked", False)),
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6X Manual Publish Separated Actual Publish Execution Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- gate_status: {result['gate_status']}",
        f"- actual_publish_execution_gate_label: {result['actual_publish_execution_gate_label']}",
        f"- separated_actual_publish_execution_gate_recorded: {result['separated_actual_publish_execution_gate_recorded']}",
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
    template = load_json(Path(args.template))
    ls6w_validation = load_json(Path(args.ls6w_validation_result))
    ls6w_run = load_json(Path(args.ls6w_run_result))
    ls6w_preflight = load_json(Path(args.ls6w_final_runner_preflight_result))
    ls6w_lock = load_json(Path(args.ls6w_final_runner_preflight_lock))
    ls6v_ready = load_json(Path(args.ls6v_ready_result))
    ls6v_command = load_json(Path(args.ls6v_command_result))
    ls6t_ready = load_json(Path(args.ls6t_ready_result))
    ls6t_confirmation = load_json(Path(args.ls6t_confirmation_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    errors: list[str] = []
    validate_common(
        policy,
        ls6w_validation,
        ls6w_run,
        ls6w_preflight,
        ls6w_lock,
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
        status = STATUS_TEMPLATE_READY if not errors else STATUS_NOT_READY
        source_doc = template
    else:
        gate_path = Path(args.gate)
        if not gate_path.exists():
            errors.append("gate file missing")
            gate_doc: dict[str, Any] = template
        else:
            gate_doc = load_json(gate_path)
            validate_gate(gate_doc, errors)
        status = STATUS_READY if not errors else STATUS_NOT_READY
        source_doc = gate_doc

    result = build_result(status, policy, source_doc, ls6w_validation, ls6v_ready, ls6t_ready, ls6r_ready, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
