#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY"
STATUS_NOT_READY_MISSING_VERIFY_FLAG = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_NOT_READY_MISSING_PREFLIGHT_FLAG = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_PREFLIGHT_FLAG"
STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG"
STATUS_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG = "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_policy.json")
    parser.add_argument("--ls6z-ready-result", default="exchange/logs/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_result.json")
    parser.add_argument("--ls6z-command-result", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.json")
    parser.add_argument("--ls6y-validation-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--ls6y-boundary-preflight-result", default="exchange/runtime/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_preflight_result.json")
    parser.add_argument("--ls6y-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
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
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--wordpress-current-draft-status-output", default="exchange/runtime/start_ls6aa_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--actual-publish-execution-final-preflight-output", default="exchange/runtime/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--actual-publish-execution-final-preflight-lock-output", default="exchange/locks/start_ls6aa_manual_publish_actual_publish_execution_final_preflight.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--report", default="reports/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_report.md")
    parser.add_argument("--verify-current-draft", action="store_true")
    parser.add_argument("--record-actual-publish-execution-final-preflight", action="store_true")
    parser.add_argument("--require-separated-actual-publish-execution-phase", action="store_true")
    parser.add_argument("--require-explicit-execute-now-for-actual-publish", action="store_true")
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
        "# LS-6AA Manual Publish Actual Publish Execution Final Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result.get('post_id')}",
        f"- draft_verified: {result.get('draft_verified')}",
        f"- returned_post_status: {result.get('returned_post_status')}",
        f"- wordpress_get_executed: {result.get('wordpress_get_executed')}",
        f"- final_explicit_publish_execution_command_label: {result.get('final_explicit_publish_execution_command_label')}",
        f"- requires_explicit_execute_now_for_actual_publish: {result.get('requires_explicit_execute_now_for_actual_publish')}",
        f"- publish_execution_still_blocked: {result.get('publish_execution_still_blocked')}",
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


def parse_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, val = line.split("=", 1)
        env[k.strip()] = val.strip()
    return env


def verify_current_draft(base_url: str, username: str, password: str, post_id: int) -> tuple[dict[str, Any] | None, str | None]:
    url = f"{base_url.rstrip('/')}/wp-json/wp/v2/posts/{post_id}"
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    req_obj = urllib.request.Request(url=url, method="GET", headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(req_obj, timeout=20) as resp:
            code = getattr(resp, "status", resp.getcode())
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return None, f"wordpress GET failed with HTTP {e.code}"
    except urllib.error.URLError:
        return None, "wordpress GET failed with connection error"

    if code != 200:
        return None, f"wordpress GET failed with HTTP {code}"
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None, "wordpress GET returned invalid JSON"
    return payload, None


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def build_wp_verification(post_id: int, returned_status: str, post_link: str, title: str, asin: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AA",
        "document_type": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_RESULT",
        "status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED" if not errors else "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED",
        "post_id": post_id,
        "expected_status": "draft",
        "returned_post_status": returned_status,
        "post_link": post_link,
        "payload_title": title,
        "payload_asin": asin,
        "wordpress_get_executed": True,
        "wordpress_get_post_id": post_id,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        k_cread(): True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": list(errors),
    }


def build_final_preflight(post_id: int, returned_status: str, final_explicit_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AA",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_PASSED_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_FAILED_NO_PUBLISH",
        "post_id": post_id,
        "current_post_status_verified": returned_status == "draft" and not errors,
        "returned_post_status": returned_status,
        "final_explicit_publish_execution_command_label": final_explicit_label,
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
        "wordpress_get_executed": True,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        k_cread(): True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_separate_actual_publish_execution_phase": True,
        "requires_explicit_execute_now_for_actual_publish": True,
        "publish_execution_still_blocked": True,
        "errors": list(errors),
    }


def build_lock(post_id: int, final_explicit_label: str) -> dict[str, Any]:
    return {
        "phase": "LS-6AA",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": "draft",
        "final_explicit_publish_execution_command_label": final_explicit_label,
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
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6AB",
        "requires_separate_actual_publish_execution_phase": True,
        "requires_explicit_execute_now_for_actual_publish": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, post_id: int, returned_status: str, final_explicit_label: str, errors: list[str], draft_verified: bool, wp_get_executed: bool, wp_get_post_id: int) -> dict[str, Any]:
    return {
        "phase": "LS-6AA",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "draft_verified": draft_verified,
        "returned_post_status": returned_status,
        "wordpress_get_executed": wp_get_executed,
        "wordpress_get_post_id": wp_get_post_id if wp_get_executed else 0,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "final_explicit_publish_execution_command_label": final_explicit_label,
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
        "requires_separate_actual_publish_execution_phase": True,
        "requires_explicit_execute_now_for_actual_publish": True,
        "publish_execution_still_blocked": True,
        k_cread(): wp_get_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "next_phase": {
            "phase": "LS-6AB",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_separate_actual_publish_execution_phase": True,
            "requires_explicit_execute_now_for_actual_publish": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()

    if not args.verify_current_draft:
        result = build_run_result(STATUS_NOT_READY_MISSING_VERIFY_FLAG, 183, "", "", ["missing --verify-current-draft"], False, False, 0)
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.record_actual_publish_execution_final_preflight:
        result = build_run_result(STATUS_NOT_READY_MISSING_PREFLIGHT_FLAG, 183, "", "", ["missing --record-actual-publish-execution-final-preflight"], False, False, 0)
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.require_separated_actual_publish_execution_phase:
        result = build_run_result(STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG, 183, "", "", ["missing --require-separated-actual-publish-execution-phase"], False, False, 0)
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.require_explicit_execute_now_for_actual_publish:
        result = build_run_result(STATUS_NOT_READY_MISSING_EXPLICIT_EXECUTE_NOW_FLAG, 183, "", "", ["missing --require-explicit-execute-now-for-actual-publish"], False, False, 0)
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6z_ready = try_load_json(Path(args.ls6z_ready_result), errors)
    ls6z_command = try_load_json(Path(args.ls6z_command_result), errors)
    ls6y_validation = try_load_json(Path(args.ls6y_validation_result), errors)
    ls6y_preflight = try_load_json(Path(args.ls6y_boundary_preflight_result), errors)
    ls6y_lock = try_load_json(Path(args.ls6y_boundary_lock), errors)
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

    req(policy.get("phase") == "LS-6AA", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z ready status mismatch", errors)
    req(ls6z_ready.get("command_status") == "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6Z command_status mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6Z final explicit label mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z final explicit consumed must be false", errors)
    req(ls6z_ready.get("manual_publish_executed") is False, "LS-6Z manual_publish_executed must be false", errors)
    req(ls6z_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6Z actual_publish_execution_gate_consumed must be false", errors)
    req(ls6z_ready.get("actual_publish_runner_boundary_consumed") is False, "LS-6Z actual_publish_runner_boundary_consumed must be false", errors)
    req(ls6z_ready.get("final_execution_command_consumed") is False, "LS-6Z final_execution_command_consumed must be false", errors)
    req(ls6z_ready.get("approval_label_consumed") is False, "LS-6Z approval_label_consumed must be false", errors)
    req(ls6z_ready.get("execute_now_confirmation_consumed") is False, "LS-6Z execute_now_confirmation_consumed must be false", errors)
    req(ls6z_ready.get("actual_publish_execution_allowed_by_this_phase") is False, "LS-6Z actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(ls6z_ready.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6Z actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(ls6z_ready.get("manual_publish_allowed_by_this_phase") is False, "LS-6Z manual_publish_allowed_by_this_phase must be false", errors)
    req(ls6z_ready.get("manual_publish_execution_allowed_by_this_phase") is False, "LS-6Z manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(ls6z_ready.get("requires_actual_publish_execution_final_preflight") is True, "LS-6Z requires_actual_publish_execution_final_preflight must be true", errors)
    req(ls6z_ready.get("publish_execution_still_blocked") is True, "LS-6Z publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6z_ready, "next_phase", "phase") == "LS-6AA", "LS-6Z next_phase mismatch", errors)

    cmd_obj = ls6z_command.get("final_explicit_publish_execution_command", {})
    req(ls6z_command.get("command_status") == "FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6Z command result status mismatch", errors)
    req(cmd_obj.get("final_explicit_publish_execution_command_label") == "FINAL_EXPLICIT_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6Z command label mismatch", errors)
    req(cmd_obj.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y validation status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y boundary consumed must be false", errors)
    req(ls6y_validation.get("manual_publish_executed") is False, "LS-6Y manual_publish_executed must be false", errors)
    req(ls6y_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6Y preflight status mismatch", errors)
    req(ls6y_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_LOCKED_NO_PUBLISH", "LS-6Y lock status mismatch", errors)

    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X actual_publish_execution_gate_consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)

    req(ls6w_validation.get("status") == "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6W validation status mismatch", errors)
    req(ls6w_validation.get("returned_post_status") == "draft", "LS-6W returned_post_status mismatch", errors)
    req(ls6w_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6W preflight status mismatch", errors)
    req(ls6w_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6W lock status mismatch", errors)

    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must be false", errors)
    req(safe_get(ls6v_command, "final_execution_command", "final_execution_command_consumed") is False, "LS-6V command consumed must be false", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    req(ls6t_confirmation.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    req(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    req(post_id == 183, "target post_id mismatch", errors)

    cred_errors: list[str] = []
    env_path = Path(args.credential_env)
    if not env_path.exists():
        cred_errors.append("credential env file missing")
    env = parse_env(env_path) if env_path.exists() else {}
    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        if not env.get(key):
            cred_errors.append(f"missing credential key: {key}")

    returned_status = ""
    wp_payload: dict[str, Any] = {}
    wp_get_executed = False

    final_explicit_label = str(ls6z_ready.get("final_explicit_publish_execution_command_label", ""))

    if not errors and not cred_errors:
        wp_payload, err = verify_current_draft(env["WORDPRESS_BASE_URL"], env["WORDPRESS_USERNAME"], env["WORDPRESS_APP_PASSWORD"], post_id)
        wp_get_executed = True
        if err:
            cred_errors.append(err)
        else:
            if to_int(wp_payload.get("id")) != post_id:
                cred_errors.append("wordpress GET id mismatch")
            returned_status = str(wp_payload.get("status", ""))
            if returned_status != "draft":
                cred_errors.append("wordpress GET status mismatch")

    all_errors = list(errors) + list(cred_errors)

    title = str(target.get("title", ""))
    asin = str(target.get("asin", ""))
    post_link = str(target.get("post_link", ""))

    wp_result = build_wp_verification(post_id, returned_status, post_link, title, asin, cred_errors)
    if not wp_get_executed:
        wp_result["wordpress_get_executed"] = False
        wp_result[k_cread()] = False
        wp_result["status"] = "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED"
    write_json(Path(args.wordpress_current_draft_status_output), wp_result)

    preflight_result = build_final_preflight(post_id, returned_status, final_explicit_label, all_errors)
    if not wp_get_executed:
        preflight_result["wordpress_get_executed"] = False
        preflight_result[k_cread()] = False
    write_json(Path(args.actual_publish_execution_final_preflight_output), preflight_result)

    lock = build_lock(post_id, final_explicit_label)
    write_json(Path(args.actual_publish_execution_final_preflight_lock_output), lock)

    if errors:
        status = STATUS_NOT_READY
    elif cred_errors:
        status = STATUS_FAILED
    else:
        status = STATUS_PASSED

    run_result = build_run_result(status, post_id, returned_status, final_explicit_label, all_errors, status == STATUS_PASSED, wp_get_executed, post_id)
    write_json(Path(args.output), run_result)
    write_report(Path(args.report), run_result)
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
