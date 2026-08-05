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


STATUS_PASSED = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH"
STATUS_NOT_READY = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY"
STATUS_NOT_READY_MISSING_VERIFY_FLAG = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_NOT_READY_MISSING_PREFLIGHT_FLAG = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_PREFLIGHT_FLAG"
STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG = "LS6W_MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6w_manual_publish_actual_execution_final_runner_preflight_policy.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6v-command-result", default="exchange/human_review/start_ls6v_manual_publish_final_execution_command.json")
    parser.add_argument("--ls6u-validation-result", default="exchange/logs/start_ls6u_manual_publish_actual_execution_runner_boundary_validation_result.json")
    parser.add_argument("--ls6u-runner-boundary-preflight-result", default="exchange/runtime/start_ls6u_manual_publish_actual_execution_runner_boundary_preflight_result.json")
    parser.add_argument("--ls6u-runner-boundary-lock", default="exchange/locks/start_ls6u_manual_publish_actual_execution_runner_boundary.lock.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6t-confirmation-result", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--wordpress-current-draft-status-output", default="exchange/runtime/start_ls6w_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--final-runner-preflight-output", default="exchange/runtime/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--final-runner-preflight-lock-output", default="exchange/locks/start_ls6w_manual_publish_actual_execution_final_runner_preflight.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6w_manual_publish_actual_execution_final_runner_preflight_result.json")
    parser.add_argument("--report", default="reports/start_ls6w_manual_publish_actual_execution_final_runner_preflight_report.md")
    parser.add_argument("--verify-current-draft", action="store_true")
    parser.add_argument("--record-final-runner-preflight", action="store_true")
    parser.add_argument("--require-separated-publish-execution", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6W Manual Publish Actual Execution Final Runner Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result.get('post_id')}",
        f"- draft_verified: {result.get('draft_verified')}",
        f"- returned_post_status: {result.get('returned_post_status')}",
        f"- wordpress_get_executed: {result.get('wordpress_get_executed')}",
        f"- final_execution_command_label: {result.get('final_execution_command_label')}",
        f"- requires_separate_publish_execution: {result.get('requires_separate_publish_execution')}",
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
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, val = line.split("=", 1)
        data[k.strip()] = val.strip()
    return data


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


def build_wordpress_verification(*, payload_title: str, payload_asin: str, post_link: str, post_id: int, returned_status: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6W",
        "document_type": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_RESULT",
        "status": "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED" if not errors else "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFICATION_FAILED",
        "post_id": post_id,
        "expected_status": "draft",
        "returned_post_status": returned_status,
        "post_link": post_link,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
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
        "credential_env_read_executed": True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": errors,
    }


def build_final_preflight(*, post_id: int, returned_status: str, final_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6W",
        "document_type": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_RESULT",
        "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_PASSED_NO_PUBLISH" if not errors else "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_FAILED_NO_PUBLISH",
        "post_id": post_id,
        "current_post_status_verified": returned_status == "draft" and not errors,
        "returned_post_status": returned_status,
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
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
        "credential_env_read_executed": True,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "requires_separate_publish_execution": True,
        "publish_execution_still_blocked": True,
        "errors": errors,
    }


def build_lock(post_id: int, final_label: str) -> dict[str, Any]:
    return {
        "phase": "LS-6W",
        "document_type": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCK",
        "status": "MANUAL_PUBLISH_ACTUAL_EXECUTION_FINAL_RUNNER_PREFLIGHT_LOCKED_NO_PUBLISH",
        "locked": True,
        "post_id": post_id,
        "target_post_status": "draft",
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6X",
        "requires_separate_publish_execution": True,
        "publish_execution_still_blocked": True,
    }


def build_run_result(status: str, post_id: int, returned_status: str, final_label: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6W",
        "status": status,
        "execution_mode": "FINAL_RUNNER_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "draft_verified": returned_status == "draft" and status == STATUS_PASSED,
        "returned_post_status": returned_status,
        "wordpress_get_executed": True if status != STATUS_NOT_READY else False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "final_execution_command_label": final_label,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "manual_publish_executed": False,
        "requires_separate_publish_execution": True,
        "publish_execution_still_blocked": True,
        "credential_env_read_executed": True if status != STATUS_NOT_READY else False,
        "credential_value_output": False,
        "authorization_header_output": False,
        "next_phase": {
            "phase": "LS-6X",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_separate_publish_execution": True,
            "publish_execution_still_blocked": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    ls6v_ready = load_json(Path(args.ls6v_ready_result))
    ls6v_command = load_json(Path(args.ls6v_command_result))
    ls6u_validation = load_json(Path(args.ls6u_validation_result))
    ls6u_preflight = load_json(Path(args.ls6u_runner_boundary_preflight_result))
    ls6u_lock = load_json(Path(args.ls6u_runner_boundary_lock))
    ls6t_ready = load_json(Path(args.ls6t_ready_result))
    ls6t_confirm = load_json(Path(args.ls6t_confirmation_result))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    if not args.verify_current_draft:
        result = build_run_result(STATUS_NOT_READY_MISSING_VERIFY_FLAG, 183, "", "", ["missing --verify-current-draft"])
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.record_final_runner_preflight:
        result = build_run_result(STATUS_NOT_READY_MISSING_PREFLIGHT_FLAG, 183, "", "", ["missing --record-final-runner-preflight"])
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.require_separated_publish_execution:
        result = build_run_result(STATUS_NOT_READY_MISSING_SEPARATED_EXECUTION_FLAG, 183, "", "", ["missing --require-separated-publish-execution"])
        write_json(Path(args.output), result)
        write_report(Path(args.report), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    errors: list[str] = []

    req(policy.get("phase") == "LS-6W", "policy phase mismatch", errors)
    req(policy.get("execution_mode") == "FINAL_RUNNER_PREFLIGHT_ONLY_NO_PUBLISH", "policy execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy production_status mismatch", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("command_status") == "FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6V command_status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_label") == "FINAL_COMMAND_FOR_MANUAL_PUBLISH_EXECUTION_GATE_ONLY", "LS-6V final label mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V final_execution_command_consumed must be false", errors)
    req(ls6v_ready.get("manual_publish_executed") is False, "LS-6V manual_publish_executed must be false", errors)
    req(ls6v_ready.get("publish_execution_still_blocked") is True, "LS-6V publish_execution_still_blocked must be true", errors)

    req(ls6u_validation.get("status") == "LS6U_MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6U validation status mismatch", errors)
    req(ls6u_preflight.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6U preflight status mismatch", errors)
    req(ls6u_lock.get("status") == "MANUAL_PUBLISH_ACTUAL_EXECUTION_RUNNER_BOUNDARY_LOCKED_NO_PUBLISH", "LS-6U lock status mismatch", errors)
    req(ls6u_validation.get("actual_runner_execution_allowed_by_this_phase") is False, "LS-6U actual runner allowed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T execute_now_confirmation_consumed must be false", errors)
    req(ls6t_confirm.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "LS-6T confirmation status mismatch", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    req(ls6r_approval.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "LS-6R approval status mismatch", errors)

    req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)

    target = policy.get("target_post", {})
    post_id = to_int(target.get("post_id"))
    req(post_id == 183, "target post_id mismatch", errors)
    req(ls6v_ready.get("post_id") == 183, "LS-6V post_id mismatch", errors)
    req(ls6v_ready.get("returned_post_status") == "draft", "LS-6V returned_post_status mismatch", errors)

    env_path = Path(args.credential_env)
    if not env_path.exists():
        errors.append("credential env file missing")

    env = parse_env(env_path) if env_path.exists() else {}
    for key in ["WORDPRESS_BASE_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"]:
        if not env.get(key):
            errors.append(f"missing credential key: {key}")

    payload: dict[str, Any] = {}
    returned_status = ""

    if not errors:
        payload, err = verify_current_draft(env["WORDPRESS_BASE_URL"], env["WORDPRESS_USERNAME"], env["WORDPRESS_APP_PASSWORD"], post_id)
        if err:
            errors.append(err)
        else:
            if to_int(payload.get("id")) != post_id:
                errors.append("wordpress GET id mismatch")
            returned_status = str(payload.get("status", ""))
            if returned_status != "draft":
                errors.append("wordpress GET status mismatch")

    final_label = str(safe_get(ls6v_command, "final_execution_command", "final_execution_command_label") or "")
    if not final_label:
        final_label = str(ls6v_ready.get("final_execution_command_label", ""))

    wp_errors = [] if not errors else list(errors)
    wp_result = build_wordpress_verification(
        payload_title=str(target.get("title", "")),
        payload_asin=str(target.get("asin", "")),
        post_link=str(target.get("post_link", "")),
        post_id=post_id,
        returned_status=returned_status,
        errors=wp_errors,
    )
    write_json(Path(args.wordpress_current_draft_status_output), wp_result)

    preflight = build_final_preflight(post_id=post_id, returned_status=returned_status, final_label=final_label, errors=list(errors))
    write_json(Path(args.final_runner_preflight_output), preflight)

    lock = build_lock(post_id, final_label)
    write_json(Path(args.final_runner_preflight_lock_output), lock)

    if not errors:
        status = STATUS_PASSED
    elif any(e.startswith("missing credential key:") or e.startswith("wordpress GET") for e in errors):
        status = STATUS_FAILED
    else:
        status = STATUS_NOT_READY
    result = build_run_result(status, post_id, returned_status, final_label, list(errors))
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
