#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


STATUS_PASSED = "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED"
STATUS_FAILED = "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_FAILED_NO_PUBLISH"
STATUS_FAILED_ALREADY_PUBLISHED = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_FAILED_NO_PUBLISH_OR_ALREADY_PUBLISHED"
)
STATUS_MISSING_EXECUTE_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_EXECUTE_FLAG"
)
STATUS_BAD_POST_CONFIRMATION = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_BAD_POST_CONFIRMATION"
)
STATUS_BAD_STATUS_CONFIRMATION = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_BAD_STATUS_CONFIRMATION"
)
STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_CREDENTIAL_READ_ALLOW_FLAG"
)
STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_WORDPRESS_GET_ALLOW_FLAG"
)
STATUS_MISSING_WORDPRESS_POST_ALLOW_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_WORDPRESS_POST_ALLOW_FLAG"
)
STATUS_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG"
)
STATUS_MISSING_RUNNER_EXECUTION_ALLOW_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_RUNNER_EXECUTION_ALLOW_FLAG"
)
STATUS_MISSING_NO_SECRET_OUTPUT_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_NO_SECRET_OUTPUT_FLAG"
)
STATUS_MISSING_FORBID_POST119_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_FORBID_POST119_FLAG"
)
STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_FORBID_CONTENT_UPDATE_FLAG"
)
STATUS_MISSING_FORBID_NEW_POST_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_FORBID_NEW_POST_FLAG"
)
STATUS_MISSING_FORBID_DELETE_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_FORBID_DELETE_FLAG"
)
STATUS_MISSING_FORBID_SCHEDULE_FLAG = (
    "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_READY_MISSING_FORBID_SCHEDULE_FLAG"
)
LOCKED_STATUS = "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_LOCKED_PUBLISHED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6at_actual_publish_execution_runner_separated_publish_execution_policy.json",
    )
    parser.add_argument(
        "--ls6as-template-result",
        default="exchange/logs/start_ls6as_actual_publish_execution_runner_final_command_template_result.json",
    )
    parser.add_argument(
        "--ls6as-ready-result",
        default="exchange/logs/start_ls6as_actual_publish_execution_runner_final_command_ready_result.json",
    )
    parser.add_argument(
        "--ls6as-final-command-result",
        default="exchange/human_review/start_ls6as_actual_publish_execution_runner_final_command.json",
    )
    parser.add_argument(
        "--ls6ar-credential-preflight-result",
        default="exchange/runtime/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--ls6ar-credential-preflight-lock",
        default="exchange/locks/start_ls6ar_actual_publish_execution_runner_credential_preflight.lock.json",
    )
    parser.add_argument(
        "--ls6ar-validation-result",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_validation_result.json",
    )
    parser.add_argument("--credential-env-path", default="/etc/ai-media-os/credential.env")
    parser.add_argument(
        "--publish-execution-output",
        default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--publish-execution-lock-output",
        default="exchange/locks/start_ls6at_actual_publish_execution_runner_separated_publish_execution.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6at_actual_publish_execution_runner_separated_publish_execution_report.md",
    )

    parser.add_argument("--execute-separated-publish", action="store_true")
    parser.add_argument("--confirm-post-id", type=int, default=0)
    parser.add_argument("--confirm-current-status", default="")
    parser.add_argument("--confirm-target-status", default="")
    parser.add_argument("--allow-credential-env-read", action="store_true")
    parser.add_argument("--allow-wordpress-get", action="store_true")
    parser.add_argument("--allow-wordpress-post", action="store_true")
    parser.add_argument("--allow-actual-publish", action="store_true")
    parser.add_argument("--allow-runner-execution", action="store_true")
    parser.add_argument("--require-no-secret-output", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-content-update", action="store_true")
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
        "# LS-6AT Separated Publish Execution Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- production_status: {payload['production_status']}",
        f"- post_id: {payload['post_id']}",
        f"- pre_publish_returned_post_status: {payload['pre_publish_returned_post_status']}",
        f"- post_publish_returned_post_status: {payload['post_publish_returned_post_status']}",
        f"- publish_executed: {payload['publish_executed']}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def choose_missing_flag_status(args: argparse.Namespace) -> str | None:
    if not args.execute_separated_publish:
        return STATUS_MISSING_EXECUTE_FLAG
    if not args.allow_credential_env_read:
        return STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG
    if not args.allow_wordpress_get:
        return STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG
    if not args.allow_wordpress_post:
        return STATUS_MISSING_WORDPRESS_POST_ALLOW_FLAG
    if not args.allow_actual_publish:
        return STATUS_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG
    if not args.allow_runner_execution:
        return STATUS_MISSING_RUNNER_EXECUTION_ALLOW_FLAG
    if not args.require_no_secret_output:
        return STATUS_MISSING_NO_SECRET_OUTPUT_FLAG
    if not args.forbid_post119_update:
        return STATUS_MISSING_FORBID_POST119_FLAG
    if not args.forbid_content_update:
        return STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG
    if not args.forbid_new_post:
        return STATUS_MISSING_FORBID_NEW_POST_FLAG
    if not args.forbid_delete:
        return STATUS_MISSING_FORBID_DELETE_FLAG
    if not args.forbid_schedule:
        return STATUS_MISSING_FORBID_SCHEDULE_FLAG
    return None


def parse_credential_env(path: Path, accepted_url_keys: list[str], required_keys: list[str]) -> tuple[dict[str, str], dict[str, bool]]:
    values: dict[str, str] = {}
    flags = {
        "credential_env_exists": path.exists(),
        "credential_env_readable": False,
        "credential_env_read_executed": False,
        "credential_required_keys_present": False,
        "credential_required_keys_non_empty": False,
    }
    if not flags["credential_env_exists"]:
        return values, flags

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return values, flags

    flags["credential_env_readable"] = True
    flags["credential_env_read_executed"] = True

    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, value = s.split("=", 1)
        k = key.strip()
        if not k:
            continue
        values[k] = value.strip()

    all_present = True
    all_non_empty = True
    url_present = any(k in values for k in accepted_url_keys)
    url_non_empty = any(values.get(k, "") != "" for k in accepted_url_keys)
    if not url_present:
        all_present = False
    if not url_non_empty:
        all_non_empty = False
    for key in required_keys:
        if key not in values:
            all_present = False
        if values.get(key, "") == "":
            all_non_empty = False

    flags["credential_required_keys_present"] = all_present
    flags["credential_required_keys_non_empty"] = all_non_empty
    return values, flags


def build_next_phase(policy: dict[str, Any]) -> dict[str, Any]:
    p = policy.get("next_phase", {})
    return {
        "phase": str(p.get("phase", "")),
        "requires_post_publish_verification": bool(p.get("requires_post_publish_verification", False)),
        "requires_published_evidence": bool(p.get("requires_published_evidence", False)),
        "requires_rollback_readiness_record": bool(p.get("requires_rollback_readiness_record", False)),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6as_template = try_load_json(Path(args.ls6as_template_result), errors)
    ls6as_ready = try_load_json(Path(args.ls6as_ready_result), errors)
    ls6as_final = try_load_json(Path(args.ls6as_final_command_result), errors)
    ls6ar_preflight = try_load_json(Path(args.ls6ar_credential_preflight_result), errors)
    ls6ar_lock = try_load_json(Path(args.ls6ar_credential_preflight_lock), errors)
    ls6ar_validation = try_load_json(Path(args.ls6ar_validation_result), errors)

    target = policy.get("target_post", {})
    target_post_id = int(target.get("post_id", 0))
    expected_pre_status = str(target.get("expected_pre_publish_status", "draft"))
    target_status = str(target.get("target_status", "publish"))

    missing_flag_status = choose_missing_flag_status(args)
    if args.confirm_post_id != target_post_id:
        missing_flag_status = STATUS_BAD_POST_CONFIRMATION
    if args.confirm_current_status != expected_pre_status or args.confirm_target_status != target_status:
        missing_flag_status = STATUS_BAD_STATUS_CONFIRMATION

    ls6as_req = policy.get("required_previous_phase", {}).get("ls6as", {})
    ls6ar_req = policy.get("required_previous_phase", {}).get("ls6ar", {})

    req(policy.get("phase") == "LS-6AT", "policy.phase mismatch", errors)

    req(ls6as_template.get("status") == ls6as_req.get("required_template_status"), "LS-6AS template status mismatch", errors)
    req(ls6as_ready.get("status") == ls6as_req.get("required_ready_status"), "LS-6AS ready status mismatch", errors)
    req(ls6as_ready.get("command_status") == ls6as_req.get("required_command_status"), "LS-6AS command status mismatch", errors)
    req(
        ls6as_ready.get("actual_publish_execution_runner_final_command_label")
        == ls6as_req.get("required_final_command_label"),
        "final command label mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("actual_publish_execution_runner_final_command_consumed", False))
        is bool(ls6as_req.get("required_final_command_consumed", False)),
        "final command consumed mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("actual_publish_execution_runner_final_command_allows_execution_by_this_phase", False))
        is bool(ls6as_req.get("required_final_command_allows_execution_by_this_phase", False)),
        "final command allows execution mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("actual_publish_execution_runner_final_command_approved_for_later_separated_phase", False))
        is bool(ls6as_req.get("required_final_command_approved_for_later_separated_phase", True)),
        "final command approved_for_later mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("actual_publish_execution_runner_separate_publish_execution_phase_required", False))
        is bool(ls6as_req.get("required_separate_publish_execution_phase", True)),
        "separate publish phase required mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("requires_actual_publish_execution_runner_separated_execution", False))
        is bool(ls6as_req.get("required_actual_publish_execution_runner_separated_execution", True)),
        "requires separated execution mismatch",
        errors,
    )
    req(
        bool(ls6as_ready.get("publish_execution_still_blocked", False))
        is bool(ls6as_req.get("required_publish_execution_still_blocked", True)),
        "publish_execution_still_blocked mismatch",
        errors,
    )

    req(
        ls6as_final.get("command_status") == ls6as_req.get("required_command_status"),
        "LS-6AS final command result mismatch",
        errors,
    )
    final_cmd = ls6as_final.get("final_command", {})
    req(
        final_cmd.get("actual_publish_execution_runner_final_command_label")
        == ls6as_req.get("required_final_command_label"),
        "LS-6AS final command label mismatch",
        errors,
    )

    req(
        ls6ar_validation.get("status") == ls6ar_req.get("required_validation_status"),
        "LS-6AR validation status mismatch",
        errors,
    )
    req(
        bool(ls6ar_preflight.get("actual_publish_execution_runner_credential_preflight_ready", False))
        is bool(ls6ar_req.get("required_credential_preflight_ready", True)),
        "credential preflight ready mismatch",
        errors,
    )
    req(
        bool(ls6ar_preflight.get("actual_publish_execution_runner_credential_preflight_consumed", False))
        is bool(ls6ar_req.get("required_credential_preflight_consumed", False)),
        "credential preflight consumed mismatch",
        errors,
    )
    req(bool(ls6ar_lock.get("locked", False)) is True, "LS-6AR lock mismatch", errors)
    req(bool(ls6ar_preflight.get("ls6aq_final_boundary_validated", False)) is True, "LS-6AQ final boundary not validated", errors)

    cred_policy = policy.get("credential_policy", {})
    accepted_url_keys = list(cred_policy.get("accepted_site_url_keys", []))
    required_keys = list(cred_policy.get("required_key_names", []))

    creds, cred_flags = parse_credential_env(Path(args.credential_env_path), accepted_url_keys, required_keys)
    req(cred_flags["credential_env_exists"], "credential env missing", errors)
    req(cred_flags["credential_env_readable"], "credential env unreadable", errors)
    req(cred_flags["credential_required_keys_present"], "credential env required key missing", errors)
    req(cred_flags["credential_required_keys_non_empty"], "credential env required key empty", errors)

    status = STATUS_FAILED
    pre_post_id = 0
    pre_status = ""
    post_post_id = 0
    post_status = ""

    actual_publish = policy.get("actual_publish_execution_policy", {})

    if missing_flag_status is not None:
        status = missing_flag_status
        errors.append("required execution/confirmation flags missing or invalid")
    elif errors:
        status = STATUS_FAILED
    else:
        try:
            site_url = ""
            for key in accepted_url_keys:
                if creds.get(key, ""):
                    site_url = creds[key]
                    break
            wp_username = creds.get("WORDPRESS_USERNAME", "")
            wp_app_password = creds.get("WORDPRESS_APP_PASSWORD", "")

            post_endpoint = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{target_post_id}"
            auth = HTTPBasicAuth(wp_username, wp_app_password)

            pre_resp = requests.get(post_endpoint, params={"context": "edit"}, auth=auth, timeout=30)
            pre_resp.raise_for_status()
            pre_doc = pre_resp.json()
            pre_post_id = int(pre_doc.get("id", 0))
            pre_status = str(pre_doc.get("status", ""))

            if pre_post_id != target_post_id:
                raise RuntimeError("pre GET returns wrong post id")
            if pre_status == "publish":
                status = STATUS_FAILED_ALREADY_PUBLISHED
                errors.append("pre GET already publish")
            elif pre_status != str(actual_publish.get("requires_pre_publish_status", expected_pre_status)):
                raise RuntimeError("pre GET returns non-draft")

            if status != STATUS_FAILED_ALREADY_PUBLISHED:
                post_payload = {"status": target_status}
                post_resp = requests.post(post_endpoint, json=post_payload, auth=auth, timeout=30)
                post_resp.raise_for_status()
                post_doc = post_resp.json()
                post_post_id = int(post_doc.get("id", 0))
                post_status = str(post_doc.get("status", ""))
                if post_post_id != target_post_id:
                    raise RuntimeError("POST response wrong post id")
                if post_status != target_status:
                    raise RuntimeError("POST response non-publish")

                verify_resp = requests.get(post_endpoint, params={"context": "edit"}, auth=auth, timeout=30)
                verify_resp.raise_for_status()
                verify_doc = verify_resp.json()
                post_post_id = int(verify_doc.get("id", 0))
                post_status = str(verify_doc.get("status", ""))
                if post_post_id != target_post_id:
                    raise RuntimeError("post GET wrong post id")
                if post_status != target_status:
                    raise RuntimeError("post GET non-publish")

                status = STATUS_PASSED
        except Exception as ex:
            if status != STATUS_FAILED_ALREADY_PUBLISHED:
                status = STATUS_FAILED
                errors.append(str(ex))

    success = status == STATUS_PASSED
    next_phase = build_next_phase(policy)

    result = {
        "phase": "LS-6AT",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_RESULT",
        "status": status,
        "execution_mode": "SEPARATED_ACTUAL_PUBLISH_EXECUTION",
        "production_status": "PUBLISHED" if success else "NO_PUBLISH",
        "post_id": target_post_id,
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "pre_publish_returned_post_id": pre_post_id,
        "pre_publish_returned_post_status": pre_status,
        "post_publish_returned_post_id": post_post_id,
        "post_publish_returned_post_status": post_status,
        "returned_post_status": post_status,
        "ls6as_final_command_validated": not errors or success,
        "ls6ar_credential_preflight_validated": (
            ls6ar_validation.get("status") == ls6ar_req.get("required_validation_status")
        ),
        "actual_publish_execution_runner_separated_execution_started": status not in {
            STATUS_MISSING_EXECUTE_FLAG,
            STATUS_BAD_POST_CONFIRMATION,
            STATUS_BAD_STATUS_CONFIRMATION,
            STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG,
            STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG,
            STATUS_MISSING_WORDPRESS_POST_ALLOW_FLAG,
            STATUS_MISSING_ACTUAL_PUBLISH_ALLOW_FLAG,
            STATUS_MISSING_RUNNER_EXECUTION_ALLOW_FLAG,
            STATUS_MISSING_NO_SECRET_OUTPUT_FLAG,
            STATUS_MISSING_FORBID_POST119_FLAG,
            STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG,
            STATUS_MISSING_FORBID_NEW_POST_FLAG,
            STATUS_MISSING_FORBID_DELETE_FLAG,
            STATUS_MISSING_FORBID_SCHEDULE_FLAG,
        },
        "actual_publish_execution_runner_separated_execution_completed": success,
        "actual_publish_execution_runner_final_command_consumed": success,
        "actual_publish_execution_runner_credential_preflight_consumed": success,
        "actual_publish_execution_runner_final_boundary_consumed": success,
        "credential_env_read_executed": bool(cred_flags["credential_env_read_executed"]),
        "credential_env_exists": bool(cred_flags["credential_env_exists"]),
        "credential_env_readable": bool(cred_flags["credential_env_readable"]),
        "credential_required_keys_present": bool(cred_flags["credential_required_keys_present"]),
        "credential_required_keys_non_empty": bool(cred_flags["credential_required_keys_non_empty"]),
        "credential_values_loaded_for_output": False,
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_string_output": False,
        "wordpress_api_call_executed": status in {STATUS_PASSED, STATUS_FAILED, STATUS_FAILED_ALREADY_PUBLISHED},
        "wordpress_get_executed": status in {STATUS_PASSED, STATUS_FAILED, STATUS_FAILED_ALREADY_PUBLISHED},
        "wordpress_post_executed": status in {STATUS_PASSED, STATUS_FAILED},
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": status in {STATUS_PASSED, STATUS_FAILED},
        "wordpress_publish_executed": success,
        "publish_executed": success,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "wordpress_new_post_executed": False,
        "wordpress_content_update_executed": False,
        "wordpress_title_update_executed": False,
        "wordpress_meta_update_executed": False,
        "wordpress_schedule_executed": False,
        "actual_publish_execution_runner_network_call_enabled": args.allow_wordpress_get and args.allow_wordpress_post,
        "actual_publish_execution_runner_credential_read_enabled": args.allow_credential_env_read,
        "actual_publish_execution_runner_publish_enabled": args.allow_actual_publish,
        "actual_publish_execution_runner_execution_enabled": args.allow_runner_execution,
        "actual_publish_execution_runner_executed": success,
        "manual_publish_executed": False,
        "actual_publish_execution_allowed_by_this_phase": bool(
            actual_publish.get("actual_publish_execution_allowed_by_this_phase", True)
        ),
        "actual_runner_execution_allowed_by_this_phase": bool(
            actual_publish.get("actual_runner_execution_allowed_by_this_phase", True)
        ),
        "manual_publish_allowed_by_this_phase": bool(
            actual_publish.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "manual_publish_execution_allowed_by_this_phase": bool(
            actual_publish.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "allowed_post_id_only": True,
        "updated_post_id": target_post_id if success else 0,
        "updated_fields": ["status"] if success else [],
        "updated_status": target_status if success else "",
        "content_update_executed": False,
        "title_update_executed": False,
        "meta_update_executed": False,
        "new_post_created": False,
        "locked": success,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_post_publish_verification": bool(next_phase.get("requires_post_publish_verification", False)),
        "requires_published_evidence": bool(next_phase.get("requires_published_evidence", False)),
        "requires_rollback_readiness_record": bool(next_phase.get("requires_rollback_readiness_record", False)),
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock_payload = {
        "phase": "LS-6AT",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_LOCK",
        "status": LOCKED_STATUS if success else status,
        "locked": success,
        "post_id": target_post_id,
        "target_post_status": target_status,
        "pre_publish_returned_post_status": pre_status,
        "post_publish_returned_post_status": post_status,
        "actual_publish_execution_runner_separated_execution_completed": success,
        "actual_publish_execution_runner_final_command_consumed": success,
        "actual_publish_execution_runner_credential_preflight_consumed": success,
        "actual_publish_execution_runner_final_boundary_consumed": success,
        "wordpress_api_call_executed": result["wordpress_api_call_executed"],
        "wordpress_get_executed": result["wordpress_get_executed"],
        "wordpress_post_executed": result["wordpress_post_executed"],
        "wordpress_write_executed_by_this_phase": result["wordpress_write_executed_by_this_phase"],
        "wordpress_publish_executed": result["wordpress_publish_executed"],
        "publish_executed": result["publish_executed"],
        "post119_update_executed": False,
        "delete_executed": False,
        "future_schedule_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": str(next_phase.get("phase", "")),
        "requires_post_publish_verification": bool(next_phase.get("requires_post_publish_verification", False)),
        "requires_published_evidence": bool(next_phase.get("requires_published_evidence", False)),
        "requires_rollback_readiness_record": bool(next_phase.get("requires_rollback_readiness_record", False)),
    }

    write_json(Path(args.publish_execution_output), result)
    write_json(Path(args.publish_execution_lock_output), lock_payload)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
