#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6af_manual_publish_actual_publish_runner_final_gate_policy.json")
    parser.add_argument("--actual-publish-runner-final-gate-result", default="exchange/runtime/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
    parser.add_argument("--actual-publish-runner-final-gate-lock", default="exchange/locks/start_ls6af_manual_publish_actual_publish_runner_final_gate.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
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
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6af_manual_publish_actual_publish_runner_final_gate_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6af_manual_publish_actual_publish_runner_final_gate_validation_report.md")
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
        "# LS-6AF Manual Publish Actual Publish Runner Final Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- actual_publish_runner_final_gate_ready: {result['actual_publish_runner_final_gate_ready']}",
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


def build_result(run: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AF",
        "status": STATUS_VALIDATED if not errors else STATUS_NOT_READY,
        "execution_mode": "ACTUAL_PUBLISH_RUNNER_FINAL_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": run.get("post_id", 0),
        "post_link": run.get("post_link", ""),
        "payload_title": run.get("payload_title", ""),
        "payload_asin": run.get("payload_asin", ""),
        "ls6ae_final_preflight_validated": bool(run.get("ls6ae_final_preflight_validated", False)),
        "ls6ae_draft_verified": bool(run.get("ls6ae_draft_verified", False)),
        "returned_post_status": run.get("returned_post_status", ""),
        "actual_publish_runner_final_gate_ready": bool(run.get("actual_publish_runner_final_gate_ready", False)),
        "actual_publish_runner_final_gate_consumed": bool(run.get("actual_publish_runner_final_gate_consumed", False)),
        "actual_publish_final_preflight_ready": bool(run.get("actual_publish_final_preflight_ready", False)),
        "actual_publish_final_preflight_consumed": bool(run.get("actual_publish_final_preflight_consumed", False)),
        "actual_publish_execution_boundary_ready": bool(run.get("actual_publish_execution_boundary_ready", False)),
        "actual_publish_execution_boundary_consumed": bool(run.get("actual_publish_execution_boundary_consumed", False)),
        "actual_publish_execute_now_final_confirmation_label": run.get("actual_publish_execute_now_final_confirmation_label", ""),
        "actual_publish_execute_now_final_confirmation_consumed": bool(run.get("actual_publish_execute_now_final_confirmation_consumed", False)),
        "explicit_execute_now_for_actual_publish_required": bool(run.get("explicit_execute_now_for_actual_publish_required", False)),
        "explicit_execute_now_for_actual_publish_received": bool(run.get("explicit_execute_now_for_actual_publish_received", False)),
        "explicit_execute_now_for_actual_publish_consumed": bool(run.get("explicit_execute_now_for_actual_publish_consumed", False)),
        "actual_publish_execution_runner_ready": bool(run.get("actual_publish_execution_runner_ready", False)),
        "actual_publish_execution_runner_executed": bool(run.get("actual_publish_execution_runner_executed", False)),
        "actual_publish_execution_runner_blocked": bool(run.get("actual_publish_execution_runner_blocked", False)),
        "final_explicit_publish_execution_command_label": run.get("final_explicit_publish_execution_command_label", ""),
        "final_explicit_publish_execution_command_consumed": bool(run.get("final_explicit_publish_execution_command_consumed", False)),
        "actual_publish_execution_final_preflight_ready": bool(run.get("actual_publish_execution_final_preflight_ready", False)),
        "actual_publish_execution_final_preflight_consumed": bool(run.get("actual_publish_execution_final_preflight_consumed", False)),
        "actual_publish_runner_boundary_consumed": bool(run.get("actual_publish_runner_boundary_consumed", False)),
        "actual_publish_execution_gate_consumed": bool(run.get("actual_publish_execution_gate_consumed", False)),
        "final_execution_command_consumed": bool(run.get("final_execution_command_consumed", False)),
        "approval_label_consumed": bool(run.get("approval_label_consumed", False)),
        "execute_now_confirmation_consumed": bool(run.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(run.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(run.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(run.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(run.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(run.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(run.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(run.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(run.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(run.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(run.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(run.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_existing_post_update_executed": bool(run.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(run.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run.get("publish_executed", False)),
        "future_schedule_executed": bool(run.get("future_schedule_executed", False)),
        "delete_executed": bool(run.get("delete_executed", False)),
        "post119_update_executed": bool(run.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(run.get("credential_env_read_executed", False)),
        "credential_value_output": bool(run.get("credential_value_output", False)),
        "credential_value_persisted": bool(run.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run.get("credential_secret_output", False)),
        "secret_length_output": bool(run.get("secret_length_output", False)),
        "secret_hash_output": bool(run.get("secret_hash_output", False)),
        "authorization_header_output": bool(run.get("authorization_header_output", False)),
        "locked": True,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_final_execution_command": bool(run.get("requires_actual_publish_final_execution_command", False)),
        "requires_separate_publish_execution_phase": bool(run.get("requires_separate_publish_execution_phase", False)),
        "publish_execution_still_blocked": bool(run.get("publish_execution_still_blocked", False)),
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


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    runtime = try_load_json(Path(args.actual_publish_runner_final_gate_result), errors)
    lock = try_load_json(Path(args.actual_publish_runner_final_gate_lock), errors)
    run = try_load_json(Path(args.run_result), errors)

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
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    req(policy.get("phase") == "LS-6AF", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_RUNNER_FINAL_GATE_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(run.get("status") == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_PASSED_NO_PUBLISH", "run status mismatch", errors)
    req(runtime.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_READY_NO_PUBLISH", "runtime status mismatch", errors)
    req(lock.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_LOCKED_NO_PUBLISH", "lock status mismatch", errors)

    req(ls6ae_run.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6AE run status mismatch", errors)
    req(ls6ae_validation.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AE validation status mismatch", errors)
    req(ls6ae_wp.get("wordpress_get_executed") is True, "LS-6AE wordpress get must be true", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_consumed") is False, "LS-6AE final preflight consumed must be false", errors)
    req(ls6ae_lock.get("actual_publish_final_preflight_consumed") is False, "LS-6AE lock final preflight consumed must be false", errors)

    req(ls6ad_validation.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AD validation status mismatch", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD boundary consumed must be false", errors)
    req(ls6ad_lock.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD lock boundary consumed must be false", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC consumed must be false", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC confirmation consumed must be false", errors)
    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner executed must be false", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must be false", errors)
    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock preflight consumed must be false", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z consumed must be false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V consumed must be false", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T consumed must be false", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R consumed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6OC1 rerun_allowed must be false", errors)

    req(run.get("post_id") == 183, "run.post_id mismatch", errors)
    req(run.get("post_link") == "https://hoshido.jp/?p=183", "run.post_link mismatch", errors)
    req(run.get("payload_title") == "2.5次元の誘惑", "run.payload_title mismatch", errors)
    req(run.get("payload_asin") == "B07X2G67B4", "run.payload_asin mismatch", errors)
    req(run.get("ls6ae_final_preflight_validated") is True, "run.ls6ae_final_preflight_validated must be true", errors)
    req(run.get("ls6ae_draft_verified") is True, "run.ls6ae_draft_verified must be true", errors)
    req(run.get("returned_post_status") == "draft", "run.returned_post_status mismatch", errors)
    req(run.get("actual_publish_runner_final_gate_ready") is True, "run.actual_publish_runner_final_gate_ready must be true", errors)
    req(run.get("actual_publish_final_preflight_ready") is True, "run.actual_publish_final_preflight_ready must be true", errors)
    req(run.get("actual_publish_execution_boundary_ready") is True, "run.actual_publish_execution_boundary_ready must be true", errors)
    req(run.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "run.confirmation label mismatch", errors)
    req(run.get("explicit_execute_now_for_actual_publish_required") is True, "run.explicit required must be true", errors)
    req(run.get("explicit_execute_now_for_actual_publish_received") is True, "run.explicit received must be true", errors)
    req(run.get("actual_publish_execution_runner_ready") is True, "run.runner ready must be true", errors)
    req(run.get("actual_publish_execution_runner_blocked") is True, "run.runner blocked must be true", errors)
    req(run.get("final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "run.final explicit label mismatch", errors)
    req(run.get("actual_publish_execution_final_preflight_ready") is True, "run.execution final preflight ready must be true", errors)

    false_keys = [
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
        "actual_publish_runner_final_gate_consumed",
        "actual_publish_final_preflight_consumed",
        "actual_publish_execution_boundary_consumed",
        "actual_publish_execute_now_final_confirmation_consumed",
        "explicit_execute_now_for_actual_publish_consumed",
        "actual_publish_execution_runner_executed",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
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
        "rerun_allowed",
        "ls6oc1_rerun_executed",
    ]
    for key in false_keys:
        req(run.get(key, False) is False, f"run.{key} must be false", errors)

    req(run.get("requires_actual_publish_final_execution_command") is True, "run.requires_actual_publish_final_execution_command must be true", errors)
    req(run.get("requires_separate_publish_execution_phase") is True, "run.requires_separate_publish_execution_phase must be true", errors)
    req(run.get("publish_execution_still_blocked") is True, "run.publish_execution_still_blocked must be true", errors)

    req(lock.get("locked") is True, "lock.locked must be true", errors)
    req(lock.get("rerun_allowed") is False, "lock.rerun_allowed must be false", errors)
    req(lock.get("ls6oc1_rerun_executed") is False, "lock.ls6oc1_rerun_executed must be false", errors)
    req(lock.get("requires_next_phase") == "LS-6AG", "lock.requires_next_phase mismatch", errors)

    next_phase = run.get("next_phase", {})
    req(safe_get(next_phase, "phase") == "LS-6AG", "run.next_phase.phase mismatch", errors)
    req(safe_get(next_phase, "execution_allowed") is False, "run.next_phase.execution_allowed must be false", errors)
    req(safe_get(next_phase, "manual_publish_execution_allowed_by_this_phase") is False, "run.next_phase.manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(next_phase, "actual_publish_execution_allowed_by_this_phase") is False, "run.next_phase.actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(next_phase, "actual_runner_execution_allowed_by_this_phase") is False, "run.next_phase.actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(safe_get(next_phase, "requires_actual_publish_final_execution_command") is True, "run.next_phase.requires_actual_publish_final_execution_command must be true", errors)
    req(safe_get(next_phase, "requires_separate_publish_execution_phase") is True, "run.next_phase.requires_separate_publish_execution_phase must be true", errors)
    req(safe_get(next_phase, "publish_execution_still_blocked") is True, "run.next_phase.publish_execution_still_blocked must be true", errors)

    result = build_result(run, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
