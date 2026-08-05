#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


STATUS_PASSED = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_PASSED_GET_ONLY"
STATUS_FAILED = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_FAILED_GET_ONLY"
STATUS_LOCKED = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_LOCKED_GET_ONLY"

STATUS_MISSING_RECORD_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_RECORD_FLAG"
STATUS_BAD_POST_CONFIRMATION = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_BAD_POST_CONFIRMATION"
STATUS_BAD_STATUS_CONFIRMATION = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_BAD_STATUS_CONFIRMATION"
STATUS_MISSING_PUBLIC_URL_GET_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_PUBLIC_URL_GET_FLAG"
STATUS_MISSING_PUBLIC_REST_GET_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_PUBLIC_REST_GET_FLAG"
STATUS_MISSING_NO_CREDENTIAL_READ_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_NO_CREDENTIAL_READ_FLAG"
STATUS_MISSING_NO_WRITE_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_NO_WRITE_FLAG"
STATUS_MISSING_NO_PUBLISH_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_NO_PUBLISH_FLAG"
STATUS_MISSING_NO_ROLLBACK_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_NO_ROLLBACK_FLAG"
STATUS_MISSING_FORBID_POST119_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_FORBID_POST119_FLAG"
STATUS_MISSING_FORBID_POST183_UPDATE_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_FORBID_POST183_UPDATE_FLAG"
STATUS_MISSING_FORBID_NEW_POST_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_FORBID_NEW_POST_FLAG"
STATUS_MISSING_FORBID_DELETE_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_FORBID_DELETE_FLAG"
STATUS_MISSING_FORBID_SCHEDULE_FLAG = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_READY_MISSING_FORBID_SCHEDULE_FLAG"

PUBLIC_REST_UNAVAILABLE_WARNING = "PUBLIC_REST_UNAVAILABLE_BUT_PUBLIC_URL_REACHABLE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls_mon1_post183_published_state_monitor_policy.json",
    )
    parser.add_argument(
        "--ls-close1-result",
        default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--ls-close1-lock",
        default="exchange/locks/start_ls_close1_one_shot_publish_chain_closure.lock.json",
    )
    parser.add_argument(
        "--ls-close1-run-result",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--ls-close1-validation-result",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_validation_result.json",
    )
    parser.add_argument(
        "--ls6au-result",
        default="exchange/runtime/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--ls6au-lock",
        default="exchange/locks/start_ls6au_post_publish_verification_published_evidence.lock.json",
    )
    parser.add_argument(
        "--ls6au-validation-result",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_validation_result.json",
    )
    parser.add_argument(
        "--monitor-output",
        default="exchange/runtime/start_ls_mon1_post183_published_state_monitor_result.json",
    )
    parser.add_argument(
        "--monitor-lock-output",
        default="exchange/locks/start_ls_mon1_post183_published_state_monitor.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls_mon1_post183_published_state_monitor_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls_mon1_post183_published_state_monitor_report.md",
    )

    parser.add_argument("--record-monitor-checkpoint", action="store_true")
    parser.add_argument("--confirm-post-id", type=int, default=0)
    parser.add_argument("--confirm-expected-status", default="")
    parser.add_argument("--allow-public-url-get", action="store_true")
    parser.add_argument("--allow-public-rest-get", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-wordpress-write", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-rollback", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-post183-update", action="store_true")
    parser.add_argument("--forbid-new-post", action="store_true")
    parser.add_argument("--forbid-delete", action="store_true")
    parser.add_argument("--forbid-schedule", action="store_true")
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


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-MON-1 Post-183 Published State Monitor Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- production_status: {payload['production_status']}",
        f"- post_id: {payload['post_id']}",
        f"- post_link: {payload['post_link']}",
        f"- monitor_checkpoint: {payload['monitor_checkpoint']}",
        f"- public_url_http_status: {payload['public_url_http_status']}",
        f"- public_rest_http_status: {payload['public_rest_http_status']}",
        f"- public_rest_warning: {payload['public_rest_warning']}",
        f"- recommended_next_action: {payload['recommended_next_action']}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {item}" for item in payload["errors"])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    if payload.get("public_rest_warning"):
        lines.append(f"- {payload['public_rest_warning']}")
    else:
        lines.append("- none")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def choose_missing_flag_status(args: argparse.Namespace) -> str | None:
    if not args.record_monitor_checkpoint:
        return STATUS_MISSING_RECORD_FLAG
    if not args.allow_public_url_get:
        return STATUS_MISSING_PUBLIC_URL_GET_FLAG
    if not args.allow_public_rest_get:
        return STATUS_MISSING_PUBLIC_REST_GET_FLAG
    if not args.require_no_credential_read:
        return STATUS_MISSING_NO_CREDENTIAL_READ_FLAG
    if not args.require_no_wordpress_write:
        return STATUS_MISSING_NO_WRITE_FLAG
    if not args.require_no_publish:
        return STATUS_MISSING_NO_PUBLISH_FLAG
    if not args.require_no_rollback:
        return STATUS_MISSING_NO_ROLLBACK_FLAG
    if not args.forbid_post119_update:
        return STATUS_MISSING_FORBID_POST119_FLAG
    if not args.forbid_post183_update:
        return STATUS_MISSING_FORBID_POST183_UPDATE_FLAG
    if not args.forbid_new_post:
        return STATUS_MISSING_FORBID_NEW_POST_FLAG
    if not args.forbid_delete:
        return STATUS_MISSING_FORBID_DELETE_FLAG
    if not args.forbid_schedule:
        return STATUS_MISSING_FORBID_SCHEDULE_FLAG
    return None


