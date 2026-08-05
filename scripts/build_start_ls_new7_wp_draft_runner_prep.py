#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"
FAILED = "LSNEW7_WP_DRAFT_RUNNER_PREP_FAILED_NO_EXECUTION"
LOCKED = "LSNEW7_WP_DRAFT_RUNNER_PREP_LOCKED_NO_EXECUTION"
REQ_LS6_STATUS = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION"
REQ_LS6_VALID = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new7_wp_draft_runner_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new7_wp_draft_runner_prep_schema.json")
    p.add_argument("--ls-new6-payload", default="exchange/new_release/start_ls_new6_wp_draft_payload_prep.json")
    p.add_argument("--ls-new6-preview", default="exchange/new_release/start_ls_new6_wp_draft_payload_preview.md")
    p.add_argument("--ls-new6-safety-summary", default="exchange/new_release/start_ls_new6_wp_draft_payload_safety_summary.json")
    p.add_argument("--ls-new6-result", default="exchange/runtime/start_ls_new6_wp_draft_payload_prep_result.json")
    p.add_argument("--ls-new6-validation-result", default="exchange/logs/start_ls_new6_wp_draft_payload_prep_validation_result.json")
    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json")
    p.add_argument("--output-safety-contract", default="exchange/new_release/start_ls_new7_wp_draft_runner_safety_contract.json")
    p.add_argument("--output-preflight-checklist", default="exchange/new_release/start_ls_new7_wp_draft_runner_preflight_checklist.json")
    p.add_argument("--output-command-template", default="exchange/new_release/start_ls_new7_blocked_execution_command_template.md")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new7_wp_draft_runner_prep_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new7_wp_draft_runner_prep.lock.json")
    p.add_argument("--report", default="reports/start_ls_new7_wp_draft_runner_prep_report.md")

    p.add_argument("--require-no-runner-execution", action="store_true")
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


def _blocked_template() -> str:
    return "\n".join(
        [
            "# LS-NEW-7 Blocked Execution Command Template",
            "",
            "This is not an executable command.",
            "This file documents that execution is blocked in LS-NEW-7.",
            "",
            "- Phase: LS-NEW-7",
            "- Runner execution allowed: false",
            "- WordPress API allowed: false",
            "- WordPress draft creation allowed: false",
            "- Credential read allowed: false",
            "- Target post ID allocation allowed: false",
            "- Execution allowed: false",
            "",
            "Actual execution must not be attempted in LS-NEW-7.",
            "A later phase must create a separate approved execution command after final preflight.",
            "",
        ]
    )


def _summary_md() -> str:
    return "\n".join(
        [
            "# LS-NEW-7 WordPress Draft Runner Prep Summary",
            "",
            "- Phase: LS-NEW-7",
            "- Status: READY_NO_EXECUTION",
            "- Runner execution allowed: false",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Source payload: exchange/new_release/start_ls_new6_wp_draft_payload_prep.json",
            "",
        ]
    )


