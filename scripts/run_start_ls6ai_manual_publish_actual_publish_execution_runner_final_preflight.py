#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


STATUS_PASSED = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
STATUS_NOT_READY_MISSING_VERIFY_FLAG = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"
STATUS_NOT_READY_MISSING_EXECUTE_NOW_FLAG = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_EXECUTE_NOW_FLAG"
STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG = "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_policy.json")
    parser.add_argument("--ls6ah-run-result", default="exchange/logs/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary_result.json")
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
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--wordpress-current-draft-status-output", default="exchange/runtime/start_ls6ai_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--actual-publish-execution-runner-final-preflight-output", default="exchange/runtime/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_result.json")
    parser.add_argument("--actual-publish-execution-runner-final-preflight-lock-output", default="exchange/locks/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_result.json")
    parser.add_argument("--report", default="reports/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_report.md")
    parser.add_argument("--verify-current-draft", action="store_true")
    parser.add_argument("--record-actual-publish-execution-runner-final-preflight", action="store_true")
    parser.add_argument("--require-actual-publish-execution-runner-execute-now", action="store_true")
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
        "# LS-6AI Manual Publish Actual Publish Execution Runner Final Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- wordpress_get_executed: {result['wordpress_get_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- actual_publish_execution_runner_final_preflight_ready: {result['actual_publish_execution_runner_final_preflight_ready']}",
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


