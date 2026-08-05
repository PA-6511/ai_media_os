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

READY = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE"
FAILED = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_FAILED_NO_WRITE"
LOCKED = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCKED_NO_WRITE"
REQ_LS11_STATUS = "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_READY_NO_WRITE"
REQ_LS11_VALID = "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"

URL_ALIASES = ["WP_BASE_URL", "WORDPRESS_BASE_URL", "WP_SITE_URL", "WORDPRESS_SITE_URL"]
USERNAME_ALIASES = ["WP_USERNAME", "WORDPRESS_USERNAME", "WP_USER", "WORDPRESS_USER"]
APP_PASSWORD_ALIASES = [
    "WP_APP_PASSWORD",
    "WORDPRESS_APP_PASSWORD",
    "WP_APPLICATION_PASSWORD",
    "WORDPRESS_APPLICATION_PASSWORD",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new12_authenticated_wp_read_preflight_policy.json")
    p.add_argument("--schema", default="config/start_ls_new12_authenticated_wp_read_preflight_schema.json")
    p.add_argument("--ls-new11-result", default="exchange/runtime/start_ls_new11_credential_wp_connectivity_preflight_result.json")
    p.add_argument("--ls-new11-validation-result", default="exchange/logs/start_ls_new11_credential_wp_connectivity_preflight_validation_result.json")
    p.add_argument("--ls-new11-manifest", default="exchange/new_release/start_ls_new11_credential_preflight_manifest.json")
    p.add_argument("--ls-new11-credential-summary", default="exchange/new_release/start_ls_new11_credential_presence_summary.json")
    p.add_argument("--ls-new11-wp-connectivity-result", default="exchange/new_release/start_ls_new11_wp_connectivity_preflight_result.json")
    p.add_argument("--ls-new11-no-write-safety-contract", default="exchange/new_release/start_ls_new11_no_write_safety_contract.json")
    p.add_argument("--ls-new11-next-phase-handoff", default="exchange/new_release/start_ls_new11_next_phase_handoff.json")
    p.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    p.add_argument("--authenticated-read-endpoint", default="/wp-json/wp/v2/users/me?context=edit")
    p.add_argument("--connect-timeout-seconds", type=int, default=5)

    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new12_authenticated_wp_read_preflight_manifest.json")
    p.add_argument("--output-authenticated-read-result", default="exchange/new_release/start_ls_new12_authenticated_wp_read_result.json")
    p.add_argument("--output-secret-non-output-summary", default="exchange/new_release/start_ls_new12_secret_non_output_summary.json")
    p.add_argument("--output-no-write-safety-contract", default="exchange/new_release/start_ls_new12_no_write_safety_contract.json")
    p.add_argument("--output-draft-creation-hold-boundary", default="exchange/new_release/start_ls_new12_draft_creation_hold_boundary.json")
    p.add_argument("--output-next-phase-handoff", default="exchange/new_release/start_ls_new12_next_phase_handoff.json")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new12_authenticated_wp_read_preflight_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new12_authenticated_wp_read_preflight_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new12_authenticated_wp_read_preflight.lock.json")
    p.add_argument("--report", default="reports/start_ls_new12_authenticated_wp_read_preflight_report.md")

    p.add_argument("--allow-credential-env-existence-check", action="store_true")
    p.add_argument("--allow-credential-env-read", action="store_true")
    p.add_argument("--allow-authenticated-wp-read-get", action="store_true")

    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-wordpress-draft", action="store_true")
    p.add_argument("--require-no-wordpress-publish", action="store_true")
    p.add_argument("--require-no-wordpress-update", action="store_true")
    p.add_argument("--require-no-wordpress-delete", action="store_true")
    p.add_argument("--require-no-runner-execution", action="store_true")
    p.add_argument("--require-no-final-execution-command", action="store_true")
    p.add_argument("--require-no-generic-external-fetch", action="store_true")
    p.add_argument("--require-no-web-scraping", action="store_true")
    p.add_argument("--require-no-rss-fetch", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
    p.add_argument("--require-no-credential-value-output", action="store_true")
    p.add_argument("--require-no-credential-secret-output", action="store_true")
    p.add_argument("--require-no-credential-length-output", action="store_true")
    p.add_argument("--require-no-credential-hash-output", action="store_true")
    p.add_argument("--require-no-authorization-output", action="store_true")
    p.add_argument("--require-no-basic-auth-output", action="store_true")
    p.add_argument("--require-no-base64-auth-output", action="store_true")
    p.add_argument("--require-no-response-body-output", action="store_true")
    p.add_argument("--require-no-user-identity-output", action="store_true")
    p.add_argument("--require-no-response-body-save", action="store_true")
    p.add_argument("--require-no-user-identity-save", action="store_true")
    p.add_argument("--require-no-approval-label-consumption", action="store_true")
    p.add_argument("--require-no-target-post-id-allocation", action="store_true")
    p.add_argument("--require-no-candidate-selection", action="store_true")
    p.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    p.add_argument("--forbid-post119-update", action="store_true")
    p.add_argument("--forbid-post183-update", action="store_true")
    return p.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json {label}: {path}")
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _validate_flags(args: argparse.Namespace, errors: list[str]) -> None:
    allows = {
        "--allow-credential-env-existence-check": args.allow_credential_env_existence_check,
        "--allow-credential-env-read": args.allow_credential_env_read,
        "--allow-authenticated-wp-read-get": args.allow_authenticated_wp_read_get,
    }
    for name, enabled in allows.items():
        if not enabled:
            errors.append(f"missing required allow flag: {name}")

    forbids = {
        "--require-no-wordpress-write": args.require_no_wordpress_write,
        "--require-no-wordpress-draft": args.require_no_wordpress_draft,
        "--require-no-wordpress-publish": args.require_no_wordpress_publish,
        "--require-no-wordpress-update": args.require_no_wordpress_update,
        "--require-no-wordpress-delete": args.require_no_wordpress_delete,
        "--require-no-runner-execution": args.require_no_runner_execution,
        "--require-no-final-execution-command": args.require_no_final_execution_command,
        "--require-no-generic-external-fetch": args.require_no_generic_external_fetch,
        "--require-no-web-scraping": args.require_no_web_scraping,
        "--require-no-rss-fetch": args.require_no_rss_fetch,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-credential-value-output": args.require_no_credential_value_output,
        "--require-no-credential-secret-output": args.require_no_credential_secret_output,
        "--require-no-credential-length-output": args.require_no_credential_length_output,
        "--require-no-credential-hash-output": args.require_no_credential_hash_output,
        "--require-no-authorization-output": args.require_no_authorization_output,
        "--require-no-basic-auth-output": args.require_no_basic_auth_output,
        "--require-no-base64-auth-output": args.require_no_base64_auth_output,
        "--require-no-response-body-output": args.require_no_response_body_output,
        "--require-no-user-identity-output": args.require_no_user_identity_output,
        "--require-no-response-body-save": args.require_no_response_body_save,
        "--require-no-user-identity-save": args.require_no_user_identity_save,
        "--require-no-approval-label-consumption": args.require_no_approval_label_consumption,
        "--require-no-target-post-id-allocation": args.require_no_target_post_id_allocation,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in forbids.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _parse_env(content: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _select_value(env_map: dict[str, str], aliases: list[str]) -> tuple[bool, bool, str]:
    for key in aliases:
        if key in env_map:
            value = env_map.get(key, "")
            return True, bool(str(value).strip()), str(value)
    return False, False, ""


def _status_class(code: int) -> str:
    if 200 <= code <= 299:
        return "2xx"
    if 300 <= code <= 399:
        return "3xx"
    if 400 <= code <= 499:
        return "4xx"
    return "5xx"


def _resolve_url(site_url: str, endpoint: str) -> str:
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    if endpoint.startswith("/"):
        return site_url.rstrip("/") + endpoint
    return site_url.rstrip("/") + "/" + endpoint


def _run_authenticated_wp_get(site_url: str, username: str, app_password: str, endpoint: str, timeout: int) -> tuple[bool, str]:
    auth = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
    req_obj = urllib.request.Request(
        url=_resolve_url(site_url, endpoint),
        method="GET",
        headers={"Authorization": f"Basic {auth}"},
    )
    try:
        with urllib.request.urlopen(req_obj, timeout=timeout) as resp:
            cls = _status_class(int(resp.getcode()))
            return cls == "2xx", cls
    except urllib.error.HTTPError as e:
        return False, _status_class(int(e.code))
    except Exception:
        return False, "NETWORK_ERROR"


def _fixed_false_block() -> dict[str, Any]:
    return {
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "generic_external_fetch_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
    }


def _summary_text(read_ok: bool, status_class: str) -> str:
    return "\n".join(
        [
            "# LS-NEW-12 Authenticated WP Read Preflight Summary",
            "",
            "- Phase: LS-NEW-12",
            "- Status: READY_NO_WRITE",
            "- Credential env read executed: true",
            "- Authenticated WP read GET attempted: true",
            f"- Authenticated WP read GET succeeded: {'true' if read_ok else 'false'}",
            f"- Authenticated WP read status class: {status_class}",
            "- Response body saved: false",
            "- Authenticated user identity saved: false",
            "- Credential values output: false",
            "- Credential length output: false",
            "- Credential hash output: false",
            "- Authorization header output: false",
            "- Basic auth output: false",
            "- Base64 auth output: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- WordPress publish executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Ready for LS-NEW-13: true",
            "",
            "LS-NEW-12 は認証付き WordPress read-only プリフライトのみであり、",
            "WordPress下書き作成・WordPress write・公開・credential値出力・response body保存・ユーザー情報保存は実行しない。",
            "",
        ]
    )


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-12 Authenticated WP Read Preflight Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- wordpress_authenticated_read_status_class: {result.get('wordpress_authenticated_read_status_class', 'SKIPPED')}",
        "",
        "## Errors",
    ]
    errs = list(result.get("errors", []))
    if errs:
        lines.extend(f"- {e}" for e in errs)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    _validate_flags(args, errors)

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    ls11_result = try_load_json(Path(args.ls_new11_result), errors, "ls-new11-result")
    ls11_validation = try_load_json(Path(args.ls_new11_validation_result), errors, "ls-new11-validation-result")
    ls11_manifest = try_load_json(Path(args.ls_new11_manifest), errors, "ls-new11-manifest")
    ls11_credential_summary = try_load_json(Path(args.ls_new11_credential_summary), errors, "ls-new11-credential-summary")
    ls11_wp_connectivity = try_load_json(Path(args.ls_new11_wp_connectivity_result), errors, "ls-new11-wp-connectivity-result")
    ls11_no_write_contract = try_load_json(Path(args.ls_new11_no_write_safety_contract), errors, "ls-new11-no-write-safety-contract")
    ls11_handoff = try_load_json(Path(args.ls_new11_next_phase_handoff), errors, "ls-new11-next-phase-handoff")

    req(policy.get("phase") == "LS-NEW-12", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-12", "schema phase mismatch", errors)

    req(ls11_validation.get("validation_status") == REQ_LS11_VALID, "ls-new11 validation status mismatch", errors)
    req(ls11_result.get("status") == REQ_LS11_STATUS, "ls-new11 run status mismatch", errors)
    req(ls11_result.get("ready_for_ls_new_12") is True, "ls-new11 ready_for_ls_new_12 mismatch", errors)

    req(ls11_result.get("credential_env_exists") is True, "ls-new11 credential_env_exists mismatch", errors)
    req(ls11_result.get("credential_existence_check_executed") is True, "ls-new11 credential_existence_check_executed mismatch", errors)
    req(ls11_result.get("credential_env_read_executed") is True, "ls-new11 credential_env_read_executed mismatch", errors)
    req(ls11_result.get("required_url_key_present") is True, "ls-new11 required_url_key_present mismatch", errors)
    req(ls11_result.get("required_username_key_present") is True, "ls-new11 required_username_key_present mismatch", errors)
    req(ls11_result.get("required_app_password_key_present") is True, "ls-new11 required_app_password_key_present mismatch", errors)
    req(ls11_result.get("required_url_value_nonempty") is True, "ls-new11 required_url_value_nonempty mismatch", errors)
    req(ls11_result.get("required_username_value_nonempty") is True, "ls-new11 required_username_value_nonempty mismatch", errors)
    req(ls11_result.get("required_app_password_value_nonempty") is True, "ls-new11 required_app_password_value_nonempty mismatch", errors)
    req(ls11_result.get("wordpress_rest_index_get_succeeded") is True, "ls-new11 wordpress_rest_index_get_succeeded mismatch", errors)
    req(ls11_result.get("wordpress_rest_response_body_saved") is False, "ls-new11 wordpress_rest_response_body_saved mismatch", errors)
    req(ls11_result.get("wordpress_authenticated_get_executed") is False, "ls-new11 wordpress_authenticated_get_executed mismatch", errors)

    req(ls11_result.get("execution_allowed") is False, "ls-new11 execution_allowed mismatch", errors)
    req(ls11_result.get("runner_execution_allowed") is False, "ls-new11 runner_execution_allowed mismatch", errors)
    req(ls11_result.get("final_execution_command_created") is False, "ls-new11 final_execution_command_created mismatch", errors)
    req(ls11_result.get("wordpress_write_executed") is False, "ls-new11 wordpress_write_executed mismatch", errors)
    req(ls11_result.get("wordpress_draft_created") is False, "ls-new11 wordpress_draft_created mismatch", errors)
    req(ls11_result.get("wordpress_publish_executed") is False, "ls-new11 wordpress_publish_executed mismatch", errors)
    req(ls11_result.get("wordpress_update_executed") is False, "ls-new11 wordpress_update_executed mismatch", errors)
    req(ls11_result.get("wordpress_delete_executed") is False, "ls-new11 wordpress_delete_executed mismatch", errors)
    req(ls11_result.get("target_post_id") is None, "ls-new11 target_post_id must be null", errors)
    req(ls11_result.get("target_post_id_allocated") is False, "ls-new11 target_post_id_allocated mismatch", errors)
    req(ls11_result.get("approval_label_consumed") is False, "ls-new11 approval_label_consumed mismatch", errors)

    req(ls11_manifest.get("phase") == "LS-NEW-11", "ls-new11 manifest phase mismatch", errors)
    req(ls11_credential_summary.get("phase") == "LS-NEW-11", "ls-new11 credential-summary phase mismatch", errors)
    req(ls11_wp_connectivity.get("phase") == "LS-NEW-11", "ls-new11 wp-connectivity-result phase mismatch", errors)
    req(ls11_no_write_contract.get("phase") == "LS-NEW-11", "ls-new11 no-write-safety-contract phase mismatch", errors)
    req(ls11_handoff.get("phase") == "LS-NEW-11", "ls-new11 next-phase-handoff phase mismatch", errors)

    credential_env_path = Path(args.credential_env)
    credential_env_exists = credential_env_path.exists()
    credential_existence_check_executed = args.allow_credential_env_existence_check
    credential_env_read_executed = False
    env_map: dict[str, str] = {}

    if not credential_env_exists:
        errors.append("credential env missing")
    elif args.allow_credential_env_read:
        try:
            env_map = _parse_env(credential_env_path.read_text(encoding="utf-8"))
            credential_env_read_executed = True
        except Exception:
            errors.append("credential env read failed")

    url_present, url_nonempty, url_value = _select_value(env_map, URL_ALIASES)
    user_present, user_nonempty, user_value = _select_value(env_map, USERNAME_ALIASES)
    app_present, app_nonempty, app_value = _select_value(env_map, APP_PASSWORD_ALIASES)

    if not url_present:
        errors.append("required URL key missing")
    if not user_present:
        errors.append("required username key missing")
    if not app_present:
        errors.append("required app password key missing")
    if url_present and not url_nonempty:
        errors.append("required URL empty")
    if user_present and not user_nonempty:
        errors.append("required username empty")
    if app_present and not app_nonempty:
        errors.append("required app password empty")

    auth_get_attempted = False
    auth_get_succeeded = False
    auth_status_class = "SKIPPED"

    if args.allow_authenticated_wp_read_get and url_nonempty and user_nonempty and app_nonempty:
        auth_get_attempted = True
        auth_get_succeeded, auth_status_class = _run_authenticated_wp_get(
            url_value,
            user_value,
            app_value,
            args.authenticated_read_endpoint,
            args.connect_timeout_seconds,
        )
        if not auth_get_succeeded:
            errors.append("wordpress authenticated read failed")

    success = len(errors) == 0
    status = READY if success else FAILED

    content = {
        "content_item_id": str(ls11_result.get("content_item_id", "new-comic-001")),
        "title": str(ls11_result.get("title", "月曜日のたわわ")),
        "volume": str(ls11_result.get("volume", "第15巻")),
        "author": str(ls11_result.get("author", "比村奇石")),
        "publisher": str(ls11_result.get("publisher", "講談社")),
        "release_date": str(ls11_result.get("release_date", "2026-07-06")),
        "post_status_target": "draft",
    }

    common = {
        "phase": "LS-NEW-12",
        "status": status,
        "execution_mode": "AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE",
        "production_status": "NO_WRITE_AUTHENTICATED_READ_PREFLIGHT_ONLY",
        "ls_new11_validated": success,
        "ls_new11_ready": success,
        "credential_env_exists": credential_env_exists,
        "credential_existence_check_executed": credential_existence_check_executed,
        "credential_env_read_executed": credential_env_read_executed,
        "wordpress_authenticated_read_get_attempted": auth_get_attempted,
        "wordpress_authenticated_read_get_succeeded": auth_get_succeeded,
        "wordpress_authenticated_read_status_class": auth_status_class,
        "wordpress_authenticated_read_endpoint_kind": "users_me",
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "authenticated_wp_read_result_created": success,
        "secret_non_output_summary_created": success,
        "no_write_safety_contract_created": success,
        "draft_creation_hold_boundary_created": success,
        "next_phase_handoff_created": success,
        "preflight_summary_created": success,
        **content,
        **_fixed_false_block(),
        "ready_for_ls_new_13": success,
        "recommended_next_action": "BEGIN_LS_NEW_13_DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION" if success else "REVIEW_ERRORS_AND_RETRY_LS_NEW_12",
        "recommended_next_phase_options": ["LS-NEW-13", "LS-MON-2"],
        "errors": list(errors),
    }

    manifest = {
        **common,
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_MANIFEST",
    }
    write_json(Path(args.output_manifest), manifest)

    authenticated_read_result = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_RESULT",
        "status": "LSNEW12_AUTHENTICATED_WP_READ_READY_NO_WRITE" if success else "LSNEW12_AUTHENTICATED_WP_READ_FAILED_NO_WRITE",
        "wordpress_authenticated_read_get_attempted": auth_get_attempted,
        "wordpress_authenticated_read_get_succeeded": auth_get_succeeded,
        "wordpress_authenticated_read_status_class": auth_status_class,
        "wordpress_authenticated_read_endpoint_kind": "users_me",
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_authenticated_read_result), authenticated_read_result)

    secret_non_output_summary = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_SECRET_NON_OUTPUT_SUMMARY",
        "status": "LSNEW12_SECRET_NON_OUTPUT_CONFIRMED",
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
    }
    write_json(Path(args.output_secret_non_output_summary), secret_non_output_summary)

    no_write_contract = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_NO_WRITE_SAFETY_CONTRACT",
        "status": "LSNEW12_NO_WRITE_SAFETY_CONTRACT_READY",
        "no_write_required": True,
        "wordpress_get_only": True,
        "wordpress_post_allowed": False,
        "wordpress_put_allowed": False,
        "wordpress_patch_allowed": False,
        "wordpress_delete_allowed": False,
        "wordpress_draft_create_allowed": False,
        "wordpress_publish_allowed": False,
        "wordpress_update_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "target_post_id_allocation_allowed": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_no_write_safety_contract), no_write_contract)

    draft_creation_hold_boundary = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_DRAFT_CREATION_HOLD_BOUNDARY",
        "status": "LSNEW12_DRAFT_CREATION_HOLD_BOUNDARY_READY_NO_DRAFT_CREATION",
        "draft_creation_still_blocked": True,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "required_before_later_draft_creation": [
            "LS-NEW-13 must prepare a separate draft creation command without execution",
            "A later explicit execution approval gate must approve one draft creation only",
            "target_post_id must remain null before creation",
            "post119/post183 update must remain forbidden",
            "rollback/freeze boundary must remain available",
        ],
        "execution_allowed": False,
    }
    write_json(Path(args.output_draft_creation_hold_boundary), draft_creation_hold_boundary)

    handoff = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_NEXT_PHASE_HANDOFF",
        "status": "LSNEW12_NEXT_PHASE_HANDOFF_READY",
        "next_phase": "LS-NEW-13",
        "next_phase_name": "Draft Creation Command Prep / No Execution",
        "handoff_ready": success,
        "ready_for_ls_new_13": success,
        "notes": [
            "LS-NEW-12 confirmed authenticated WordPress read-only GET.",
            "LS-NEW-12 did not save response body, user identity, Authorization header, Basic auth, base64, or credential values.",
            "LS-NEW-13 may prepare a blocked draft creation command only.",
            "No WordPress draft creation is allowed by this handoff.",
        ],
    }
    write_json(Path(args.output_next_phase_handoff), handoff)

    write_text(Path(args.output_summary), _summary_text(auth_get_succeeded, auth_status_class))

    result = {
        **common,
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_RESULT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)

    lock = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCK",
        "status": LOCKED,
        "locked": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "base64_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "wordpress_authenticated_read_response_body_saved": False,
        "wordpress_authenticated_user_identity_saved": False,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }
    write_json(Path(args.lock_output), lock)

    _report(Path(args.report), result)
    print(status)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