def http_get_status(url: str, timeout: float = 20.0) -> int:
    req_obj = request.Request(url=url, method="GET")
    with request.urlopen(req_obj, timeout=timeout) as resp:  # nosec: B310
        return int(getattr(resp, "status", 0) or 0)


def http_get_json(url: str, timeout: float = 20.0) -> tuple[int, dict[str, Any]]:
    req_obj = request.Request(url=url, method="GET")
    with request.urlopen(req_obj, timeout=timeout) as resp:  # nosec: B310
        status = int(getattr(resp, "status", 0) or 0)
        body = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("public REST payload is not an object")
    return status, payload


def is_reachable_status(code: int) -> bool:
    return 200 <= code < 400


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls_close1_result = try_load_json(Path(args.ls_close1_result), errors)
    ls_close1_lock = try_load_json(Path(args.ls_close1_lock), errors)
    ls_close1_run = try_load_json(Path(args.ls_close1_run_result), errors)
    ls_close1_validation = try_load_json(Path(args.ls_close1_validation_result), errors)
    ls6au_result = try_load_json(Path(args.ls6au_result), errors)
    ls6au_lock = try_load_json(Path(args.ls6au_lock), errors)
    ls6au_validation = try_load_json(Path(args.ls6au_validation_result), errors)

    target = policy.get("target_post", {})
    req_close1 = policy.get("required_previous_phase", {}).get("ls_close1", {})
    req_ls6au = policy.get("required_previous_phase", {}).get("ls6au", {})
    monitor_policy = policy.get("monitor_policy", {})

    missing_flag_status = choose_missing_flag_status(args)
    if args.confirm_post_id != int(target.get("post_id", 0)):
        missing_flag_status = STATUS_BAD_POST_CONFIRMATION
    if args.confirm_expected_status != str(target.get("expected_status", "")):
        missing_flag_status = STATUS_BAD_STATUS_CONFIRMATION

    req(policy.get("phase") == "LS-MON-1", "policy.phase mismatch", errors)

    req(
        ls_close1_result.get("status") == req_close1.get("required_run_status"),
        "LS-CLOSE-1 run status mismatch",
        errors,
    )
    req(
        ls_close1_validation.get("status") == req_close1.get("required_validation_status"),
        "LS-CLOSE-1 validation status mismatch",
        errors,
    )
    req(
        ls_close1_result.get("production_status") == req_close1.get("required_production_status"),
        "LS-CLOSE-1 production_status mismatch",
        errors,
    )
    req(
        ls_close1_result.get("completion_status") == req_close1.get("required_completion_status"),
        "LS-CLOSE-1 completion_status mismatch",
        errors,
    )
    req(
        int(ls_close1_result.get("post_id", 0)) == int(req_close1.get("required_post_id", 0)),
        "LS-CLOSE-1 post_id mismatch",
        errors,
    )
    req(ls_close1_result == ls_close1_run, "LS-CLOSE-1 result mismatch", errors)
    req(bool(ls_close1_lock.get("locked", False)) is True, "LS-CLOSE-1 lock mismatch", errors)
    req(bool(ls_close1_result.get("wordpress_api_call_executed", False)) is False, "LS-CLOSE-1 wordpress_api_call_executed must be false", errors)
    req(bool(ls_close1_result.get("credential_env_read_executed", False)) is False, "LS-CLOSE-1 credential_env_read_executed must be false", errors)
    req(bool(ls_close1_result.get("publish_executed_by_this_phase", False)) is False, "LS-CLOSE-1 publish_executed_by_this_phase must be false", errors)
    req(bool(ls_close1_result.get("rollback_executed", False)) is False, "LS-CLOSE-1 rollback_executed must be false", errors)

    req(
        ls6au_result.get("status") == req_ls6au.get("required_run_status"),
        "LS-6AU run status mismatch",
        errors,
    )
    req(
        ls6au_validation.get("status") == req_ls6au.get("required_validation_status"),
        "LS-6AU validation status mismatch",
        errors,
    )
    req(bool(ls6au_lock.get("locked", False)) is True, "LS-6AU lock mismatch", errors)
    req(
        ls6au_result.get("production_status") == req_ls6au.get("required_production_status"),
        "LS-6AU production_status mismatch",
        errors,
    )
    req(
        int(ls6au_result.get("post_id", 0)) == int(req_ls6au.get("required_post_id", 0)),
        "LS-6AU post_id mismatch",
        errors,
    )
    req(
        str(ls6au_result.get("rest_returned_post_status", "")) == req_ls6au.get("required_rest_returned_post_status"),
        "LS-6AU rest status mismatch",
        errors,
    )
    req(
        bool(ls6au_result.get("public_url_reachable", False)) is bool(req_ls6au.get("required_public_url_reachable", True)),
        "LS-6AU public_url_reachable mismatch",
        errors,
    )
    req(
        bool(ls6au_result.get("post_publish_verified", False)) is bool(req_ls6au.get("required_post_publish_verified", True)),
        "LS-6AU post_publish_verified mismatch",
        errors,
    )
    req(
        bool(ls6au_result.get("published_evidence_recorded", False)) is bool(req_ls6au.get("required_published_evidence_recorded", True)),
        "LS-6AU published_evidence_recorded mismatch",
        errors,
    )
    req(
        bool(ls6au_result.get("rollback_readiness_recorded", False)) is bool(req_ls6au.get("required_rollback_readiness_recorded", True)),
        "LS-6AU rollback_readiness_recorded mismatch",
        errors,
    )
    req(bool(ls6au_result.get("wordpress_post_executed", False)) is False, "LS-6AU wordpress_post_executed must be false", errors)
    req(bool(ls6au_result.get("wordpress_write_executed_by_this_phase", False)) is False, "LS-6AU wordpress_write_executed_by_this_phase must be false", errors)
    req(bool(ls6au_result.get("publish_executed_by_this_phase", False)) is False, "LS-6AU publish_executed_by_this_phase must be false", errors)

    public_url_http_status: int | None = None
    public_url_reachable = False
    public_url_reachable_status_ok = False

    public_rest_get_executed = bool(args.allow_public_rest_get)
    public_rest_http_status: int | None = None
    public_rest_reachable = False
    public_rest_returned_post_id: int | None = None
    public_rest_returned_post_status: str | None = None
    public_rest_status_verified = False
    public_rest_warning: str | None = None

    should_run_monitor_gets = missing_flag_status is None and not errors
    if should_run_monitor_gets:
        try:
            public_url_http_status = http_get_status(str(target.get("post_link", "")))
            public_url_reachable_status_ok = is_reachable_status(public_url_http_status)
            public_url_reachable = public_url_reachable_status_ok
        except (error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"public URL GET failed: {exc}")

        if not public_url_reachable_status_ok:
            errors.append("public URL not reachable with expected status")

        try:
            public_rest_http_status, rest_payload = http_get_json(str(target.get("public_rest_url", "")))
            public_rest_reachable = is_reachable_status(public_rest_http_status)
            if public_rest_reachable:
                public_rest_returned_post_id = int(rest_payload.get("id", 0))
                public_rest_returned_post_status = str(rest_payload.get("status", ""))
                if public_rest_returned_post_id != int(target.get("post_id", 0)):
                    errors.append("public REST returned post_id mismatch")
                if public_rest_returned_post_status != str(target.get("expected_status", "")):
                    errors.append("public REST returned post_status mismatch")
                public_rest_status_verified = (
                    public_rest_returned_post_id == int(target.get("post_id", 0))
                    and public_rest_returned_post_status == str(target.get("expected_status", ""))
                )
            else:
                if public_url_reachable:
                    public_rest_warning = PUBLIC_REST_UNAVAILABLE_WARNING
                else:
                    errors.append("public REST not reachable")
        except (error.URLError, error.HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            if public_url_reachable:
                public_rest_warning = PUBLIC_REST_UNAVAILABLE_WARNING
            else:
                errors.append("public REST GET failed")

    status = STATUS_PASSED if not errors and missing_flag_status is None else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status

    payload = {
        "phase": "LS-MON-1",
        "document_type": "POST_183_PUBLISHED_STATE_MONITOR_RESULT",
        "status": status,
        "execution_mode": "GET_ONLY_MONITOR_NO_CREDENTIAL_NO_WRITE",
        "production_status": "PUBLISHED_STATE_MONITORED" if status == STATUS_PASSED else "PUBLISHED_STATE_MONITORING",
        "post_id": int(target.get("post_id", 0)),
        "post_link": str(target.get("post_link", "")),
        "public_rest_url": str(target.get("public_rest_url", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "ls_close1_validated": ls_close1_validation.get("status") == req_close1.get("required_validation_status"),
        "ls_close1_completion_status": str(ls_close1_result.get("completion_status", "")),
        "ls6au_validated": ls6au_validation.get("status") == req_ls6au.get("required_validation_status"),
        "ls6au_production_status": str(ls6au_result.get("production_status", "")),
        "ls6au_rest_returned_post_status": str(ls6au_result.get("rest_returned_post_status", "")),
        "ls6au_public_url_reachable": bool(ls6au_result.get("public_url_reachable", False)),
        "monitor_checkpoint_recorded": bool(args.record_monitor_checkpoint),
        "monitor_scope": str(monitor_policy.get("monitor_scope", "POST_183_ONLY")),
        "monitor_window": str(monitor_policy.get("monitor_window", "FIRST_24H_AFTER_PUBLISH")),
        "monitor_checkpoint": str(monitor_policy.get("monitor_checkpoint", "LS_MON_1_INITIAL_CHECKPOINT")),
        "public_url_get_executed": bool(args.allow_public_url_get),
        "public_url_http_status": public_url_http_status,
        "public_url_reachable": public_url_reachable,
        "public_url_reachable_status_ok": public_url_reachable_status_ok,
        "public_rest_get_executed": public_rest_get_executed,
        "public_rest_http_status": public_rest_http_status,
        "public_rest_reachable": public_rest_reachable,
        "public_rest_returned_post_id": public_rest_returned_post_id,
        "public_rest_returned_post_status": public_rest_returned_post_status,
        "public_rest_status_verified": public_rest_status_verified,
        "public_rest_warning": public_rest_warning,
        "published_state_preserved": public_url_reachable,
        "post_publish_state_monitor_ok": public_url_reachable and (public_rest_status_verified or public_rest_warning == PUBLIC_REST_UNAVAILABLE_WARNING),
        "wordpress_authenticated_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_values_loaded_for_output": False,
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_publish_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "wordpress_new_post_executed": False,
        "new_post_created": False,
        "wordpress_content_update_executed": False,
        "content_update_executed": False,
        "wordpress_title_update_executed": False,
        "title_update_executed": False,
        "wordpress_meta_update_executed": False,
        "meta_update_executed": False,
        "wordpress_schedule_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "locked": status == STATUS_PASSED,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "recommended_next_action": str(
            monitor_policy.get(
                "recommended_next_action",
                "CONTINUE_24H_GET_ONLY_MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
            )
        ),
        "recommended_next_phase_options": list(
            monitor_policy.get("recommended_next_phase_options", ["LS-MON-2", "LS-NEXT-1", "LS-REUSE-1"])
        ),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    for key, expected in policy.get("must_remain_false_flags", {}).items():
        observed = bool(payload.get(key, False))
        req(observed is bool(expected), f"{key} mismatch", errors)

    status = STATUS_PASSED if not errors and missing_flag_status is None else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status
    payload["status"] = status
    payload["locked"] = status == STATUS_PASSED
    payload["production_status"] = "PUBLISHED_STATE_MONITORED" if status == STATUS_PASSED else "PUBLISHED_STATE_MONITORING"
    payload["errors"] = list(errors)

    lock_payload = {
        "phase": "LS-MON-1",
        "document_type": "POST_183_PUBLISHED_STATE_MONITOR_LOCK",
        "status": STATUS_LOCKED if status == STATUS_PASSED else status,
        "locked": status == STATUS_PASSED,
        "post_id": int(target.get("post_id", 0)),
        "target_post_status": str(target.get("expected_status", "publish")),
        "monitor_checkpoint_recorded": bool(args.record_monitor_checkpoint),
        "monitor_scope": str(monitor_policy.get("monitor_scope", "POST_183_ONLY")),
        "monitor_window": str(monitor_policy.get("monitor_window", "FIRST_24H_AFTER_PUBLISH")),
        "monitor_checkpoint": str(monitor_policy.get("monitor_checkpoint", "LS_MON_1_INITIAL_CHECKPOINT")),
        "public_url_get_executed": bool(args.allow_public_url_get),
        "public_url_reachable": public_url_reachable,
        "public_rest_get_executed": public_rest_get_executed,
        "published_state_preserved": payload["published_state_preserved"],
        "post_publish_state_monitor_ok": payload["post_publish_state_monitor_ok"],
        "wordpress_authenticated_api_call_executed": False,
        "credential_env_read_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "delete_executed": False,
        "future_schedule_executed": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "recommended_next_action": payload["recommended_next_action"],
        "recommended_next_phase_options": payload["recommended_next_phase_options"],
    }

    write_json(Path(args.monitor_output), payload)
    write_json(Path(args.monitor_lock_output), lock_payload)
    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
