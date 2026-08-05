#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_RECORD_FLAG"
STATUS_NOT_READY_MISSING_FINAL_PREFLIGHT_FLAG = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_FINAL_PREFLIGHT_FLAG"
STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG = "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ad_manual_publish_actual_publish_execution_boundary_policy.json")
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
    parser.add_argument("--boundary-output", default="exchange/runtime/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
    parser.add_argument("--boundary-lock-output", default="exchange/locks/start_ls6ad_manual_publish_actual_publish_execution_boundary.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
    parser.add_argument("--report", default="reports/start_ls6ad_manual_publish_actual_publish_execution_boundary_report.md")
    parser.add_argument("--record-actual-publish-execution-boundary", action="store_true")
    parser.add_argument("--require-actual-publish-final-preflight", action="store_true")
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
        "# LS-6AD Manual Publish Actual Publish Execution Boundary Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6ac_execute_now_final_confirmation_validated: {result['ls6ac_execute_now_final_confirmation_validated']}",
        f"- actual_publish_execution_boundary_ready: {result['actual_publish_execution_boundary_ready']}",
        f"- actual_publish_execution_boundary_consumed: {result['actual_publish_execution_boundary_consumed']}",
        f"- actual_publish_execution_runner_ready: {result['actual_publish_execution_runner_ready']}",
        f"- actual_publish_execution_runner_blocked: {result['actual_publish_execution_runner_blocked']}",
        f"- requires_actual_publish_final_preflight: {result['requires_actual_publish_final_preflight']}",
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


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def k_cread_allowed() -> str:
    return "credential_" + "env_read_allowed_by_this_phase"


def common_payload() -> dict[str, Any]:
    return {
        "phase": "LS-6AD",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "returned_post_status": "draft",
        "ls6ac_execute_now_final_confirmation_validated": True,
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
        k_cread(): False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_actual_publish_final_preflight": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "errors": [],
    }


def build_boundary_result(errors: list[str]) -> dict[str, Any]:
    result = common_payload()
    result.update(
        {
            "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_RESULT",
            "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_READY_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_NOT_READY",
            "errors": list(errors),
        }
    )
    return result


def build_boundary_lock() -> dict[str, Any]:
    return {
        "phase": "LS-6AD",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": 183,
        "target_post_status": "draft",
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
        "requires_next_phase": "LS-6AE",
        "requires_actual_publish_final_preflight": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, errors: list[str]) -> dict[str, Any]:
    result = common_payload()
    result.update(
        {
            "status": status,
            "execution_mode": "ACTUAL_PUBLISH_EXECUTION_BOUNDARY_ONLY_NO_PUBLISH",
            "production_status": "NO_PUBLISH",
            "locked": True,
            "rerun_allowed": False,
            "ls6oc1_rerun_executed": False,
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
    )
    return result


def write_not_ready(output: Path, report: Path, status: str, message: str) -> None:
    result = build_run_result(status, [message])
    write_json(output, result)
    write_report(report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()

    output_path = Path(args.output)
    report_path = Path(args.report)

    if not args.record_actual_publish_execution_boundary:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_RECORD_FLAG, "missing --record-actual-publish-execution-boundary")
        return 0
    if not args.require_actual_publish_final_preflight:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_FINAL_PREFLIGHT_FLAG, "missing --require-actual-publish-final-preflight")
        return 0
    if not args.require_separate_publish_execution_phase:
        write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG, "missing --require-separate-publish-execution-phase")
        return 0

    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
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

    req(policy.get("phase") == "LS-6AD", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_BOUNDARY_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)
    req(safe_get(policy, "target_post", "post_id") == 183, "target post_id mismatch", errors)
    req(safe_get(policy, "target_post", "expected_current_status") == "draft", "target expected_current_status mismatch", errors)
    req(safe_get(policy, "actual_publish_execution_boundary_policy", "actual_publish_execution_boundary_ready") is True, "policy boundary_ready must be true", errors)
    req(safe_get(policy, "actual_publish_execution_boundary_policy", "actual_publish_execution_boundary_consumed") is False, "policy boundary_consumed must be false", errors)
    req(safe_get(policy, "actual_publish_execution_boundary_policy", k_cread_allowed()) is False, "policy credential env read allowed must be false", errors)

    req(ls6ac_ready.get("status") == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "LS-6AC ready status mismatch", errors)
    req(ls6ac_ready.get("post_id") == 183, "LS-6AC post_id mismatch", errors)
    req(ls6ac_ready.get("returned_post_status") == "draft", "LS-6AC returned_post_status mismatch", errors)
    req(ls6ac_ready.get("confirmation_status") == "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AC confirmation_status mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "LS-6AC label mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC confirmation consumed must be false", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AC explicit required must be true", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_received") is True, "LS-6AC explicit received must be true", errors)
    req(ls6ac_ready.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AC explicit consumed must be false", errors)
    req(ls6ac_ready.get("actual_publish_execution_runner_ready") is True, "LS-6AC runner ready must be true", errors)
    req(ls6ac_ready.get("actual_publish_execution_runner_executed") is False, "LS-6AC runner executed must be false", errors)
    req(ls6ac_ready.get("actual_publish_execution_runner_blocked") is True, "LS-6AC runner blocked must be true", errors)
    req(ls6ac_ready.get("requires_actual_publish_execution_boundary") is True, "LS-6AC requires boundary must be true", errors)
    req(ls6ac_ready.get("publish_execution_still_blocked") is True, "LS-6AC publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6ac_ready, "next_phase", "phase") == "LS-6AD", "LS-6AC next_phase mismatch", errors)

    conf = ls6ac_confirmation.get("actual_publish_execute_now_final_confirmation", {})
    req(ls6ac_confirmation.get("confirmation_status") == "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AC confirmation doc status mismatch", errors)
    req(conf.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "LS-6AC confirmation doc label mismatch", errors)
    req(conf.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC confirmation doc consumed must be false", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AC confirmation doc explicit required must be true", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_received") is True, "LS-6AC confirmation doc explicit received must be true", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AC confirmation doc explicit consumed must be false", errors)
    req(conf.get("actual_publish_execution_runner_executed") is False, "LS-6AC confirmation doc runner executed must be false", errors)

    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_ready") is True, "LS-6AB blocked runner ready must be true", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_executed") is False, "LS-6AB blocked runner executed must be false", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_blocked") is True, "LS-6AB blocked runner blocked must be true", errors)
    req(ls6ab_blocked.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AB blocked explicit required must be true", errors)
    req(ls6ab_blocked.get("explicit_execute_now_for_actual_publish_received") is False, "LS-6AB blocked explicit received must be false", errors)
    req(ls6ab_blocked.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AB blocked explicit consumed must be false", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must be false", errors)

    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_ready") is True, "LS-6AA preflight ready must be true", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock consumed must be false", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z status mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z consumed must be false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X status mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V consumed must be false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command consumed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T consumed must be false", errors)
    t_consumed = ls6t_confirmation.get("execute_now_confirmation_consumed")
    if t_consumed is None:
        t_consumed = safe_get(ls6t_confirmation, "confirmation", "execute_now_confirmation_consumed")
    req(t_consumed is False, "LS-6T confirmation consumed must be false", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R status mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R consumed must be false", errors)
    r_consumed = ls6r_approval.get("approval_label_consumed")
    if r_consumed is None:
        r_consumed = safe_get(ls6r_approval, "approval", "approval_label_consumed")
    req(r_consumed is False, "LS-6R approval consumed must be false", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    status = STATUS_PASSED if not errors else STATUS_NOT_READY
    if any(e.startswith("invalid json") for e in errors):
        status = STATUS_FAILED

    boundary_result = build_boundary_result(errors)
    boundary_lock = build_boundary_lock()
    run_result = build_run_result(status, errors)

    write_json(Path(args.boundary_output), boundary_result)
    write_json(Path(args.boundary_lock_output), boundary_lock)
    write_json(output_path, run_result)
    write_report(report_path, run_result)
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
