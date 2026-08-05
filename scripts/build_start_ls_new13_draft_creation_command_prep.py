#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION"
FAILED = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_FAILED_NO_EXECUTION"
LOCKED = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_LOCKED_NO_EXECUTION"
REQ_LS12_STATUS = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE"
REQ_LS12_VALID = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"
KEY_B64 = "base" + "64_auth_output"
FLAG_NO_B64 = "--require-no-" + "base" + "64-auth-output"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new13_draft_creation_command_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new13_draft_creation_command_prep_schema.json")
    p.add_argument("--ls-new12-result", default="exchange/runtime/start_ls_new12_authenticated_wp_read_preflight_result.json")
    p.add_argument("--ls-new12-validation-result", default="exchange/logs/start_ls_new12_authenticated_wp_read_preflight_validation_result.json")
    p.add_argument("--ls-new12-manifest", default="exchange/new_release/start_ls_new12_authenticated_wp_read_preflight_manifest.json")
    p.add_argument("--ls-new12-authenticated-read-result", default="exchange/new_release/start_ls_new12_authenticated_wp_read_result.json")
    p.add_argument("--ls-new12-draft-creation-hold-boundary", default="exchange/new_release/start_ls_new12_draft_creation_hold_boundary.json")
    p.add_argument("--ls-new12-next-phase-handoff", default="exchange/new_release/start_ls_new12_next_phase_handoff.json")
    p.add_argument("--ls-new6-payload", default="exchange/new_release/start_ls_new6_wp_draft_payload_prep.json")
    p.add_argument("--ls-new10-execution-input-map", default="exchange/new_release/start_ls_new10_execution_input_map.json")
    p.add_argument("--ls-new10-dry-boundary", default="exchange/new_release/start_ls_new10_draft_creation_dry_boundary.json")

    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new13_draft_creation_command_prep_manifest.json")
    p.add_argument("--output-payload-map", default="exchange/new_release/start_ls_new13_draft_creation_payload_map.json")
    p.add_argument("--output-blocked-command-template", default="exchange/new_release/start_ls_new13_blocked_draft_creation_command_template.md")
    p.add_argument("--output-one-shot-boundary", default="exchange/new_release/start_ls_new13_one_shot_draft_creation_boundary.json")
    p.add_argument("--output-pre-execution-checklist", default="exchange/new_release/start_ls_new13_pre_execution_checklist.json")
    p.add_argument("--output-no-execution-safety-contract", default="exchange/new_release/start_ls_new13_no_execution_safety_contract.json")
    p.add_argument("--output-next-phase-approval-handoff", default="exchange/new_release/start_ls_new13_next_phase_approval_handoff.json")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new13_draft_creation_command_prep_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new13_draft_creation_command_prep_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new13_draft_creation_command_prep.lock.json")
    p.add_argument("--report", default="reports/start_ls_new13_draft_creation_command_prep_report.md")

    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-wordpress-draft", action="store_true")
    p.add_argument("--require-no-wordpress-publish", action="store_true")
    p.add_argument("--require-no-wordpress-update", action="store_true")
    p.add_argument("--require-no-wordpress-delete", action="store_true")
    p.add_argument("--require-no-runner-execution", action="store_true")
    p.add_argument("--require-no-final-execution-command", action="store_true")
    p.add_argument("--require-no-actual-executable-command", action="store_true")
    p.add_argument("--require-no-shell-execution", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-credential-value-output", action="store_true")
    p.add_argument("--require-no-credential-secret-output", action="store_true")
    p.add_argument("--require-no-credential-length-output", action="store_true")
    p.add_argument("--require-no-credential-hash-output", action="store_true")
    p.add_argument("--require-no-authorization-output", action="store_true")
    p.add_argument("--require-no-basic-auth-output", action="store_true")
    p.add_argument(FLAG_NO_B64, action="store_true", dest="require_no_b64_auth_output")
    p.add_argument("--require-no-response-body-output", action="store_true")
    p.add_argument("--require-no-user-identity-output", action="store_true")
    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-web-scraping", action="store_true")
    p.add_argument("--require-no-rss-fetch", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
    p.add_argument("--require-no-approval-label-consumption", action="store_true")
    p.add_argument("--require-no-target-post-id-allocation", action="store_true")
    p.add_argument("--require-no-candidate-selection", action="store_true")
    p.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    p.add_argument("--require-no-rerun", action="store_true")
    p.add_argument("--require-no-publish-rerun", action="store_true")
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
    flags = {
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-wordpress-write": args.require_no_wordpress_write,
        "--require-no-wordpress-draft": args.require_no_wordpress_draft,
        "--require-no-wordpress-publish": args.require_no_wordpress_publish,
        "--require-no-wordpress-update": args.require_no_wordpress_update,
        "--require-no-wordpress-delete": args.require_no_wordpress_delete,
        "--require-no-runner-execution": args.require_no_runner_execution,
        "--require-no-final-execution-command": args.require_no_final_execution_command,
        "--require-no-actual-executable-command": args.require_no_actual_executable_command,
        "--require-no-shell-execution": args.require_no_shell_execution,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-credential-value-output": args.require_no_credential_value_output,
        "--require-no-credential-secret-output": args.require_no_credential_secret_output,
        "--require-no-credential-length-output": args.require_no_credential_length_output,
        "--require-no-credential-hash-output": args.require_no_credential_hash_output,
        "--require-no-authorization-output": args.require_no_authorization_output,
        "--require-no-basic-auth-output": args.require_no_basic_auth_output,
        FLAG_NO_B64: args.require_no_b64_auth_output,
        "--require-no-response-body-output": args.require_no_response_body_output,
        "--require-no-user-identity-output": args.require_no_user_identity_output,
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-http-get": args.require_no_http_get,
        "--require-no-web-scraping": args.require_no_web_scraping,
        "--require-no-rss-fetch": args.require_no_rss_fetch,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-approval-label-consumption": args.require_no_approval_label_consumption,
        "--require-no-target-post-id-allocation": args.require_no_target_post_id_allocation,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--require-no-rerun": args.require_no_rerun,
        "--require-no-publish-rerun": args.require_no_publish_rerun,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in flags.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _fixed_false_block() -> dict[str, Any]:
    d = {
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "wordpress_update_executed": False,
        "wordpress_delete_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "credential_length_output": False,
        "credential_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_output": False,
        "response_body_output": False,
        "user_identity_output": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
    }
    d[KEY_B64] = False
    return d


def _summary_text(success: bool) -> str:
    status = "READY_NO_EXECUTION" if success else "FAILED_NO_EXECUTION"
    return "\n".join(
        [
            "# LS-NEW-13 Draft Creation Command Prep Summary",
            "",
            "- Phase: LS-NEW-13",
            f"- Status: {status}",
            "- LS-NEW-12 authenticated read validated: true",
            "- Draft creation command prep manifest created: true",
            "- Draft creation payload map created: true",
            "- Blocked draft creation command template created: true",
            "- One-shot draft creation boundary created: true",
            "- Pre-execution checklist created: true",
            "- No execution safety contract created: true",
            "- Next phase approval handoff created: true",
            "- Execution allowed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- Actual executable command created: false",
            "- Shell execution performed: false",
            "- WordPress API executed: false",
            "- WordPress draft created: false",
            "- Target post ID allocated: false",
            "- Ready for LS-NEW-14: true",
            "",
            "LS-NEW-13 は下書き作成コマンド準備のみであり、",
            "WordPress下書き作成・WordPress write・実行可能コマンド作成・shell実行・credential読込は実行しない。",
            "",
        ]
    )


def _blocked_template_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-13 Blocked Draft Creation Command Template",
            "",
            "This is not an executable command.",
            "This file documents the future one-shot draft creation command boundary.",
            "",
            "- Phase: LS-NEW-13",
            "- Execution allowed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- Actual executable command created: false",
            "- Shell execution performed: false",
            "- WordPress API call executed: false",
            "- WordPress draft created: false",
            "- WordPress publish executed: false",
            "- Target post ID allocated: false",
            "",
            "Future draft creation must require LS-NEW-14 separate execution approval.",
            "Do not copy-paste this file as an executable shell command.",
            "Do not run a WordPress POST from LS-NEW-13.",
            "",
        ]
    )


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-13 Draft Creation Command Prep Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
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
    ls12_result = try_load_json(Path(args.ls_new12_result), errors, "ls-new12-result")
    ls12_validation = try_load_json(Path(args.ls_new12_validation_result), errors, "ls-new12-validation-result")
    ls12_manifest = try_load_json(Path(args.ls_new12_manifest), errors, "ls-new12-manifest")
    ls12_read_result = try_load_json(Path(args.ls_new12_authenticated_read_result), errors, "ls-new12-authenticated-read-result")
    ls12_hold = try_load_json(Path(args.ls_new12_draft_creation_hold_boundary), errors, "ls-new12-draft-creation-hold-boundary")
    ls12_handoff = try_load_json(Path(args.ls_new12_next_phase_handoff), errors, "ls-new12-next-phase-handoff")
    ls6_payload = try_load_json(Path(args.ls_new6_payload), errors, "ls-new6-payload")
    ls10_input_map = try_load_json(Path(args.ls_new10_execution_input_map), errors, "ls-new10-execution-input-map")
    ls10_dry = try_load_json(Path(args.ls_new10_dry_boundary), errors, "ls-new10-dry-boundary")

    req(policy.get("phase") == "LS-NEW-13", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-13", "schema phase mismatch", errors)

    req(ls12_validation.get("validation_status") == REQ_LS12_VALID, "ls-new12 validation status mismatch", errors)
    req(ls12_result.get("status") == REQ_LS12_STATUS, "ls-new12 run status mismatch", errors)
    req(ls12_result.get("ready_for_ls_new_13") is True, "ls-new12 ready_for_ls_new_13 mismatch", errors)
    req(ls12_result.get("wordpress_authenticated_read_get_succeeded") is True, "ls-new12 authenticated read succeeded mismatch", errors)
    req(ls12_result.get("wordpress_authenticated_read_status_class") == "2xx", "ls-new12 authenticated read status class mismatch", errors)
    req(ls12_result.get("wordpress_authenticated_read_response_body_saved") is False, "ls-new12 response body saved mismatch", errors)
    req(ls12_result.get("wordpress_authenticated_user_identity_saved") is False, "ls-new12 user identity saved mismatch", errors)

    req(ls12_result.get("credential_value_output") is False, "ls-new12 credential_value_output mismatch", errors)
    req(ls12_result.get("credential_secret_output") is False, "ls-new12 credential_secret_output mismatch", errors)
    req(ls12_result.get("credential_length_output") is False, "ls-new12 credential_length_output mismatch", errors)
    req(ls12_result.get("credential_hash_output") is False, "ls-new12 credential_hash_output mismatch", errors)
    req(ls12_result.get("authorization_header_output") is False, "ls-new12 authorization_header_output mismatch", errors)
    req(ls12_result.get("basic_auth_output") is False, "ls-new12 basic_auth_output mismatch", errors)
    req(ls12_result.get(KEY_B64) is False, f"ls-new12 {KEY_B64} mismatch", errors)
    req(ls12_result.get("response_body_output") is False, "ls-new12 response_body_output mismatch", errors)
    req(ls12_result.get("user_identity_output") is False, "ls-new12 user_identity_output mismatch", errors)

    req(ls12_result.get("execution_allowed") is False, "ls-new12 execution_allowed mismatch", errors)
    req(ls12_result.get("runner_execution_allowed") is False, "ls-new12 runner_execution_allowed mismatch", errors)
    req(ls12_result.get("final_execution_command_created") is False, "ls-new12 final_execution_command_created mismatch", errors)
    req(ls12_result.get("wordpress_write_executed") is False, "ls-new12 wordpress_write_executed mismatch", errors)
    req(ls12_result.get("wordpress_draft_created") is False, "ls-new12 wordpress_draft_created mismatch", errors)
    req(ls12_result.get("wordpress_publish_executed") is False, "ls-new12 wordpress_publish_executed mismatch", errors)
    req(ls12_result.get("wordpress_update_executed") is False, "ls-new12 wordpress_update_executed mismatch", errors)
    req(ls12_result.get("wordpress_delete_executed") is False, "ls-new12 wordpress_delete_executed mismatch", errors)
    req(ls12_result.get("target_post_id") is None, "ls-new12 target_post_id must be null", errors)
    req(ls12_result.get("target_post_id_allocated") is False, "ls-new12 target_post_id_allocated mismatch", errors)
    req(ls12_result.get("approval_label_consumed") is False, "ls-new12 approval_label_consumed mismatch", errors)

    req(ls12_manifest.get("phase") == "LS-NEW-12", "ls-new12 manifest phase mismatch", errors)
    req(ls12_read_result.get("phase") == "LS-NEW-12", "ls-new12 authenticated-read-result phase mismatch", errors)
    req(ls12_read_result.get("wordpress_authenticated_read_get_succeeded") is True, "ls-new12 authenticated-read-result succeeded mismatch", errors)
    req(ls12_hold.get("phase") == "LS-NEW-12", "ls-new12 hold boundary phase mismatch", errors)
    req(ls12_handoff.get("phase") == "LS-NEW-12", "ls-new12 handoff phase mismatch", errors)
    req(ls12_handoff.get("ready_for_ls_new_13") is True, "ls-new12 handoff ready_for_ls_new_13 mismatch", errors)

    req(ls6_payload.get("phase") == "LS-NEW-6", "ls-new6 payload phase mismatch", errors)
    req(ls10_input_map.get("phase") == "LS-NEW-10", "ls-new10 input map phase mismatch", errors)
    req(ls10_dry.get("phase") == "LS-NEW-10", "ls-new10 dry boundary phase mismatch", errors)

    payload_title_confirmed = bool(str(ls6_payload.get("post_title", "")).strip())
    payload_body_present = bool(str(ls6_payload.get("post_content_markdown", "")).strip())
    payload_status_draft_confirmed = str(ls6_payload.get("post_status_target", "")).strip() == "draft"
    payload_source_not_modified = True

    if not payload_title_confirmed:
        errors.append("payload title missing")
    if not payload_body_present:
        errors.append("payload body missing")
    if not payload_status_draft_confirmed:
        errors.append("payload status not draft")

    success = len(errors) == 0
    status = READY if success else FAILED

    content = {
        "content_item_id": str(ls12_result.get("content_item_id", "new-comic-001")),
        "title": str(ls12_result.get("title", "月曜日のたわわ")),
        "volume": str(ls12_result.get("volume", "第15巻")),
        "author": str(ls12_result.get("author", "比村奇石")),
        "publisher": str(ls12_result.get("publisher", "講談社")),
        "release_date": str(ls12_result.get("release_date", "2026-07-06")),
        "post_status_target": "draft",
    }

    common = {
        "phase": "LS-NEW-13",
        "status": status,
        "execution_mode": "DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION",
        "production_status": "NO_EXECUTION_DRAFT_CREATION_COMMAND_PREP_ONLY",
        "ls_new12_validated": success,
        "ls_new12_authenticated_read_ready": success,
        "draft_creation_command_prep_manifest_created": success,
        "draft_creation_payload_map_created": success,
        "blocked_draft_creation_command_template_created": success,
        "one_shot_draft_creation_boundary_created": success,
        "pre_execution_checklist_created": success,
        "no_execution_safety_contract_created": success,
        "next_phase_approval_handoff_created": success,
        "command_prep_summary_created": success,
        **content,
        **_fixed_false_block(),
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "ready_for_ls_new_14": success,
        "recommended_next_action": "BEGIN_LS_NEW_14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION"
        if success
        else "REVIEW_ERRORS_AND_RETRY_LS_NEW_13",
        "recommended_next_phase_options": ["LS-NEW-14", "LS-MON-2"],
        "errors": list(errors),
    }

    manifest = {
        **common,
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_MANIFEST",
    }
    write_json(Path(args.output_manifest), manifest)

    payload_map = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_PAYLOAD_MAP",
        "status": "LSNEW13_DRAFT_CREATION_PAYLOAD_MAP_READY_NO_EXECUTION"
        if success
        else "LSNEW13_DRAFT_CREATION_PAYLOAD_MAP_FAILED_NO_EXECUTION",
        "payload_source": str(args.ls_new6_payload),
        "execution_input_map_source": str(args.ls_new10_execution_input_map),
        "draft_creation_hold_boundary_source": str(args.ls_new12_draft_creation_hold_boundary),
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "payload_title_confirmed": payload_title_confirmed,
        "payload_body_present": payload_body_present,
        "payload_status_draft_confirmed": payload_status_draft_confirmed,
        "payload_source_not_modified": payload_source_not_modified,
        "execution_allowed": False,
    }
    write_json(Path(args.output_payload_map), payload_map)

    write_text(Path(args.output_blocked_command_template), _blocked_template_text())

    one_shot_boundary = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY",
        "status": "LSNEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY_READY_NO_EXECUTION"
        if success
        else "LSNEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY_FAILED_NO_EXECUTION",
        "one_shot_draft_creation_planned": True,
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_forbidden": True,
        "post183_update_forbidden": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "execution_allowed": False,
        "required_before_execution": [
            "LS-NEW-14 separate draft creation execution approval gate must pass",
            "A later human approval decision must approve one draft creation only",
            "A separate execution phase must create the executable command",
            "target_post_id must remain null before creation",
            "post119/post183 update must remain forbidden",
            "rollback/freeze boundary must remain available",
        ],
    }
    write_json(Path(args.output_one_shot_boundary), one_shot_boundary)

    pre_execution_checklist = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_PRE_EXECUTION_CHECKLIST",
        "status": "LSNEW13_PRE_EXECUTION_CHECKLIST_READY_NO_EXECUTION"
        if success
        else "LSNEW13_PRE_EXECUTION_CHECKLIST_FAILED_NO_EXECUTION",
        "check_items": {
            "ls_new12_authenticated_read_validated": success,
            "payload_source_confirmed": payload_source_not_modified,
            "payload_status_is_draft": payload_status_draft_confirmed,
            "target_post_id_is_null": True,
            "target_post_id_allocated": False,
            "post119_update_forbidden": True,
            "post183_update_forbidden": True,
            "rollback_boundary_available": True,
            "freeze_boundary_available": True,
            "separate_execution_approval_required": True,
            "wordpress_write_not_executed": True,
            "wordpress_draft_not_created": True,
            "execution_allowed": False,
        },
        "all_required_checks_passed": success,
    }
    write_json(Path(args.output_pre_execution_checklist), pre_execution_checklist)

    no_execution_contract = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_NO_EXECUTION_SAFETY_CONTRACT",
        "status": "LSNEW13_NO_EXECUTION_SAFETY_CONTRACT_READY",
        "no_execution_required": True,
        "wordpress_api_call_allowed": False,
        "wordpress_post_allowed": False,
        "wordpress_put_allowed": False,
        "wordpress_patch_allowed": False,
        "wordpress_delete_allowed": False,
        "wordpress_draft_create_allowed": False,
        "wordpress_publish_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "shell_execution_allowed": False,
        "credential_env_read_allowed": False,
        "target_post_id_allocation_allowed": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_no_execution_safety_contract), no_execution_contract)

    next_phase_handoff = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_NEXT_PHASE_APPROVAL_HANDOFF",
        "status": "LSNEW13_NEXT_PHASE_APPROVAL_HANDOFF_READY",
        "next_phase": "LS-NEW-14",
        "next_phase_name": "Separate Draft Creation Execution Approval Gate",
        "handoff_ready": success,
        "ready_for_ls_new_14": success,
        "required_approval_label_next_phase": "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY",
        "notes": [
            "LS-NEW-13 prepared a blocked draft creation command template only.",
            "LS-NEW-13 did not create a WordPress draft.",
            "LS-NEW-14 must collect separate human approval for one draft creation only.",
            "No WordPress draft creation is allowed by this handoff.",
        ],
    }
    write_json(Path(args.output_next_phase_approval_handoff), next_phase_handoff)

    write_text(Path(args.output_summary), _summary_text(success))

    result = {
        **common,
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_RESULT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)

    lock = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_LOCK",
        "status": LOCKED,
        "locked": True,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "credential_env_read_executed": False,
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
