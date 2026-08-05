#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


STATUS_PASSED = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED"
STATUS_FAILED = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_FAILED"
STATUS_NOT_READY_PREREQ = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_NOT_READY"
STATUS_MISSING_VERIFY_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_VERIFY_FLAG"
STATUS_BAD_POST_CONFIRMATION = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_BAD_POST_CONFIRMATION"
STATUS_BAD_STATUS_CONFIRMATION = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_BAD_STATUS_CONFIRMATION"
STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_CREDENTIAL_READ_ALLOW_FLAG"
STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_WORDPRESS_GET_ALLOW_FLAG"
STATUS_MISSING_PUBLIC_URL_GET_ALLOW_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_PUBLIC_URL_GET_ALLOW_FLAG"
STATUS_MISSING_NO_WRITE_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_NO_WRITE_FLAG"
STATUS_MISSING_NO_SECRET_OUTPUT_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_NO_SECRET_OUTPUT_FLAG"
STATUS_MISSING_FORBID_POST119_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_POST119_FLAG"
STATUS_MISSING_FORBID_CONTENT_UPDATE_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_CONTENT_UPDATE_FLAG"
STATUS_MISSING_FORBID_NEW_POST_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_NEW_POST_FLAG"
STATUS_MISSING_FORBID_DELETE_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_DELETE_FLAG"
STATUS_MISSING_FORBID_SCHEDULE_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_SCHEDULE_FLAG"
STATUS_MISSING_FORBID_ROLLBACK_FLAG = "LS6AU_POST_PUBLISH_VERIFICATION_NOT_READY_MISSING_FORBID_ROLLBACK_FLAG"
LOCKED_STATUS = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_LOCKED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6au_post_publish_verification_published_evidence_policy.json",
    )
    parser.add_argument(
        "--ls6at-publish-execution-result",
        default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--ls6at-publish-execution-lock",
        default="exchange/locks/start_ls6at_actual_publish_execution_runner_separated_publish_execution.lock.json",
    )
    parser.add_argument(
        "--ls6at-run-result",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--ls6at-validation-result",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json",
    )
    parser.add_argument("--credential-env-path", default="/etc/ai-media-os/credential.env")
    parser.add_argument(
        "--post-publish-verification-output",
        default="exchange/runtime/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--post-publish-verification-lock-output",
        default="exchange/locks/start_ls6au_post_publish_verification_published_evidence.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6au_post_publish_verification_published_evidence_report.md",
    )

    parser.add_argument("--verify-post-publish", action="store_true")
    parser.add_argument("--confirm-post-id", type=int, default=0)
    parser.add_argument("--confirm-expected-status", default="")
    parser.add_argument("--allow-credential-env-read", action="store_true")
    parser.add_argument("--allow-wordpress-get", action="store_true")
    parser.add_argument("--allow-public-url-get", action="store_true")
    parser.add_argument("--require-no-wordpress-write", action="store_true")
    parser.add_argument("--require-no-secret-output", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-content-update", action="store_true")
    parser.add_argument("--forbid-new-post", action="store_true")
    parser.add_argument("--forbid-delete", action="store_true")
    parser.add_argument("--forbid-schedule", action="store_true")
    parser.add_argument("--forbid-rollback-execution", action="store_true")
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
        "# LS-6AU Post Publish Verification Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- production_status: {payload['production_status']}",
        f"- post_id: {payload['post_id']}",
        f"- rest_returned_post_status: {payload['rest_returned_post_status']}",
        f"- public_url_reachable: {payload['public_url_reachable']}",
        f"- completion_status: {payload['completion_status']}",
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
    if not args.verify_post_publish:
        return STATUS_MISSING_VERIFY_FLAG
    if not args.allow_credential_env_read:
        return STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG
    if not args.allow_wordpress_get:
        return STATUS_MISSING_WORDPRESS_GET_ALLOW_FLAG
    if not args.allow_public_url_get:
        return STATUS_MISSING_PUBLIC_URL_GET_ALLOW_FLAG
    if not args.require_no_wordpress_write:
        return STATUS_MISSING_NO_WRITE_FLAG
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
    if not args.forbid_rollback_execution:
        return STATUS_MISSING_FORBID_ROLLBACK_FLAG
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

    all_present = any(values.get(k, "") != "" for k in accepted_url_keys)
    all_non_empty = all_present
    for key in required_keys:
        if key not in values:
            all_present = False
        if values.get(key, "") == "":
            all_non_empty = False

    flags["credential_required_keys_present"] = all_present
    flags["credential_required_keys_non_empty"] = all_non_empty
    return values, flags


def build_next_phase() -> dict[str, Any]:
    return {
        "phase": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED",
        "recommended_next_action": "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM",
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6at_result = try_load_json(Path(args.ls6at_publish_execution_result), errors)
    ls6at_lock = try_load_json(Path(args.ls6at_publish_execution_lock), errors)
    ls6at_run = try_load_json(Path(args.ls6at_run_result), errors)
    ls6at_validation = try_load_json(Path(args.ls6at_validation_result), errors)

    target = policy.get("target_post", {})
    target_post_id = int(target.get("post_id", 0))
    expected_status = str(target.get("expected_status", "publish"))
    post_link = str(target.get("post_link", ""))

    missing_flag_status = choose_missing_flag_status(args)
    if args.confirm_post_id != target_post_id:
        missing_flag_status = STATUS_BAD_POST_CONFIRMATION
    if args.confirm_expected_status != expected_status:
        missing_flag_status = STATUS_BAD_STATUS_CONFIRMATION

    req(policy.get("phase") == "LS-6AU", "policy.phase mismatch", errors)

    req_prev = policy.get("required_previous_phase", {}).get("ls6at", {})
    req(ls6at_result.get("status") == req_prev.get("required_run_status"), "LS-6AT run status mismatch", errors)
    req(ls6at_validation.get("status") == req_prev.get("required_validation_status"), "LS-6AT validation status mismatch", errors)
    req(ls6at_result == ls6at_run, "LS-6AT run result mismatch", errors)
    req(ls6at_result.get("production_status") == req_prev.get("required_production_status"), "LS-6AT production_status mismatch", errors)
    req(int(ls6at_result.get("post_id", 0)) == req_prev.get("required_post_id"), "LS-6AT post_id mismatch", errors)
    req(str(ls6at_result.get("post_publish_returned_post_status", "")) == req_prev.get("required_post_publish_status"), "LS-6AT post_publish status mismatch", errors)
    req(int(ls6at_result.get("updated_post_id", 0)) == req_prev.get("required_updated_post_id"), "LS-6AT updated_post_id mismatch", errors)
    req(list(ls6at_result.get("updated_fields", [])) == list(req_prev.get("required_updated_fields", [])), "LS-6AT updated_fields mismatch", errors)
    req(str(ls6at_result.get("updated_status", "")) == req_prev.get("required_updated_status"), "LS-6AT updated_status mismatch", errors)

    req(bool(ls6at_result.get("post119_update_executed", False)) is False, "LS-6AT post119_update_executed must be false", errors)
    req(bool(ls6at_result.get("content_update_executed", False)) is False, "LS-6AT content_update_executed must be false", errors)
    req(bool(ls6at_result.get("title_update_executed", False)) is False, "LS-6AT title_update_executed must be false", errors)
    req(bool(ls6at_result.get("meta_update_executed", False)) is False, "LS-6AT meta_update_executed must be false", errors)
    req(bool(ls6at_result.get("new_post_created", False)) is False, "LS-6AT new_post_created must be false", errors)
    req(bool(ls6at_result.get("delete_executed", False)) is False, "LS-6AT delete_executed must be false", errors)
    req(bool(ls6at_result.get("future_schedule_executed", False)) is False, "LS-6AT future_schedule_executed must be false", errors)
    req(bool(ls6at_result.get("credential_value_output", False)) is False, "LS-6AT credential_value_output must be false", errors)
    req(bool(ls6at_lock.get("locked", False)) is True, "LS-6AT lock mismatch", errors)

    cred_policy = policy.get("credential_policy", {})
    accepted_url_keys = list(cred_policy.get("accepted_site_url_keys", []))
    required_keys = list(cred_policy.get("required_key_names", []))
    creds, cred_flags = parse_credential_env(Path(args.credential_env_path), accepted_url_keys, required_keys)

    req(cred_flags["credential_env_exists"], "credential env missing", errors)
    req(cred_flags["credential_env_readable"], "credential env unreadable", errors)
    req(cred_flags["credential_required_keys_present"], "credential env required key missing", errors)
    req(cred_flags["credential_required_keys_non_empty"], "credential env required key empty", errors)

    rest_id = 0
    rest_status = ""
    public_url_reachable = False

    if missing_flag_status is not None:
        errors.append("required verification flags missing or invalid")
        status = missing_flag_status
    elif errors:
        status = STATUS_NOT_READY_PREREQ
    else:
        try:
            site_url = ""
            for key in accepted_url_keys:
                if creds.get(key, ""):
                    site_url = creds[key]
                    break
            auth = HTTPBasicAuth(creds.get("WORDPRESS_USERNAME", ""), creds.get("WORDPRESS_APP_PASSWORD", ""))
            endpoint = f"{site_url.rstrip('/')}/wp-json/wp/v2/posts/{target_post_id}"

            rest_resp = requests.get(endpoint, params={"context": "edit"}, auth=auth, timeout=30)
            rest_resp.raise_for_status()
            rest_doc = rest_resp.json()
            rest_id = int(rest_doc.get("id", 0))
            rest_status = str(rest_doc.get("status", ""))
            if rest_id != target_post_id:
                raise RuntimeError("REST GET returns wrong post id")
            if rest_status != expected_status:
                raise RuntimeError("REST GET returns non-publish")

            pub_resp = requests.get(post_link, timeout=30)
            if pub_resp.status_code == 404:
                raise RuntimeError("public URL returns 404")
            pub_resp.raise_for_status()
            public_url_reachable = True

            status = STATUS_PASSED
        except Exception as ex:
            status = STATUS_FAILED
            errors.append(str(ex))

    success = status == STATUS_PASSED
    next_phase = build_next_phase()

    result = {
        "phase": "LS-6AU",
        "document_type": "POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_RESULT",
        "status": status,
        "execution_mode": "POST_PUBLISH_VERIFICATION_ONLY_NO_WRITE",
        "production_status": "PUBLISHED_VERIFIED" if success else "PUBLISHED_VERIFICATION_FAILED",
        "post_id": target_post_id,
        "post_link": post_link,
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "ls6at_publish_execution_validated": ls6at_validation.get("status") == req_prev.get("required_validation_status"),
        "ls6at_production_status": str(ls6at_result.get("production_status", "")),
        "ls6at_pre_publish_returned_post_status": str(ls6at_result.get("pre_publish_returned_post_status", "")),
        "ls6at_post_publish_returned_post_status": str(ls6at_result.get("post_publish_returned_post_status", "")),
        "ls6at_returned_post_status": str(ls6at_result.get("returned_post_status", "")),
        "ls6at_updated_post_id": int(ls6at_result.get("updated_post_id", 0)),
        "ls6at_updated_fields": list(ls6at_result.get("updated_fields", [])),
        "ls6at_updated_status": str(ls6at_result.get("updated_status", "")),
        "rest_verification_executed": status in {STATUS_PASSED, STATUS_FAILED},
        "rest_returned_post_id": rest_id,
        "rest_returned_post_status": rest_status,
        "public_url_verification_executed": status in {STATUS_PASSED, STATUS_FAILED},
        "public_url_reachable": public_url_reachable,
        "post_publish_verified": success,
        "published_evidence_recorded": success,
        "rollback_readiness_recorded": success,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "wordpress_api_call_executed": status in {STATUS_PASSED, STATUS_FAILED},
        "wordpress_get_executed": status in {STATUS_PASSED, STATUS_FAILED},
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_publish_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "wordpress_new_post_executed": False,
        "wordpress_content_update_executed": False,
        "wordpress_title_update_executed": False,
        "wordpress_meta_update_executed": False,
        "wordpress_schedule_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
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
        "manual_publish_executed": False,
        "allowed_post_id_only": True,
        "write_scope_verified_as_status_only_from_ls6at": True,
        "no_write_executed_by_this_phase": True,
        "start_ls_one_shot_publish_chain_closed": success,
        "completion_status": "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED" if success else "START_LS_ONE_SHOT_PUBLISH_CHAIN_NOT_CLOSED",
        "locked": success,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "next_phase": next_phase,
        "recommended_next_action": next_phase["recommended_next_action"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock_payload = {
        "phase": "LS-6AU",
        "document_type": "POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_LOCK",
        "status": LOCKED_STATUS if success else status,
        "locked": success,
        "post_id": target_post_id,
        "target_post_status": expected_status,
        "post_publish_verified": success,
        "published_evidence_recorded": success,
        "rollback_readiness_recorded": success,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
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
        "completion_status": result["completion_status"],
        "recommended_next_action": next_phase["recommended_next_action"],
    }

    write_json(Path(args.post_publish_verification_output), result)
    write_json(Path(args.post_publish_verification_lock_output), lock_payload)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