def get_ls6ac_consumed(doc: dict[str, Any]) -> Any:
    return doc.get(
        "actual_publish_execute_now_final_confirmation_consumed",
        safe_get(doc, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed"),
    )


def get_ls6ac_explicit_consumed(doc: dict[str, Any]) -> Any:
    return doc.get(
        "explicit_execute_now_for_actual_publish_consumed",
        safe_get(doc, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_consumed"),
    )


def get_ls6t_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("execute_now_confirmation_consumed", safe_get(doc, "confirmation", "execute_now_confirmation_consumed"))


def get_ls6r_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("approval_label_consumed", safe_get(doc, "approval", "approval_label_consumed"))


def get_ls6z_consumed(doc: dict[str, Any]) -> Any:
    return doc.get(
        "final_explicit_publish_execution_command_consumed",
        safe_get(doc, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed"),
    )


def get_ls6x_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("actual_publish_execution_gate_consumed", safe_get(doc, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed"))


def get_ls6v_consumed(doc: dict[str, Any]) -> Any:
    return doc.get("final_execution_command_consumed", safe_get(doc, "final_execution_command", "final_execution_command_consumed"))


def read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def fetch_wordpress_post(base_url: str, username: str, app_password: str, post_id: int) -> tuple[int, dict[str, Any]]:
    endpoint = base_url.rstrip("/") + f"/wp-json/wp/v2/posts/{post_id}"
    token = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
    req_obj = request.Request(endpoint, headers={"Authorization": f"Basic {token}"}, method="GET")
    try:
        with request.urlopen(req_obj, timeout=20) as resp:
            code = int(getattr(resp, "status", 200))
            body = resp.read().decode("utf-8")
            return code, json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return int(exc.code), parsed


def build_wordpress_result(status: str, returned_status: str, get_executed: bool, cred_read: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AI",
        "document_type": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_RESULT",
        "status": status,
        "post_id": 183,
        "expected_status": "draft",
        "returned_post_status": returned_status,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "wordpress_get_executed": get_executed,
        "wordpress_get_post_id": 183,
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
        "credential_env_read_executed": cred_read,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": list(errors),
    }


def build_final_preflight_result(status: str, returned_status: str, draft_verified: bool, get_executed: bool, cred_read: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AI",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_PUBLISH" if status == STATUS_PASSED else "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_FAILED_NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "current_post_status_verified": draft_verified,
        "returned_post_status": returned_status,
        "actual_publish_execution_runner_final_preflight_ready": draft_verified,
        "actual_publish_execution_runner_final_preflight_consumed": False,
        "actual_publish_execution_runner_boundary_ready": True,
        "actual_publish_execution_runner_boundary_consumed": False,
        "actual_publish_final_execution_command_recorded": True,
        "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
        "actual_publish_final_execution_command_consumed": False,
        "actual_publish_runner_final_gate_ready": True,
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
        "wordpress_get_executed": get_executed,
        "wordpress_get_post_id": 183,
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
        "credential_env_read_executed": cred_read,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_actual_publish_execution_runner_execute_now": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "errors": list(errors),
    }


def build_lock() -> dict[str, Any]:
    return {
        "phase": "LS-6AI",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": 183,
        "target_post_status": "draft",
        "actual_publish_execution_runner_final_preflight_ready": True,
        "actual_publish_execution_runner_final_preflight_consumed": False,
        "actual_publish_execution_runner_boundary_ready": True,
        "actual_publish_execution_runner_boundary_consumed": False,
        "actual_publish_final_execution_command_consumed": False,
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
        "requires_next_phase": "LS-6AJ",
        "requires_actual_publish_execution_runner_execute_now": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, returned_status: str, draft_verified: bool, get_executed: bool, cred_read: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AI",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": 183,
        "post_link": "https://hoshido.jp/?p=183",
        "payload_title": "2.5次元の誘惑",
        "payload_asin": "B07X2G67B4",
        "draft_verified": draft_verified,
        "returned_post_status": returned_status,
        "wordpress_get_executed": get_executed,
        "wordpress_get_post_id": 183,
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
        "actual_publish_execution_runner_final_preflight_ready": draft_verified,
        "actual_publish_execution_runner_final_preflight_consumed": False,
        "actual_publish_execution_runner_boundary_ready": True,
        "actual_publish_execution_runner_boundary_consumed": False,
        "actual_publish_final_execution_command_recorded": True,
        "actual_publish_final_execution_command_label": "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY",
        "actual_publish_final_execution_command_consumed": False,
        "actual_publish_runner_final_gate_ready": True,
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
        "credential_env_read_executed": cred_read,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "locked": draft_verified,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_execute_now": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AJ",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_execute_now": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_not_ready(output: Path, report: Path, status: str, message: str) -> int:
    result = build_run_result(status, "", False, False, False, [message])
    write_json(output, result)
    write_report(report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def validate_upstream(policy: dict[str, Any], docs: dict[str, dict[str, Any]], errors: list[str]) -> None:
    req(policy.get("phase") == "LS-6AI", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    ls6ah_run = docs["ls6ah_run"]
    ls6ah_validation = docs["ls6ah_validation"]
    ls6ah_boundary = docs["ls6ah_boundary"]
    ls6ah_lock = docs["ls6ah_lock"]

    req(ls6ah_run.get("status") == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_PASSED_NO_PUBLISH", "LS-6AH run status mismatch", errors)
    req(ls6ah_validation.get("status") == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AH validation status mismatch", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_ready") is True, "LS-6AH boundary ready must be true", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH boundary consumed must be false", errors)
    req(ls6ah_lock.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH lock boundary consumed must be false", errors)
    req(ls6ah_run.get("post_id") == 183, "LS-6AH post_id mismatch", errors)
    req(ls6ah_run.get("returned_post_status") == "draft", "LS-6AH returned_post_status mismatch", errors)
    req(ls6ah_run.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH run boundary consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_final_execution_command_consumed") is False, "LS-6AH run final execution command consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AH run runner final gate consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_final_preflight_consumed") is False, "LS-6AH run final preflight consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_execution_boundary_consumed") is False, "LS-6AH run execution boundary consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AH run execute-now final confirmation consumed must be false", errors)
    req(ls6ah_run.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AH run explicit execute-now consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_execution_runner_executed") is False, "LS-6AH run execution runner executed must be false", errors)
    req(ls6ah_run.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AH run execution final preflight consumed must be false", errors)
    req(ls6ah_run.get("final_explicit_publish_execution_command_consumed") is False, "LS-6AH run final explicit command consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_runner_boundary_consumed") is False, "LS-6AH run runner boundary consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_execution_gate_consumed") is False, "LS-6AH run execution gate consumed must be false", errors)
    req(ls6ah_run.get("final_execution_command_consumed") is False, "LS-6AH run final execution command consumed must be false", errors)
    req(ls6ah_run.get("approval_label_consumed") is False, "LS-6AH run approval consumed must be false", errors)
    req(ls6ah_run.get("execute_now_confirmation_consumed") is False, "LS-6AH run execute now confirmation consumed must be false", errors)
    req(ls6ah_run.get("actual_publish_execution_allowed_by_this_phase") is False, "LS-6AH run actual publish execution allowed must be false", errors)
    req(ls6ah_run.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6AH run actual runner execution allowed must be false", errors)
    req(ls6ah_run.get("manual_publish_allowed_by_this_phase") is False, "LS-6AH run manual publish allowed must be false", errors)
    req(ls6ah_run.get("manual_publish_execution_allowed_by_this_phase") is False, "LS-6AH run manual publish execution allowed must be false", errors)
    req(ls6ah_run.get("manual_publish_executed") is False, "LS-6AH run manual publish executed must be false", errors)
    req(ls6ah_run.get("publish_execution_still_blocked") is True, "LS-6AH run publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6ah_run, "next_phase", "phase") == "LS-6AI", "LS-6AH next_phase mismatch", errors)

    ls6ag_ready = docs["ls6ag_ready"]
    ls6ag_command = docs["ls6ag_command"]
    req(ls6ag_ready.get("status") == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6AG ready status mismatch", errors)
    req(ls6ag_ready.get("command_status") == "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AG command_status mismatch", errors)
    req(ls6ag_ready.get("actual_publish_final_execution_command_label") == "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "LS-6AG command label mismatch", errors)
    req(ls6ag_ready.get("actual_publish_final_execution_command_consumed") is False, "LS-6AG command consumed must be false", errors)
    req(ls6ag_command.get("command_status") == "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AG command result status mismatch", errors)
    req(safe_get(ls6ag_command, "actual_publish_final_execution_command", "actual_publish_final_execution_command_consumed") is False, "LS-6AG command result consumed must be false", errors)

    ls6af_validation = docs["ls6af_validation"]
    ls6af_result = docs["ls6af_result"]
    ls6af_lock = docs["ls6af_lock"]
    req(ls6af_validation.get("status") == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH", "LS-6AF validation status mismatch", errors)
    req(ls6af_result.get("actual_publish_runner_final_gate_ready") is True, "LS-6AF runner final gate ready must be true", errors)
    req(ls6af_result.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF runner final gate consumed must be false", errors)
    req(ls6af_lock.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF lock runner final gate consumed must be false", errors)

    ls6ae_validation = docs["ls6ae_validation"]
    ls6ae_wp = docs["ls6ae_wp"]
    ls6ae_result = docs["ls6ae_result"]
    ls6ae_lock = docs["ls6ae_lock"]
    req(ls6ae_validation.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AE validation status mismatch", errors)
    req(ls6ae_validation.get("draft_verified") is True, "LS-6AE draft_verified must be true", errors)
    req(ls6ae_validation.get("returned_post_status") == "draft", "LS-6AE returned_post_status mismatch", errors)
    req(ls6ae_wp.get("returned_post_status") == "draft", "LS-6AE wordpress returned_post_status mismatch", errors)
    req(ls6ae_result.get("actual_publish_final_preflight_ready") is True, "LS-6AE final preflight ready must be true", errors)
    req(ls6ae_result.get("actual_publish_final_preflight_consumed") is False, "LS-6AE final preflight consumed must be false", errors)
    req(ls6ae_lock.get("actual_publish_final_preflight_consumed") is False, "LS-6AE lock final preflight consumed must be false", errors)

    ls6ad_validation = docs["ls6ad_validation"]
    ls6ad_result = docs["ls6ad_result"]
    ls6ad_lock = docs["ls6ad_lock"]
    req(ls6ad_validation.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AD validation status mismatch", errors)
    req(ls6ad_result.get("actual_publish_execution_boundary_ready") is True, "LS-6AD boundary ready must be true", errors)
    req(ls6ad_result.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD boundary consumed must be false", errors)
    req(ls6ad_lock.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD lock boundary consumed must be false", errors)

    ls6ac_ready = docs["ls6ac_ready"]
    ls6ac_confirmation = docs["ls6ac_confirmation"]
    req(ls6ac_ready.get("status") == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "LS-6AC status mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "LS-6AC label mismatch", errors)
    req(get_ls6ac_consumed(ls6ac_ready) is False, "LS-6AC consumed must be false", errors)
    req(get_ls6ac_explicit_consumed(ls6ac_ready) is False, "LS-6AC explicit consumed must be false", errors)
    req(get_ls6ac_consumed(ls6ac_confirmation) is False, "LS-6AC confirmation consumed must be false", errors)

    ls6ab_validation = docs["ls6ab_validation"]
    ls6ab_result = docs["ls6ab_result"]
    ls6ab_lock = docs["ls6ab_lock"]
    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_result.get("actual_publish_execution_runner_ready") is True, "LS-6AB runner ready must be true", errors)
    req(ls6ab_result.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner executed must be false", errors)
    req(ls6ab_result.get("actual_publish_execution_runner_blocked") is True, "LS-6AB runner blocked must be true", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must be false", errors)

    ls6aa_validation = docs["ls6aa_validation"]
    ls6aa_result = docs["ls6aa_result"]
    ls6aa_lock = docs["ls6aa_lock"]
    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_result.get("actual_publish_execution_final_preflight_ready") is True, "LS-6AA preflight ready must be true", errors)
    req(ls6aa_result.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock preflight consumed must be false", errors)

    ls6z_ready = docs["ls6z_ready"]
    ls6z_command = docs["ls6z_command"]
    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z status mismatch", errors)
    req(get_ls6z_consumed(ls6z_ready) is False, "LS-6Z consumed must be false", errors)
    req(get_ls6z_consumed(ls6z_command) is False, "LS-6Z command consumed must be false", errors)

    ls6y_validation = docs["ls6y_validation"]
    ls6y_lock = docs["ls6y_lock"]
    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    ls6x_ready = docs["ls6x_ready"]
    ls6x_gate = docs["ls6x_gate"]
    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X status mismatch", errors)
    req(get_ls6x_consumed(ls6x_ready) is False, "LS-6X consumed must be false", errors)
    req(get_ls6x_consumed(ls6x_gate) is False, "LS-6X gate consumed must be false", errors)

    ls6v_ready = docs["ls6v_ready"]
    ls6v_command = docs["ls6v_command"]
    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V status mismatch", errors)
    req(get_ls6v_consumed(ls6v_ready) is False, "LS-6V consumed must be false", errors)
    req(get_ls6v_consumed(ls6v_command) is False, "LS-6V command consumed must be false", errors)

    ls6t_ready = docs["ls6t_ready"]
    ls6t_confirmation = docs["ls6t_confirmation"]
    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T status mismatch", errors)
    req(get_ls6t_consumed(ls6t_ready) is False, "LS-6T consumed must be false", errors)
    req(get_ls6t_consumed(ls6t_confirmation) is False, "LS-6T confirmation consumed must be false", errors)

    ls6r_ready = docs["ls6r_ready"]
    ls6r_approval = docs["ls6r_approval"]
    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R status mismatch", errors)
    req(get_ls6r_consumed(ls6r_ready) is False, "LS-6R consumed must be false", errors)
    req(get_ls6r_consumed(ls6r_approval) is False, "LS-6R approval consumed must be false", errors)

    ls6p_lock = docs["ls6p_lock"]
    ls6oc1_lock = docs["ls6oc1_lock"]
    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6OC1 rerun_allowed must be false", errors)


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    report_path = Path(args.report)

    if not args.verify_current_draft:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_VERIFY_FLAG, "missing --verify-current-draft")
    if not args.record_actual_publish_execution_runner_final_preflight:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_RECORD_FLAG, "missing --record-actual-publish-execution-runner-final-preflight")
    if not args.require_actual_publish_execution_runner_execute_now:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_EXECUTE_NOW_FLAG, "missing --require-actual-publish-execution-runner-execute-now")
    if not args.require_separate_publish_execution_phase:
        return write_not_ready(output_path, report_path, STATUS_NOT_READY_MISSING_SEPARATE_EXECUTION_PHASE_FLAG, "missing --require-separate-publish-execution-phase")

    errors: list[str] = []
    policy = try_load_json(Path(args.policy), errors)

    docs = {
        "ls6ah_run": try_load_json(Path(args.ls6ah_run_result), errors),
        "ls6ah_validation": try_load_json(Path(args.ls6ah_validation_result), errors),
        "ls6ah_boundary": try_load_json(Path(args.ls6ah_boundary_result), errors),
        "ls6ah_lock": try_load_json(Path(args.ls6ah_boundary_lock), errors),
        "ls6ag_ready": try_load_json(Path(args.ls6ag_ready_result), errors),
        "ls6ag_command": try_load_json(Path(args.ls6ag_command_result), errors),
        "ls6af_validation": try_load_json(Path(args.ls6af_validation_result), errors),
        "ls6af_result": try_load_json(Path(args.ls6af_runner_final_gate_result), errors),
        "ls6af_lock": try_load_json(Path(args.ls6af_runner_final_gate_lock), errors),
        "ls6ae_validation": try_load_json(Path(args.ls6ae_validation_result), errors),
        "ls6ae_wp": try_load_json(Path(args.ls6ae_wordpress_current_draft_status_result), errors),
        "ls6ae_result": try_load_json(Path(args.ls6ae_final_preflight_result), errors),
        "ls6ae_lock": try_load_json(Path(args.ls6ae_final_preflight_lock), errors),
        "ls6ad_validation": try_load_json(Path(args.ls6ad_validation_result), errors),
        "ls6ad_result": try_load_json(Path(args.ls6ad_boundary_result), errors),
        "ls6ad_lock": try_load_json(Path(args.ls6ad_boundary_lock), errors),
        "ls6ac_ready": try_load_json(Path(args.ls6ac_ready_result), errors),
        "ls6ac_confirmation": try_load_json(Path(args.ls6ac_confirmation_result), errors),
        "ls6ab_validation": try_load_json(Path(args.ls6ab_validation_result), errors),
        "ls6ab_result": try_load_json(Path(args.ls6ab_blocked_runner_result), errors),
        "ls6ab_lock": try_load_json(Path(args.ls6ab_blocked_runner_lock), errors),
        "ls6aa_validation": try_load_json(Path(args.ls6aa_validation_result), errors),
        "ls6aa_result": try_load_json(Path(args.ls6aa_final_preflight_result), errors),
        "ls6aa_lock": try_load_json(Path(args.ls6aa_final_preflight_lock), errors),
        "ls6z_ready": try_load_json(Path(args.ls6z_ready_result), errors),
        "ls6z_command": try_load_json(Path(args.ls6z_command_result), errors),
        "ls6y_validation": try_load_json(Path(args.ls6y_validation_result), errors),
        "ls6y_lock": try_load_json(Path(args.ls6y_boundary_lock), errors),
        "ls6x_ready": try_load_json(Path(args.ls6x_ready_result), errors),
        "ls6x_gate": try_load_json(Path(args.ls6x_gate_result), errors),
        "ls6v_ready": try_load_json(Path(args.ls6v_ready_result), errors),
        "ls6v_command": try_load_json(Path(args.ls6v_command_result), errors),
        "ls6t_ready": try_load_json(Path(args.ls6t_ready_result), errors),
        "ls6t_confirmation": try_load_json(Path(args.ls6t_confirmation_result), errors),
        "ls6r_ready": try_load_json(Path(args.ls6r_ready_result), errors),
        "ls6r_approval": try_load_json(Path(args.ls6r_approval_result), errors),
        "ls6p_lock": try_load_json(Path(args.ls6p_rerun_prevention_lock), errors),
        "ls6oc1_lock": try_load_json(Path(args.ls6oc1_consumption_lock), errors),
    }

    validate_upstream(policy, docs, errors)

    returned_post_status = str(docs["ls6ah_run"].get("returned_post_status", ""))
    if errors:
        result = build_run_result(STATUS_NOT_READY, returned_post_status, False, False, False, errors)
        write_json(output_path, result)
        write_report(report_path, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    get_executed = False
    cred_read = False
    draft_verified = False
    run_errors: list[str] = []

    credential_env_path = Path(args.credential_env)
    env_map: dict[str, str] = {}
    if not credential_env_path.exists():
        run_errors.append(f"credential env missing: {credential_env_path}")
    else:
        env_map = read_env_file(credential_env_path)
        cred_read = True

    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        if not env_map.get(key):
            run_errors.append(f"missing credential key: {key}")

    wp_status = "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED"
    returned_status = ""

    if not run_errors:
        code, payload = fetch_wordpress_post(
            env_map["WORDPRESS_BASE_URL"],
            env_map["WORDPRESS_USERNAME"],
            env_map["WORDPRESS_APP_PASSWORD"],
            183,
        )
        get_executed = True
        if code != 200:
            run_errors.append(f"wordpress get non-200: {code}")
        post_id = payload.get("id")
        returned_status = str(payload.get("status", ""))
        if post_id != 183:
            run_errors.append(f"wordpress id mismatch: {post_id}")
        if returned_status != "draft":
            run_errors.append(f"wordpress status mismatch: {returned_status}")

    if not returned_status:
        returned_status = returned_post_status

    if not run_errors and get_executed and returned_status == "draft":
        draft_verified = True
        wp_status = "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED"

    final_status = STATUS_PASSED if draft_verified else STATUS_FAILED

    wordpress_result = build_wordpress_result(wp_status, returned_status, get_executed, cred_read, run_errors)
    final_preflight_result = build_final_preflight_result(final_status, returned_status, draft_verified, get_executed, cred_read, run_errors)
    run_result = build_run_result(final_status, returned_status, draft_verified, get_executed, cred_read, run_errors)

    write_json(Path(args.wordpress_current_draft_status_output), wordpress_result)
    write_json(Path(args.actual_publish_execution_runner_final_preflight_output), final_preflight_result)
    if draft_verified:
        write_json(Path(args.actual_publish_execution_runner_final_preflight_lock_output), build_lock())
    write_json(output_path, run_result)
    write_report(report_path, run_result)
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
