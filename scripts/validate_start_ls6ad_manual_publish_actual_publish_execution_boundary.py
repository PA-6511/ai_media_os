#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ad_manual_publish_actual_publish_execution_boundary_policy.json")
    parser.add_argument("--boundary-result", default="exchange/runtime/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
    parser.add_argument("--boundary-lock", default="exchange/locks/start_ls6ad_manual_publish_actual_publish_execution_boundary.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
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
    parser.add_argument("--output", default="exchange/logs/start_ls6ad_manual_publish_actual_publish_execution_boundary_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6ad_manual_publish_actual_publish_execution_boundary_validation_report.md")
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
        "# LS-6AD Manual Publish Actual Publish Execution Boundary Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- actual_publish_execution_boundary_ready: {result['actual_publish_execution_boundary_ready']}",
        f"- actual_publish_execution_runner_ready: {result['actual_publish_execution_runner_ready']}",
        f"- locked: {result['locked']}",
        f"- requires_actual_publish_final_preflight: {result['requires_actual_publish_final_preflight']}",
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


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def check_false_flags(doc: dict[str, Any], prefix: str, errors: list[str]) -> None:
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
        k_cread(),
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
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
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]:
        req(doc.get(key, False) is False, f"{prefix}.{key} must be false", errors)


def build_result(run_result: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AD",
        "status": STATUS_VALIDATED if not errors else STATUS_NOT_READY,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_BOUNDARY_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": run_result.get("post_id", 0),
        "post_link": run_result.get("post_link", ""),
        "payload_title": run_result.get("payload_title", ""),
        "payload_asin": run_result.get("payload_asin", ""),
        "returned_post_status": run_result.get("returned_post_status", ""),
        "ls6ac_execute_now_final_confirmation_validated": bool(run_result.get("ls6ac_execute_now_final_confirmation_validated", False)),
        "actual_publish_execution_boundary_ready": bool(run_result.get("actual_publish_execution_boundary_ready", False)),
        "actual_publish_execution_boundary_consumed": bool(run_result.get("actual_publish_execution_boundary_consumed", False)),
        "actual_publish_execute_now_final_confirmation_label": run_result.get("actual_publish_execute_now_final_confirmation_label", ""),
        "actual_publish_execute_now_final_confirmation_consumed": bool(run_result.get("actual_publish_execute_now_final_confirmation_consumed", False)),
        "explicit_execute_now_for_actual_publish_required": bool(run_result.get("explicit_execute_now_for_actual_publish_required", False)),
        "explicit_execute_now_for_actual_publish_received": bool(run_result.get("explicit_execute_now_for_actual_publish_received", False)),
        "explicit_execute_now_for_actual_publish_consumed": bool(run_result.get("explicit_execute_now_for_actual_publish_consumed", False)),
        "actual_publish_execution_runner_ready": bool(run_result.get("actual_publish_execution_runner_ready", False)),
        "actual_publish_execution_runner_executed": bool(run_result.get("actual_publish_execution_runner_executed", False)),
        "actual_publish_execution_runner_blocked": bool(run_result.get("actual_publish_execution_runner_blocked", False)),
        "final_explicit_publish_execution_command_label": run_result.get("final_explicit_publish_execution_command_label", ""),
        "final_explicit_publish_execution_command_consumed": bool(run_result.get("final_explicit_publish_execution_command_consumed", False)),
        "actual_publish_execution_final_preflight_ready": bool(run_result.get("actual_publish_execution_final_preflight_ready", False)),
        "actual_publish_execution_final_preflight_consumed": bool(run_result.get("actual_publish_execution_final_preflight_consumed", False)),
        "actual_publish_runner_boundary_consumed": bool(run_result.get("actual_publish_runner_boundary_consumed", False)),
        "actual_publish_execution_gate_consumed": bool(run_result.get("actual_publish_execution_gate_consumed", False)),
        "final_execution_command_consumed": bool(run_result.get("final_execution_command_consumed", False)),
        "approval_label_consumed": bool(run_result.get("approval_label_consumed", False)),
        "execute_now_confirmation_consumed": bool(run_result.get("execute_now_confirmation_consumed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(run_result.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(run_result.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(run_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(run_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(run_result.get("manual_publish_executed", False)),
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
        k_cread(): bool(run_result.get(k_cread(), False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": True,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_final_preflight": bool(run_result.get("requires_actual_publish_final_preflight", False)),
        "requires_separate_publish_execution_phase": bool(run_result.get("requires_separate_publish_execution_phase", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "next_phase": {
            "phase": "LS-6AE",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_final_preflight": True,
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
    boundary_result = try_load_json(Path(args.boundary_result), errors)
    boundary_lock = try_load_json(Path(args.boundary_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)

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

    req(policy.get("phase") == "LS-6AD", "policy.phase mismatch", errors)

    req(run_result.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH", "run status mismatch", errors)
    req(boundary_result.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_READY_NO_PUBLISH", "boundary result status mismatch", errors)
    req(boundary_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH", "boundary lock status mismatch", errors)

    for doc, name in [(run_result, "run_result"), (boundary_result, "boundary_result")]:
        req(doc.get("post_id") == 183, f"{name}.post_id mismatch", errors)
        req(doc.get("returned_post_status") == "draft", f"{name}.returned_post_status mismatch", errors)
        req(doc.get("ls6ac_execute_now_final_confirmation_validated") is True, f"{name}.ls6ac_execute_now_final_confirmation_validated must be true", errors)
        req(doc.get("actual_publish_execution_boundary_ready") is True, f"{name}.actual_publish_execution_boundary_ready must be true", errors)
        req(doc.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", f"{name}.confirmation label mismatch", errors)
        req(doc.get("explicit_execute_now_for_actual_publish_required") is True, f"{name}.explicit required must be true", errors)
        req(doc.get("explicit_execute_now_for_actual_publish_received") is True, f"{name}.explicit received must be true", errors)
        req(doc.get("actual_publish_execution_runner_ready") is True, f"{name}.runner ready must be true", errors)
        req(doc.get("actual_publish_execution_runner_blocked") is True, f"{name}.runner blocked must be true", errors)
        req(doc.get("actual_publish_execution_final_preflight_ready") is True, f"{name}.preflight ready must be true", errors)
        req(doc.get("requires_actual_publish_final_preflight") is True, f"{name}.requires_actual_publish_final_preflight must be true", errors)
        req(doc.get("requires_separate_publish_execution_phase") is True, f"{name}.requires_separate_publish_execution_phase must be true", errors)
        req(doc.get("publish_execution_still_blocked") is True, f"{name}.publish_execution_still_blocked must be true", errors)
        check_false_flags(doc, name, errors)

    req(boundary_lock.get("locked") is True, "lock.locked must be true", errors)
    req(boundary_lock.get("rerun_allowed") is False, "lock.rerun_allowed must be false", errors)
    req(boundary_lock.get("ls6oc1_rerun_executed") is False, "lock.ls6oc1_rerun_executed must be false", errors)
    req(boundary_lock.get("requires_next_phase") == "LS-6AE", "lock.requires_next_phase mismatch", errors)

    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC consumed must remain false", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC confirmation consumed must remain false", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AC explicit consumed must remain false", errors)
    req(ls6ac_ready.get("actual_publish_execution_runner_executed") is False, "LS-6AC runner executed must remain false", errors)
    req(ls6ac_ready.get("manual_publish_executed") is False, "LS-6AC manual publish executed must remain false", errors)

    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner executed must remain false", errors)
    req(ls6ab_blocked.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AB explicit consumed must remain false", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must remain false", errors)

    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must remain false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock preflight consumed must remain false", errors)

    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z consumed must remain false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must remain false", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must remain false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must remain false", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X consumed must remain false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must remain false", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V consumed must remain false", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T consumed must remain false", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R consumed must remain false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must remain false", errors)

    req(safe_get(run_result, "next_phase", "phase") == "LS-6AE", "next_phase.phase mismatch", errors)
    req(safe_get(run_result, "next_phase", "requires_actual_publish_final_preflight") is True, "next_phase.requires_actual_publish_final_preflight must be true", errors)
    req(safe_get(run_result, "next_phase", "publish_execution_still_blocked") is True, "next_phase.publish_execution_still_blocked must be true", errors)

    result = build_result(run_result, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
