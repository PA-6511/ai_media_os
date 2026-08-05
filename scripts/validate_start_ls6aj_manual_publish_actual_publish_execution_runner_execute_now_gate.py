#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate.template.json")
    parser.add_argument("--execute-now", default="exchange/human_review/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate.json")
    parser.add_argument("--ls6ai-run-result", default="exchange/logs/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_result.json")
    parser.add_argument("--ls6ai-validation-result", default="exchange/logs/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_validation_result.json")
    parser.add_argument("--ls6ai-wordpress-current-draft-status-result", default="exchange/runtime/start_ls6ai_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--ls6ai-final-preflight-result", default="exchange/runtime/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_result.json")
    parser.add_argument("--ls6ai-final-preflight-lock", default="exchange/locks/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight.lock.json")
    parser.add_argument("--ls6ah-validation-result", default="exchange/logs/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary_validation_result.json")
    parser.add_argument("--ls6ah-boundary-result", default="exchange/runtime/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary_result.json")
    parser.add_argument("--ls6ah-boundary-lock", default="exchange/locks/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary.lock.json")
    parser.add_argument("--ls6ag-ready-result", default="exchange/logs/start_ls6ag_manual_publish_actual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6ag-command-result", default="exchange/human_review/start_ls6ag_manual_publish_actual_publish_final_execution_command.json")
    parser.add_argument("--ls6af-validation-result", default="exchange/logs/start_ls6af_manual_publish_actual_publish_runner_final_gate_validation_result.json")
    parser.add_argument("--ls6af-runner-final-gate-result", default="exchange/runtime/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
    parser.add_argument("--ls6af-runner-final-gate-lock", default="exchange/locks/start_ls6af_manual_publish_actual_publish_runner_final_gate.lock.json")
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
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate_ready_report.md")
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
        "# LS-6AJ Manual Publish Actual Publish Execution Runner Execute-Now Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- execute_now_status: {result['execute_now_status']}",
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


def get_ls6ac_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("actual_publish_execute_now_final_confirmation_consumed", safe_get(doc, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed"))


def get_ls6ac_explicit_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("explicit_execute_now_for_actual_publish_consumed", safe_get(doc, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_consumed"))


def get_ls6z_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("final_explicit_publish_execution_command_consumed", safe_get(doc, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed"))


def get_ls6x_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("actual_publish_execution_gate_consumed", safe_get(doc, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed"))


def get_ls6v_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("final_execution_command_consumed", safe_get(doc, "final_execution_command", "final_execution_command_consumed"))


def get_ls6t_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("execute_now_confirmation_consumed", safe_get(doc, "confirmation", "execute_now_confirmation_consumed"))


def get_ls6r_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("approval_label_consumed", safe_get(doc, "approval", "approval_label_consumed"))


def validate_gate_doc(doc: dict[str, Any], *, is_template: bool, errors: list[str]) -> None:
    if is_template:
        req(doc.get("document_type") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_TEMPLATE", "template document_type mismatch", errors)
        req(doc.get("execute_now_status") == "TEMPLATE_NOT_CONFIRMED", "template execute_now_status mismatch", errors)
    else:
        req(doc.get("document_type") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE", "execute-now document_type mismatch", errors)
        req(doc.get("execute_now_status") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION", "execute-now status mismatch", errors)

    target = doc.get("target_post", {})
    gate = doc.get("actual_publish_execution_runner_execute_now_gate", {})
    upstream = doc.get("upstream_consumption_state", {})
    current = doc.get("current_phase_execution", {})

    req(target.get("post_id") == 183, "target_post.post_id mismatch", errors)
    req(target.get("post_link") == "https://hoshido.jp/?p=183", "target_post.post_link mismatch", errors)
    req(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    req(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)
    req(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)

    req(gate.get("required_actual_publish_execution_runner_execute_now_label") == "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "required execute-now label mismatch", errors)
    if is_template:
        req(gate.get("actual_publish_execution_runner_execute_now_label") == "", "template execute-now label must be empty", errors)
    else:
        req(gate.get("actual_publish_execution_runner_execute_now_label") == "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "execute-now label mismatch", errors)
        req(gate.get("requires_next_phase") == "LS-6AK", "execute-now requires_next_phase mismatch", errors)

    req(gate.get("actual_publish_execution_runner_execute_now_consumed") is False, "actual_publish_execution_runner_execute_now_consumed must be false", errors)
    req(gate.get("actual_publish_execution_runner_final_preflight_ready") is True, "actual_publish_execution_runner_final_preflight_ready must be true", errors)
    req(gate.get("actual_publish_execution_runner_final_preflight_consumed") is False, "actual_publish_execution_runner_final_preflight_consumed must be false", errors)
    req(gate.get("actual_publish_execution_runner_boundary_ready") is True, "actual_publish_execution_runner_boundary_ready must be true", errors)
    req(gate.get("actual_publish_execution_runner_boundary_consumed") is False, "actual_publish_execution_runner_boundary_consumed must be false", errors)
    req(gate.get("actual_publish_final_execution_command_recorded") is True, "actual_publish_final_execution_command_recorded must be true", errors)
    req(gate.get("actual_publish_final_execution_command_consumed") is False, "actual_publish_final_execution_command_consumed must be false", errors)
    req(gate.get("actual_publish_runner_final_gate_ready") is True, "actual_publish_runner_final_gate_ready must be true", errors)
    req(gate.get("actual_publish_runner_final_gate_consumed") is False, "actual_publish_runner_final_gate_consumed must be false", errors)
    req(gate.get("actual_publish_final_preflight_ready") is True, "actual_publish_final_preflight_ready must be true", errors)
    req(gate.get("actual_publish_final_preflight_consumed") is False, "actual_publish_final_preflight_consumed must be false", errors)
    req(gate.get("actual_publish_execution_boundary_ready") is True, "actual_publish_execution_boundary_ready must be true", errors)
    req(gate.get("actual_publish_execution_boundary_consumed") is False, "actual_publish_execution_boundary_consumed must be false", errors)
    req(gate.get("actual_publish_execute_now_final_confirmation_consumed") is False, "actual_publish_execute_now_final_confirmation_consumed must be false", errors)
    req(gate.get("explicit_execute_now_for_actual_publish_required") is True, "explicit_execute_now_for_actual_publish_required must be true", errors)
    req(gate.get("explicit_execute_now_for_actual_publish_received") is True, "explicit_execute_now_for_actual_publish_received must be true", errors)
    req(gate.get("explicit_execute_now_for_actual_publish_consumed") is False, "explicit_execute_now_for_actual_publish_consumed must be false", errors)
    req(gate.get("actual_publish_execution_runner_ready") is True, "actual_publish_execution_runner_ready must be true", errors)
    req(gate.get("actual_publish_execution_runner_executed") is False, "actual_publish_execution_runner_executed must be false", errors)
    req(gate.get("actual_publish_execution_runner_blocked") is True, "actual_publish_execution_runner_blocked must be true", errors)
    req(gate.get("actual_publish_execution_allowed_by_this_phase") is False, "actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(gate.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)

    for key in [
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
    ]:
        req(upstream.get(key) is False, f"upstream_consumption_state.{key} must be false", errors)

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
        "credential_env_read_executed",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]:
        req(current.get(key) is False, f"current_phase_execution.{key} must be false", errors)


def validate_upstream(args: argparse.Namespace, errors: list[str]) -> dict[str, Any]:
    policy = try_load_json(Path(args.policy), errors)
    ls6ai_run = try_load_json(Path(args.ls6ai_run_result), errors)
    ls6ai_validation = try_load_json(Path(args.ls6ai_validation_result), errors)
    ls6ai_wp = try_load_json(Path(args.ls6ai_wordpress_current_draft_status_result), errors)
    ls6ai_final = try_load_json(Path(args.ls6ai_final_preflight_result), errors)
    ls6ai_lock = try_load_json(Path(args.ls6ai_final_preflight_lock), errors)

    ls6ah_validation = try_load_json(Path(args.ls6ah_validation_result), errors)
    ls6ah_boundary = try_load_json(Path(args.ls6ah_boundary_result), errors)
    ls6ah_lock = try_load_json(Path(args.ls6ah_boundary_lock), errors)

    ls6ag_ready = try_load_json(Path(args.ls6ag_ready_result), errors)
    ls6ag_command = try_load_json(Path(args.ls6ag_command_result), errors)

    ls6af_validation = try_load_json(Path(args.ls6af_validation_result), errors)
    ls6af_runtime = try_load_json(Path(args.ls6af_runner_final_gate_result), errors)
    ls6af_lock = try_load_json(Path(args.ls6af_runner_final_gate_lock), errors)

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
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    req(policy.get("phase") == "LS-6AJ", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6ai_run.get("status") == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6AI run status mismatch", errors)
    req(ls6ai_validation.get("status") == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AI validation status mismatch", errors)
    req(ls6ai_run.get("post_id") == 183, "LS-6AI post_id mismatch", errors)
    req(ls6ai_run.get("returned_post_status") == "draft", "LS-6AI returned_post_status mismatch", errors)
    req(ls6ai_run.get("draft_verified") is True, "LS-6AI draft_verified must be true", errors)
    req(ls6ai_run.get("actual_publish_execution_runner_final_preflight_ready") is True, "LS-6AI final preflight ready must be true", errors)
    req(ls6ai_run.get("actual_publish_execution_runner_final_preflight_consumed") is False, "LS-6AI final preflight consumed must be false", errors)
    req(ls6ai_run.get("wordpress_get_executed") is True, "LS-6AI wordpress_get_executed must be true", errors)
    req(ls6ai_run.get("wordpress_get_post_id") == 183, "LS-6AI wordpress_get_post_id mismatch", errors)
    req(ls6ai_run.get("requires_actual_publish_execution_runner_execute_now") is True, "LS-6AI requires_actual_publish_execution_runner_execute_now must be true", errors)
    req(ls6ai_run.get("publish_execution_still_blocked") is True, "LS-6AI publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6ai_run, "next_phase", "phase") == "LS-6AJ", "LS-6AI next_phase mismatch", errors)

    req(ls6ai_wp.get("returned_post_status") == "draft", "LS-6AI wordpress verification returned_post_status mismatch", errors)
    req(ls6ai_wp.get("wordpress_get_executed") is True, "LS-6AI wordpress verification get must be true", errors)
    req(ls6ai_wp.get("wordpress_get_post_id") == 183, "LS-6AI wordpress verification post id mismatch", errors)

    req(ls6ai_final.get("actual_publish_execution_runner_final_preflight_ready") is True, "LS-6AI runtime final preflight ready must be true", errors)
    req(ls6ai_final.get("actual_publish_execution_runner_final_preflight_consumed") is False, "LS-6AI runtime final preflight consumed must be false", errors)
    req(ls6ai_lock.get("actual_publish_execution_runner_final_preflight_consumed") is False, "LS-6AI lock final preflight consumed must be false", errors)

    req(ls6ah_validation.get("status") == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AH validation status mismatch", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_ready") is True, "LS-6AH boundary ready must be true", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH boundary consumed must be false", errors)
    req(ls6ah_lock.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH lock boundary consumed must be false", errors)

    req(ls6ag_ready.get("status") == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6AG ready status mismatch", errors)
    req(ls6ag_ready.get("command_status") == "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AG command_status mismatch", errors)
    req(ls6ag_ready.get("actual_publish_final_execution_command_label") == "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "LS-6AG label mismatch", errors)
    req(ls6ag_ready.get("actual_publish_final_execution_command_consumed") is False, "LS-6AG consumed must be false", errors)
    req(safe_get(ls6ag_command, "actual_publish_final_execution_command", "actual_publish_final_execution_command_consumed") is False, "LS-6AG command consumed must be false", errors)

    req(ls6af_validation.get("status") == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH", "LS-6AF validation status mismatch", errors)
    req(ls6af_runtime.get("actual_publish_runner_final_gate_ready") is True, "LS-6AF runner final gate ready must be true", errors)
    req(ls6af_runtime.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF runner final gate consumed must be false", errors)
    req(ls6af_lock.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF lock runner final gate consumed must be false", errors)

    req(ls6ae_validation.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AE validation status mismatch", errors)
    req(ls6ae_validation.get("draft_verified") is True, "LS-6AE draft_verified must be true", errors)
    req(ls6ae_wp.get("returned_post_status") == "draft", "LS-6AE wordpress returned_post_status mismatch", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_ready") is True, "LS-6AE final preflight ready must be true", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_consumed") is False, "LS-6AE final preflight consumed must be false", errors)
    req(ls6ae_lock.get("actual_publish_final_preflight_consumed") is False, "LS-6AE lock final preflight consumed must be false", errors)

    req(ls6ad_validation.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AD validation status mismatch", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_ready") is True, "LS-6AD boundary ready must be true", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD boundary consumed must be false", errors)
    req(ls6ad_lock.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD lock boundary consumed must be false", errors)

    req(ls6ac_ready.get("status") == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "LS-6AC status mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "LS-6AC label mismatch", errors)
    req(get_ls6ac_consumed(ls6ac_ready) is False, "LS-6AC consumed must be false", errors)
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
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock preflight consumed must be false", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z status mismatch", errors)
    req(get_ls6z_consumed(ls6z_ready) is False, "LS-6Z consumed must be false", errors)
    req(get_ls6z_consumed(ls6z_command) is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X status mismatch", errors)
    req(get_ls6x_consumed(ls6x_ready) is False, "LS-6X consumed must be false", errors)
    req(get_ls6x_consumed(ls6x_gate) is False, "LS-6X gate consumed must be false", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V status mismatch", errors)
    req(get_ls6v_consumed(ls6v_ready) is False, "LS-6V consumed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T status mismatch", errors)
    req(get_ls6t_consumed(ls6t_ready) is False, "LS-6T consumed must be false", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R status mismatch", errors)
    req(get_ls6r_consumed(ls6r_ready) is False, "LS-6R consumed must be false", errors)

    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6OC1 rerun_allowed must be false", errors)
    return ls6ai_run


def build_result(status: str, gate_doc: dict[str, Any], ls6ai_run: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    target = gate_doc.get("target_post", {})
    gate = gate_doc.get("actual_publish_execution_runner_execute_now_gate", {})
    upstream = gate_doc.get("upstream_consumption_state", {})
    current = gate_doc.get("current_phase_execution", {})

    return {
        "phase": "LS-6AJ",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": target.get("post_id", 183),
        "post_link": target.get("post_link", "https://hoshido.jp/?p=183"),
        "payload_title": target.get("title", "2.5次元の誘惑"),
        "payload_asin": target.get("asin", "B07X2G67B4"),
        "returned_post_status": ls6ai_run.get("returned_post_status", "draft"),
        "ls6ai_final_preflight_validated": True,
        "ls6ai_draft_verified": True,
        "actual_publish_execution_runner_execute_now_recorded": gate_doc.get("execute_now_status") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION",
        "execute_now_status": gate_doc.get("execute_now_status", ""),
        "actual_publish_execution_runner_execute_now_label": gate.get("actual_publish_execution_runner_execute_now_label", ""),
        "actual_publish_execution_runner_execute_now_consumed": bool(gate.get("actual_publish_execution_runner_execute_now_consumed", False)),
        "actual_publish_execution_runner_final_preflight_ready": bool(gate.get("actual_publish_execution_runner_final_preflight_ready", False)),
        "actual_publish_execution_runner_final_preflight_consumed": bool(gate.get("actual_publish_execution_runner_final_preflight_consumed", False)),
        "actual_publish_execution_runner_boundary_ready": bool(gate.get("actual_publish_execution_runner_boundary_ready", False)),
        "actual_publish_execution_runner_boundary_consumed": bool(gate.get("actual_publish_execution_runner_boundary_consumed", False)),
        "actual_publish_final_execution_command_recorded": bool(gate.get("actual_publish_final_execution_command_recorded", False)),
        "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
        "actual_publish_final_execution_command_consumed": bool(gate.get("actual_publish_final_execution_command_consumed", False)),
        "actual_publish_runner_final_gate_ready": bool(gate.get("actual_publish_runner_final_gate_ready", False)),
        "actual_publish_runner_final_gate_consumed": bool(gate.get("actual_publish_runner_final_gate_consumed", False)),
        "actual_publish_final_preflight_ready": bool(gate.get("actual_publish_final_preflight_ready", False)),
        "actual_publish_final_preflight_consumed": bool(gate.get("actual_publish_final_preflight_consumed", False)),
        "actual_publish_execution_boundary_ready": bool(gate.get("actual_publish_execution_boundary_ready", False)),
        "actual_publish_execution_boundary_consumed": bool(gate.get("actual_publish_execution_boundary_consumed", False)),
        "actual_publish_execute_now_final_confirmation_label": "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY",
        "actual_publish_execute_now_final_confirmation_consumed": bool(gate.get("actual_publish_execute_now_final_confirmation_consumed", False)),
        "explicit_execute_now_for_actual_publish_required": bool(gate.get("explicit_execute_now_for_actual_publish_required", False)),
        "explicit_execute_now_for_actual_publish_received": bool(gate.get("explicit_execute_now_for_actual_publish_received", False)),
        "explicit_execute_now_for_actual_publish_consumed": bool(gate.get("explicit_execute_now_for_actual_publish_consumed", False)),
        "actual_publish_execution_runner_ready": bool(gate.get("actual_publish_execution_runner_ready", False)),
        "actual_publish_execution_runner_executed": bool(gate.get("actual_publish_execution_runner_executed", False)),
        "actual_publish_execution_runner_blocked": bool(gate.get("actual_publish_execution_runner_blocked", False)),
        "final_explicit_publish_execution_command_label": "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY",
        "final_explicit_publish_execution_command_consumed": bool(upstream.get("final_explicit_publish_execution_command_consumed", False)),
        "actual_publish_execution_final_preflight_ready": True,
        "actual_publish_execution_final_preflight_consumed": bool(upstream.get("actual_publish_execution_final_preflight_consumed", False)),
        "actual_publish_runner_boundary_consumed": bool(upstream.get("actual_publish_runner_boundary_consumed", False)),
        "actual_publish_execution_gate_consumed": bool(upstream.get("actual_publish_execution_gate_consumed", False)),
        "final_execution_command_consumed": bool(upstream.get("final_execution_command_consumed", False)),
        "approval_label_consumed": bool(upstream.get("approval_label_consumed", False)),
        "execute_now_confirmation_consumed": bool(upstream.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(gate.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(gate.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(gate.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(gate.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(gate.get("manual_publish_executed", False)),
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
        "credential_env_read_executed": bool(current.get("credential_env_read_executed", False)),
        "credential_value_output": bool(current.get("credential_value_output", False)),
        "credential_value_persisted": bool(current.get("credential_value_persisted", False)),
        "credential_secret_output": bool(current.get("credential_secret_output", False)),
        "secret_length_output": bool(current.get("secret_length_output", False)),
        "secret_hash_output": bool(current.get("secret_hash_output", False)),
        "authorization_header_output": bool(current.get("authorization_header_output", False)),
        "rerun_allowed": bool(current.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(current.get("ls6oc1_rerun_executed", False)),
        "requires_actual_publish_execution_runner_final_boundary": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AK",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_final_boundary": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    ls6ai_run = validate_upstream(args, errors)

    template_doc = try_load_json(Path(args.template), errors)
    validate_gate_doc(template_doc, is_template=True, errors=errors)

    selected_doc = template_doc
    status = STATUS_TEMPLATE_READY if not errors else STATUS_NOT_READY

    if not args.allow_template:
        execute_now_doc = try_load_json(Path(args.execute_now), errors)
        validate_gate_doc(execute_now_doc, is_template=False, errors=errors)
        selected_doc = execute_now_doc
        status = STATUS_READY if not errors else STATUS_NOT_READY

    result = build_result(status, selected_doc, ls6ai_run, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