def _lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_LOCK",
        "status": LOCKED,
        "locked": True,
        "runner_execution_allowed": False,
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
        "# LS-NEW-7 WP Draft Runner Prep Report",
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
    ls6_payload = try_load_json(Path(args.ls_new6_payload), errors, "ls-new6-payload")
    _ = read_text(Path(args.ls_new6_preview), errors, "ls-new6-preview")
    ls6_safety = try_load_json(Path(args.ls_new6_safety_summary), errors, "ls-new6-safety-summary")
    ls6_result = try_load_json(Path(args.ls_new6_result), errors, "ls-new6-result")
    ls6_validation = try_load_json(Path(args.ls_new6_validation_result), errors, "ls-new6-validation-result")

    req(policy.get("phase") == "LS-NEW-7", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-7", "schema phase mismatch", errors)

    req(ls6_result.get("status") == REQ_LS6_STATUS, "ls-new6 run status mismatch", errors)
    req(ls6_validation.get("validation_status") == REQ_LS6_VALID, "ls-new6 validation status mismatch", errors)
    req(ls6_result.get("ready_for_ls_new_7") is True, "ls-new6 ready_for_ls_new_7 mismatch", errors)
    req(ls6_result.get("execution_allowed") is False, "ls-new6 execution_allowed mismatch", errors)
    req(ls6_result.get("wordpress_api_call_executed") is False, "ls-new6 wordpress_api_call_executed=true", errors)
    req(ls6_result.get("wordpress_write_executed") is False, "ls-new6 wordpress_write_executed=true", errors)
    req(ls6_result.get("wordpress_draft_created") is False, "ls-new6 wordpress_draft_created=true", errors)
    req(ls6_result.get("target_post_id_allocated") is False, "ls-new6 target_post_id_allocated=true", errors)
    req(ls6_safety.get("ready_for_ls_new_7") is True, "ls-new6 safety ready_for_ls_new_7 mismatch", errors)

    for key in [
        "content_item_id",
        "title",
        "volume",
        "author",
        "publisher",
        "release_date",
    ]:
        req(str(ls6_payload.get(key, "")).strip() != "", f"missing ls-new6 payload field: {key}", errors)

    manifest = {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_MANIFEST",
        "status": "LSNEW7_WP_DRAFT_RUNNER_PREP_MANIFEST_READY_NO_EXECUTION",
        "execution_mode": "WP_DRAFT_RUNNER_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_PREP_ONLY",
        "ls_new6_validated": len(errors) == 0,
        "source_payload": "exchange/new_release/start_ls_new6_wp_draft_payload_prep.json",
        "source_preview": "exchange/new_release/start_ls_new6_wp_draft_payload_preview.md",
        "source_safety_summary": "exchange/new_release/start_ls_new6_wp_draft_payload_safety_summary.json",
        "content_item_id": str(ls6_payload.get("content_item_id", "")),
        "title": str(ls6_payload.get("title", "")),
        "volume": str(ls6_payload.get("volume", "")),
        "author": str(ls6_payload.get("author", "")),
        "publisher": str(ls6_payload.get("publisher", "")),
        "release_date": str(ls6_payload.get("release_date", "")),
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "runner_prep_manifest_created": True,
        "runner_safety_contract_created": True,
        "runner_preflight_checklist_created": True,
        "blocked_execution_command_template_created": True,
        "runner_execution_allowed": False,
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
        "ready_for_ls_new_8": len(errors) == 0,
        "recommended_next_action": "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION" if len(errors) == 0 else "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-8", "LS-MON-2"],
        "errors": list(errors),
    }

    safety_contract = {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT",
        "status": "LSNEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT_READY_NO_EXECUTION",
        "runner_execution_allowed": False,
        "blocked_until_explicit_approval": True,
        "separate_execution_command_required": True,
        "final_preflight_required": True,
        "human_approval_required_before_any_wp_call": True,
        "wordpress_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "wordpress_draft_create_allowed": False,
        "credential_env_read_allowed": False,
        "target_post_id_allocation_allowed": False,
        "approval_label_consumption_allowed": False,
        "execution_allowed": False,
        "always_forbidden": [
            "post_id=119 update",
            "post_id=183 update",
            "secret output",
            "credential.env read in LS-NEW-7",
            "WordPress API call in LS-NEW-7",
            "WordPress draft creation in LS-NEW-7",
            "X post in LS-NEW-7",
            "external fetch in LS-NEW-7",
        ],
    }

    preflight = {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREFLIGHT_CHECKLIST",
        "status": "LSNEW7_PREFLIGHT_CHECKLIST_READY_NO_EXECUTION",
        "required_before_later_execution": [
            "LS-NEW-6 payload validation remains valid",
            "human approval remains valid",
            "final preflight completed in later phase",
            "credential readiness checked only in later approved phase",
            "target post ID remains unallocated until actual draft creation phase",
            "separate execution command approved in later phase",
            "rollback/freeze boundary prepared in later phase",
        ],
        "current_phase_checks": {
            "runner_execution_allowed": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_created": False,
            "credential_env_read_executed": False,
            "target_post_id_allocated": False,
            "execution_allowed": False,
        },
    }

    result = {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_RESULT",
        "status": READY if len(errors) == 0 else FAILED,
        "execution_mode": "WP_DRAFT_RUNNER_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_RUNNER_PREP_ONLY",
        "ls_new6_validated": len(errors) == 0,
        "runner_prep_manifest_created": len(errors) == 0,
        "runner_safety_contract_created": len(errors) == 0,
        "runner_preflight_checklist_created": len(errors) == 0,
        "blocked_execution_command_template_created": len(errors) == 0,
        "runner_prep_summary_created": len(errors) == 0,
        "content_item_id": manifest["content_item_id"],
        "title": manifest["title"],
        "volume": manifest["volume"],
        "author": manifest["author"],
        "publisher": manifest["publisher"],
        "release_date": manifest["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "runner_execution_allowed": False,
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
        "ready_for_ls_new_8": len(errors) == 0,
        "recommended_next_action": "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION" if len(errors) == 0 else "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-8", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if len(errors) == 0:
        write_json(Path(args.output_manifest), manifest)
        write_json(Path(args.output_safety_contract), safety_contract)
        write_json(Path(args.output_preflight_checklist), preflight)
        write_text(Path(args.output_command_template), _blocked_template())
        write_text(Path(args.output_summary), _summary_md())

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), _lock())
    _report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
