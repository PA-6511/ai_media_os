#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION"
FAILED = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_FAILED_NO_EXECUTION"
LOCKED = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCKED_NO_EXECUTION"
REQ_LS7_STATUS = "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"
REQ_LS7_VALID = "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new8_wp_draft_runner_final_preflight_policy.json")
    p.add_argument("--schema", default="config/start_ls_new8_wp_draft_runner_final_preflight_schema.json")
    p.add_argument("--ls-new7-manifest", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json")
    p.add_argument("--ls-new7-safety-contract", default="exchange/new_release/start_ls_new7_wp_draft_runner_safety_contract.json")
    p.add_argument("--ls-new7-preflight-checklist", default="exchange/new_release/start_ls_new7_wp_draft_runner_preflight_checklist.json")
    p.add_argument("--ls-new7-command-template", default="exchange/new_release/start_ls_new7_blocked_execution_command_template.md")
    p.add_argument("--ls-new7-summary", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_summary.md")
    p.add_argument("--ls-new7-result", default="exchange/runtime/start_ls_new7_wp_draft_runner_prep_result.json")
    p.add_argument("--ls-new7-validation-result", default="exchange/logs/start_ls_new7_wp_draft_runner_prep_validation_result.json")
    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new8_final_preflight_manifest.json")
    p.add_argument("--output-freeze-boundary", default="exchange/new_release/start_ls_new8_freeze_boundary.json")
    p.add_argument("--output-rollback-boundary", default="exchange/new_release/start_ls_new8_rollback_boundary.json")
    p.add_argument("--output-abort-conditions", default="exchange/new_release/start_ls_new8_abort_conditions.json")
    p.add_argument("--output-handoff", default="exchange/new_release/start_ls_new8_next_approval_gate_handoff.json")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new8_final_preflight_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new8_wp_draft_runner_final_preflight_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new8_wp_draft_runner_final_preflight.lock.json")
    p.add_argument("--report", default="reports/start_ls_new8_wp_draft_runner_final_preflight_report.md")

    p.add_argument("--require-no-runner-execution", action="store_true")
    p.add_argument("--require-no-final-execution-command", action="store_true")
    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-wordpress-draft", action="store_true")
    p.add_argument("--require-no-wordpress-publish", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-credential-check", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
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


def read_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        errors.append(f"failed to read {label}: {path}")
        return ""


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
    required = {
        "--require-no-runner-execution": args.require_no_runner_execution,
        "--require-no-final-execution-command": args.require_no_final_execution_command,
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-http-get": args.require_no_http_get,
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-wordpress-write": args.require_no_wordpress_write,
        "--require-no-wordpress-draft": args.require_no_wordpress_draft,
        "--require-no-wordpress-publish": args.require_no_wordpress_publish,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-credential-check": args.require_no_credential_check,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-approval-label-consumption": args.require_no_approval_label_consumption,
        "--require-no-target-post-id-allocation": args.require_no_target_post_id_allocation,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in required.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _summary_md() -> str:
    return "\n".join(
        [
            "# LS-NEW-8 WordPress Draft Runner Final Preflight Summary",
            "",
            "- Phase: LS-NEW-8",
            "- Status: READY_NO_EXECUTION",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Credential existence check executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Ready for LS-NEW-9: true",
            "",
        ]
    )


def _lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCK",
        "status": LOCKED,
        "locked": True,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "execution_allowed": False,
        "approval_label_consumed": False,
        "target_post_id_allocated": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-8 WP Draft Runner Final Preflight Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- content_item_id: {result.get('content_item_id', '')}",
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
    ls7_manifest = try_load_json(Path(args.ls_new7_manifest), errors, "ls-new7-manifest")
    ls7_safety = try_load_json(Path(args.ls_new7_safety_contract), errors, "ls-new7-safety-contract")
    ls7_preflight = try_load_json(Path(args.ls_new7_preflight_checklist), errors, "ls-new7-preflight-checklist")
    _ = read_text(Path(args.ls_new7_command_template), errors, "ls-new7-command-template")
    _ = read_text(Path(args.ls_new7_summary), errors, "ls-new7-summary")
    ls7_result = try_load_json(Path(args.ls_new7_result), errors, "ls-new7-result")
    ls7_validation = try_load_json(Path(args.ls_new7_validation_result), errors, "ls-new7-validation-result")

    req(policy.get("phase") == "LS-NEW-8", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-8", "schema phase mismatch", errors)

    req(ls7_result.get("status") == REQ_LS7_STATUS, "ls-new7 run status mismatch", errors)
    req(ls7_validation.get("validation_status") == REQ_LS7_VALID, "ls-new7 validation status mismatch", errors)
    req(ls7_result.get("ready_for_ls_new_8") is True, "ls-new7 ready_for_ls_new_8 mismatch", errors)
    req(ls7_result.get("execution_allowed") is False, "ls-new7 execution_allowed mismatch", errors)
    req(ls7_result.get("runner_execution_allowed") is False, "ls-new7 runner_execution_allowed mismatch", errors)
    req(ls7_result.get("wordpress_api_call_executed") is False, "ls-new7 wordpress_api_call_executed=true", errors)
    req(ls7_result.get("wordpress_write_executed") is False, "ls-new7 wordpress_write_executed=true", errors)
    req(ls7_result.get("wordpress_draft_created") is False, "ls-new7 wordpress_draft_created=true", errors)
    req(ls7_result.get("credential_env_read_executed") is False, "ls-new7 credential_env_read_executed=true", errors)
    req(ls7_result.get("credential_existence_check_executed") is False, "ls-new7 credential_existence_check_executed=true", errors)
    req(ls7_result.get("target_post_id_allocated") is False, "ls-new7 target_post_id_allocated=true", errors)
    req(ls7_manifest.get("status") == "LSNEW7_WP_DRAFT_RUNNER_PREP_MANIFEST_READY_NO_EXECUTION", "ls-new7 manifest status mismatch", errors)
    req(ls7_safety.get("status") == "LSNEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT_READY_NO_EXECUTION", "ls-new7 safety status mismatch", errors)
    req(ls7_preflight.get("status") == "LSNEW7_PREFLIGHT_CHECKLIST_READY_NO_EXECUTION", "ls-new7 preflight status mismatch", errors)

    content = {
        "content_item_id": str(ls7_manifest.get("content_item_id", "")),
        "title": str(ls7_manifest.get("title", "")),
        "volume": str(ls7_manifest.get("volume", "")),
        "author": str(ls7_manifest.get("author", "")),
        "publisher": str(ls7_manifest.get("publisher", "")),
        "release_date": str(ls7_manifest.get("release_date", "")),
    }
    for key, value in content.items():
        req(value.strip() != "", f"missing ls-new7 manifest field: {key}", errors)

    manifest = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_FINAL_PREFLIGHT_MANIFEST",
        "status": "LSNEW8_FINAL_PREFLIGHT_MANIFEST_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY",
        "ls_new7_validated": len(errors) == 0,
        "source_manifest": "exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json",
        "source_safety_contract": "exchange/new_release/start_ls_new7_wp_draft_runner_safety_contract.json",
        "source_preflight_checklist": "exchange/new_release/start_ls_new7_wp_draft_runner_preflight_checklist.json",
        "source_blocked_execution_command_template": "exchange/new_release/start_ls_new7_blocked_execution_command_template.md",
        "content_item_id": content["content_item_id"],
        "title": content["title"],
        "volume": content["volume"],
        "author": content["author"],
        "publisher": content["publisher"],
        "release_date": content["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "final_preflight_manifest_created": True,
        "freeze_boundary_created": True,
        "rollback_boundary_created": True,
        "abort_conditions_created": True,
        "next_approval_gate_handoff_created": True,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
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
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_9": len(errors) == 0,
        "recommended_next_action": "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION" if len(errors) == 0 else "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-9", "LS-MON-2"],
        "errors": list(errors),
    }

    freeze_boundary = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_FREEZE_BOUNDARY",
        "status": "LSNEW8_FREEZE_BOUNDARY_READY_NO_EXECUTION",
        "freeze_required_before_later_execution": True,
        "freeze_scope": [
            "LS-NEW-6 WP draft payload prep",
            "LS-NEW-7 runner prep manifest",
            "LS-NEW-7 safety contract",
            "LS-NEW-8 final preflight manifest",
        ],
        "frozen_in_current_phase": False,
        "freeze_execution_allowed": False,
        "execution_allowed": False,
    }

    rollback_boundary = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_ROLLBACK_BOUNDARY",
        "status": "LSNEW8_ROLLBACK_BOUNDARY_READY_NO_EXECUTION",
        "rollback_required_before_later_execution": True,
        "rollback_scope": [
            "If a later draft creation succeeds, rollback means moving the created draft to trash or reverting to draft-hold according to later approved policy.",
            "No rollback action is executed in LS-NEW-8 because no WordPress draft exists yet.",
        ],
        "target_post_id": None,
        "rollback_executed": False,
        "execution_allowed": False,
    }

    abort_conditions = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_ABORT_CONDITIONS",
        "status": "LSNEW8_ABORT_CONDITIONS_READY_NO_EXECUTION",
        "abort_if_any_true": [
            "LS-NEW-7 validation is not valid",
            "target_post_id is not null before draft creation",
            "target_post_id_allocated is true before draft creation",
            "execution_allowed is true in any pre-execution artifact",
            "runner_execution_allowed is true before explicit execution approval",
            "credential.env was read before later approved credential phase",
            "WordPress API was called before later approved execution phase",
            "post_id=119 update is attempted",
            "post_id=183 update is attempted",
            "approval label is consumed before execution gate",
            "external fetch is attempted",
        ],
        "abort_triggered": False,
        "execution_allowed": False,
    }

    handoff = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_NEXT_APPROVAL_GATE_HANDOFF",
        "status": "LSNEW8_NEXT_APPROVAL_GATE_HANDOFF_READY_NO_EXECUTION",
        "next_phase": "LS-NEW-9",
        "next_phase_name": "Separate Execution Approval Gate",
        "required_future_approval_label": "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
        "handoff_ready": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_draft_create_allowed": False,
        "credential_env_read_allowed": False,
    }

    result = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_RESULT",
        "status": READY if len(errors) == 0 else FAILED,
        "execution_mode": "WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY",
        "ls_new7_validated": len(errors) == 0,
        "final_preflight_manifest_created": len(errors) == 0,
        "freeze_boundary_created": len(errors) == 0,
        "rollback_boundary_created": len(errors) == 0,
        "abort_conditions_created": len(errors) == 0,
        "next_approval_gate_handoff_created": len(errors) == 0,
        "final_preflight_summary_created": len(errors) == 0,
        "content_item_id": content["content_item_id"],
        "title": content["title"],
        "volume": content["volume"],
        "author": content["author"],
        "publisher": content["publisher"],
        "release_date": content["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
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
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_label_consumed": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "abort_triggered": False,
        "handoff_ready": len(errors) == 0,
        "ready_for_ls_new_9": len(errors) == 0,
        "recommended_next_action": "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION" if len(errors) == 0 else "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-9", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if len(errors) == 0:
        write_json(Path(args.output_manifest), manifest)
        write_json(Path(args.output_freeze_boundary), freeze_boundary)
        write_json(Path(args.output_rollback_boundary), rollback_boundary)
        write_json(Path(args.output_abort_conditions), abort_conditions)
        write_json(Path(args.output_handoff), handoff)
        write_text(Path(args.output_summary), _summary_md())

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), _lock())
    _report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
