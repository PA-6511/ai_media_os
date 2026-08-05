#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW10_EXECUTION_PREP_READY_NO_DRAFT_CREATION"
FAILED = "LSNEW10_EXECUTION_PREP_FAILED_NO_DRAFT_CREATION"
LOCKED = "LSNEW10_EXECUTION_PREP_LOCKED_NO_DRAFT_CREATION"
REQ_LS9_STATUS = "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"
REQ_LS9_VALID = "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"
REQ_NEXT_ACTION = "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new10_execution_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new10_execution_prep_schema.json")
    p.add_argument("--ls-new9-decision-result", default="exchange/runtime/start_ls_new9_decision_result.json")
    p.add_argument("--ls-new9-decision-validation-result", default="exchange/logs/start_ls_new9_decision_validation_result.json")
    p.add_argument("--ls-new9-decision-record", default="exchange/new_release/start_ls_new9_decision_result_record.json")
    p.add_argument("--ls-new6-payload", default="exchange/new_release/start_ls_new6_wp_draft_payload_prep.json")
    p.add_argument("--ls-new7-runner-prep-manifest", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json")
    p.add_argument("--ls-new8-final-preflight-manifest", default="exchange/new_release/start_ls_new8_final_preflight_manifest.json")
    p.add_argument("--ls-new8-freeze-boundary", default="exchange/new_release/start_ls_new8_freeze_boundary.json")
    p.add_argument("--ls-new8-rollback-boundary", default="exchange/new_release/start_ls_new8_rollback_boundary.json")
    p.add_argument("--ls-new8-abort-conditions", default="exchange/new_release/start_ls_new8_abort_conditions.json")
    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new10_execution_prep_manifest.json")
    p.add_argument("--output-input-map", default="exchange/new_release/start_ls_new10_execution_input_map.json")
    p.add_argument("--output-dry-boundary", default="exchange/new_release/start_ls_new10_draft_creation_dry_boundary.json")
    p.add_argument("--output-credential-handoff", default="exchange/new_release/start_ls_new10_credential_preflight_handoff_request.json")
    p.add_argument("--output-blocked-command-template", default="exchange/new_release/start_ls_new10_blocked_execution_command_template.md")
    p.add_argument("--output-safety-summary", default="exchange/new_release/start_ls_new10_execution_prep_safety_summary.json")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new10_execution_prep_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new10_execution_prep_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new10_execution_prep.lock.json")
    p.add_argument("--report", default="reports/start_ls_new10_execution_prep_report.md")

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


def _fixed_false_block() -> dict[str, Any]:
    return {
        "execution_allowed": False,
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
        "target_post_id": None,
        "target_post_id_allocated": False,
    }


def _build_blocked_template() -> str:
    return "\n".join(
        [
            "# LS-NEW-10 Blocked Execution Command Template",
            "",
            "This is not an executable command.",
            "This file documents that execution is still blocked in LS-NEW-10.",
            "",
            "- Phase: LS-NEW-10",
            "- Execution allowed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API allowed: false",
            "- WordPress draft creation allowed: false",
            "- Credential read allowed: false",
            "- Credential existence check allowed: false",
            "- Target post ID allocation allowed: false",
            "",
            "Actual WordPress draft creation must not be attempted in LS-NEW-10.",
            "A later phase must perform credential / WP connectivity preflight first.",
            "",
        ]
    )


def _build_summary() -> str:
    return "\n".join(
        [
            "# LS-NEW-10 Execution Prep Summary",
            "",
            "- Phase: LS-NEW-10",
            "- Status: READY_NO_DRAFT_CREATION",
            "- LS-NEW-9 decision approved: true",
            "- Execution allowed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Credential existence check executed: false",
            "- Target post ID allocated: false",
            "- Ready for LS-NEW-11: true",
            "",
            "LS-NEW-10 は実行系準備のみであり、WordPress下書き作成・credential読込・WordPress API呼び出しは実行しない。",
            "",
        ]
    )


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-10 Execution Prep Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- ready_for_ls_new_11: {result.get('ready_for_ls_new_11', False)}",
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
    ls9_result = try_load_json(Path(args.ls_new9_decision_result), errors, "ls-new9-decision-result")
    ls9_validation = try_load_json(Path(args.ls_new9_decision_validation_result), errors, "ls-new9-decision-validation-result")
    ls9_record = try_load_json(Path(args.ls_new9_decision_record), errors, "ls-new9-decision-record")
    ls6_payload = try_load_json(Path(args.ls_new6_payload), errors, "ls-new6-payload")
    ls7_runner = try_load_json(Path(args.ls_new7_runner_prep_manifest), errors, "ls-new7-runner-prep-manifest")
    ls8_final = try_load_json(Path(args.ls_new8_final_preflight_manifest), errors, "ls-new8-final-preflight-manifest")
    _ = try_load_json(Path(args.ls_new8_freeze_boundary), errors, "ls-new8-freeze-boundary")
    _ = try_load_json(Path(args.ls_new8_rollback_boundary), errors, "ls-new8-rollback-boundary")
    _ = try_load_json(Path(args.ls_new8_abort_conditions), errors, "ls-new8-abort-conditions")

    req(policy.get("phase") == "LS-NEW-10", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-10", "schema phase mismatch", errors)
    req(ls9_result.get("status") == REQ_LS9_STATUS, "ls-new9 decision status mismatch", errors)
    req(ls9_validation.get("validation_status") == REQ_LS9_VALID, "ls-new9 decision validation status mismatch", errors)
    req(ls9_record.get("status") == REQ_LS9_STATUS, "ls-new9 decision record status mismatch", errors)
    req(ls9_result.get("ready_for_ls_new_10") is True, "ls-new9 ready_for_ls_new_10 mismatch", errors)
    req(ls9_result.get("recommended_next_action") == REQ_NEXT_ACTION, "ls-new9 recommended_next_action mismatch", errors)
    req(ls9_result.get("execution_allowed") is False, "ls-new9 execution_allowed mismatch", errors)
    req(ls9_result.get("runner_execution_allowed") is False, "ls-new9 runner_execution_allowed mismatch", errors)
    req(ls9_result.get("final_execution_command_created") is False, "ls-new9 final_execution_command_created mismatch", errors)
    req(ls9_result.get("approval_label_consumed") is False, "ls-new9 approval_label_consumed mismatch", errors)
    req(ls9_result.get("target_post_id") is None, "ls-new9 target_post_id must be null", errors)
    req(ls9_result.get("target_post_id_allocated") is False, "ls-new9 target_post_id_allocated mismatch", errors)
    req(ls9_result.get("wordpress_api_call_executed") is False, "ls-new9 wordpress_api_call_executed=true", errors)
    req(ls9_result.get("wordpress_draft_created") is False, "ls-new9 wordpress_draft_created=true", errors)
    req(ls9_result.get("credential_env_read_executed") is False, "ls-new9 credential_env_read_executed=true", errors)
    req(ls9_result.get("credential_existence_check_executed") is False, "ls-new9 credential_existence_check_executed=true", errors)

    req(ls6_payload.get("phase") == "LS-NEW-6", "ls-new6 payload phase mismatch", errors)
    req(ls7_runner.get("phase") == "LS-NEW-7", "ls-new7 runner phase mismatch", errors)
    req(ls8_final.get("phase") == "LS-NEW-8", "ls-new8 final preflight phase mismatch", errors)

    content = {
        "content_item_id": str(ls6_payload.get("content_item_id", "new-comic-001")),
        "title": str(ls6_payload.get("title", "月曜日のたわわ")),
        "volume": str(ls6_payload.get("volume", "第15巻")),
        "author": str(ls6_payload.get("author", "比村奇石")),
        "publisher": str(ls6_payload.get("publisher", "講談社")),
        "release_date": str(ls6_payload.get("release_date", "2026-07-06")),
        "post_status_target": "draft",
    }

    success = len(errors) == 0
    status = READY if success else FAILED
    ready_for_ls_new_11 = success

    common = {
        "phase": "LS-NEW-10",
        "status": status,
        "execution_mode": "EXECUTION_PREP_ONLY_NO_DRAFT_CREATION",
        "production_status": "NO_EXECUTION_EXECUTION_PREP_ONLY",
        "ls_new9_decision_validated": success,
        "ls_new9_decision_approved": success,
        **content,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_prep_manifest_created": success,
        "execution_input_map_created": success,
        "draft_creation_dry_boundary_created": success,
        "credential_preflight_handoff_request_created": success,
        "blocked_execution_command_template_created": success,
        "execution_prep_safety_summary_created": success,
        "execution_prep_summary_created": success,
        **_fixed_false_block(),
        "ready_for_ls_new_11": ready_for_ls_new_11,
        "recommended_next_action": "BEGIN_LS_NEW_11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE" if success else "REVIEW_ERRORS_AND_RETRY_LS_NEW_10",
        "recommended_next_phase_options": ["LS-NEW-11", "LS-MON-2"],
        "errors": list(errors),
    }

    manifest = {
        **common,
        "document_type": "START_LS_NEW10_EXECUTION_PREP_MANIFEST",
        "source_decision_result": args.ls_new9_decision_result,
        "source_decision_record": args.ls_new9_decision_record,
        "source_payload": args.ls_new6_payload,
        "source_runner_prep": args.ls_new7_runner_prep_manifest,
        "source_final_preflight": args.ls_new8_final_preflight_manifest,
    }
    write_json(Path(args.output_manifest), manifest)

    input_map = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_INPUT_MAP",
        "status": "LSNEW10_EXECUTION_INPUT_MAP_READY_NO_DRAFT_CREATION" if success else "LSNEW10_EXECUTION_INPUT_MAP_FAILED_NO_DRAFT_CREATION",
        "payload_source": args.ls_new6_payload,
        "runner_prep_source": args.ls_new7_runner_prep_manifest,
        "final_preflight_source": args.ls_new8_final_preflight_manifest,
        "decision_source": args.ls_new9_decision_result,
        "credential_source": None,
        "credential_env_path_recorded": False,
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_input_map), input_map)

    dry_boundary = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_DRAFT_CREATION_DRY_BOUNDARY",
        "status": "LSNEW10_DRAFT_CREATION_DRY_BOUNDARY_READY_NO_DRAFT_CREATION" if success else "LSNEW10_DRAFT_CREATION_DRY_BOUNDARY_FAILED_NO_DRAFT_CREATION",
        "draft_creation_planned_for_later_phase": True,
        "draft_creation_executed_in_current_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_draft_created": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "execution_allowed": False,
        "required_before_later_draft_creation": [
            "LS-NEW-11 credential and WP connectivity preflight must pass",
            "A later separate execution command must be created",
            "target_post_id must remain null before creation",
            "post119/post183 update must remain forbidden",
            "rollback/freeze boundary must remain available",
        ],
    }
    write_json(Path(args.output_dry_boundary), dry_boundary)

    credential_handoff = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST",
        "status": "LSNEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST_READY_NO_CREDENTIAL_READ" if success else "LSNEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST_FAILED_NO_CREDENTIAL_READ",
        "next_phase": "LS-NEW-11",
        "next_phase_name": "Credential and WordPress Connectivity Preflight",
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "execution_allowed": False,
        "handoff_ready": ready_for_ls_new_11,
        "notes": [
            "LS-NEW-10 does not read credential.env.",
            "Credential checks, if approved, must occur only in LS-NEW-11 or later.",
            "No WordPress write is allowed by this handoff.",
        ],
    }
    write_json(Path(args.output_credential_handoff), credential_handoff)

    write_text(Path(args.output_blocked_command_template), _build_blocked_template())

    safety_summary = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_SAFETY_SUMMARY",
        "status": "LSNEW10_EXECUTION_PREP_SAFETY_SUMMARY_READY_NO_DRAFT_CREATION" if success else "LSNEW10_EXECUTION_PREP_SAFETY_SUMMARY_FAILED_NO_DRAFT_CREATION",
        **_fixed_false_block(),
        "ready_for_ls_new_11": ready_for_ls_new_11,
    }
    write_json(Path(args.output_safety_summary), safety_summary)

    write_text(Path(args.output_summary), _build_summary())

    result = {
        **common,
        "document_type": "START_LS_NEW10_EXECUTION_PREP_RESULT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)

    lock = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_LOCK",
        "status": LOCKED,
        "locked": True,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
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
    write_json(Path(args.lock_output), lock)

    _report(Path(args.report), result)
    print(status)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())