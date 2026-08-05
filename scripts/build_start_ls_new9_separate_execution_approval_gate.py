#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
FAILED = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_FAILED_NO_EXECUTION"
LOCKED = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION"
REQ_LS8_STATUS = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION"
REQ_LS8_VALID = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new9_separate_execution_approval_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new9_separate_execution_approval_gate_schema.json")
    p.add_argument("--ls-new8-manifest", default="exchange/new_release/start_ls_new8_final_preflight_manifest.json")
    p.add_argument("--ls-new8-freeze-boundary", default="exchange/new_release/start_ls_new8_freeze_boundary.json")
    p.add_argument("--ls-new8-rollback-boundary", default="exchange/new_release/start_ls_new8_rollback_boundary.json")
    p.add_argument("--ls-new8-abort-conditions", default="exchange/new_release/start_ls_new8_abort_conditions.json")
    p.add_argument("--ls-new8-handoff", default="exchange/new_release/start_ls_new8_next_approval_gate_handoff.json")
    p.add_argument("--ls-new8-summary", default="exchange/new_release/start_ls_new8_final_preflight_summary.md")
    p.add_argument("--ls-new8-result", default="exchange/runtime/start_ls_new8_wp_draft_runner_final_preflight_result.json")
    p.add_argument("--ls-new8-validation-result", default="exchange/logs/start_ls_new8_wp_draft_runner_final_preflight_validation_result.json")
    p.add_argument("--output-request", default="exchange/new_release/start_ls_new9_separate_execution_approval_request.json")
    p.add_argument("--output-checklist-template", default="exchange/new_release/start_ls_new9_separate_execution_approval_checklist.template.json")
    p.add_argument("--output-decision-template", default="exchange/new_release/start_ls_new9_separate_execution_approval_decision.template.json")
    p.add_argument("--output-decision-record", default="exchange/new_release/start_ls_new9_separate_execution_approval_decision.json")
    p.add_argument("--output-scope-summary", default="exchange/new_release/start_ls_new9_approval_scope_summary.md")
    p.add_argument("--output-safety-summary", default="exchange/new_release/start_ls_new9_approval_gate_safety_summary.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new9_separate_execution_approval_gate_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new9_separate_execution_approval_gate.lock.json")
    p.add_argument("--report", default="reports/start_ls_new9_separate_execution_approval_gate_report.md")

    p.add_argument("--require-no-auto-approval", action="store_true")
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
        "--require-no-auto-approval": args.require_no_auto_approval,
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
            "# LS-NEW-9 Separate Execution Approval Gate Scope Summary",
            "",
            "- Phase: LS-NEW-9",
            "- Status: WAITING_FOR_SEPARATE_EXECUTION_APPROVAL",
            "- Human approval required: true",
            "- Human approval completed: false",
            "- Human approved for execution: false",
            "- Required approval label: APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY",
            "- Approval label consumed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- WordPress API executed: false",
            "- WordPress draft created: false",
            "- Credential read executed: false",
            "- Credential existence check executed: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "",
            "この承認ゲートは、次段の実行準備フェーズへ進むための判断ゲートであり、",
            "LS-NEW-9 自体では WordPress API / credential.env / draft creation を許可しない。",
            "",
        ]
    )


def _lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCK",
        "status": LOCKED,
        "locked": True,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label_consumed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "execution_allowed": False,
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
        "# LS-NEW-9 Separate Execution Approval Gate Report",
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
    ls8_manifest = try_load_json(Path(args.ls_new8_manifest), errors, "ls-new8-manifest")
    ls8_freeze = try_load_json(Path(args.ls_new8_freeze_boundary), errors, "ls-new8-freeze-boundary")
    ls8_rollback = try_load_json(Path(args.ls_new8_rollback_boundary), errors, "ls-new8-rollback-boundary")
    ls8_abort = try_load_json(Path(args.ls_new8_abort_conditions), errors, "ls-new8-abort-conditions")
    ls8_handoff = try_load_json(Path(args.ls_new8_handoff), errors, "ls-new8-handoff")
    _ = read_text(Path(args.ls_new8_summary), errors, "ls-new8-summary")
    ls8_result = try_load_json(Path(args.ls_new8_result), errors, "ls-new8-result")
    ls8_validation = try_load_json(Path(args.ls_new8_validation_result), errors, "ls-new8-validation-result")

    req(policy.get("phase") == "LS-NEW-9", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-9", "schema phase mismatch", errors)

    req(ls8_result.get("status") == REQ_LS8_STATUS, "ls-new8 run status mismatch", errors)
    req(ls8_validation.get("validation_status") == REQ_LS8_VALID, "ls-new8 validation status mismatch", errors)
    req(ls8_result.get("ready_for_ls_new_9") is True, "ls-new8 ready_for_ls_new_9 mismatch", errors)
    req(ls8_result.get("handoff_ready") is True, "ls-new8 handoff_ready mismatch", errors)
    req(ls8_result.get("abort_triggered") is False, "ls-new8 abort_triggered mismatch", errors)
    req(ls8_result.get("execution_allowed") is False, "ls-new8 execution_allowed mismatch", errors)
    req(ls8_result.get("runner_execution_allowed") is False, "ls-new8 runner_execution_allowed mismatch", errors)
    req(ls8_result.get("final_execution_command_created") is False, "ls-new8 final_execution_command_created mismatch", errors)
    req(ls8_result.get("target_post_id_allocated") is False, "ls-new8 target_post_id_allocated=true", errors)
    req(ls8_result.get("credential_env_read_executed") is False, "ls-new8 credential_env_read_executed=true", errors)
    req(ls8_result.get("credential_existence_check_executed") is False, "ls-new8 credential_existence_check_executed=true", errors)
    req(ls8_result.get("wordpress_api_call_executed") is False, "ls-new8 wordpress_api_call_executed=true", errors)
    req(ls8_result.get("wordpress_draft_created") is False, "ls-new8 wordpress_draft_created=true", errors)

    req(ls8_manifest.get("status") == "LSNEW8_FINAL_PREFLIGHT_MANIFEST_READY_NO_EXECUTION", "ls-new8 manifest status mismatch", errors)
    req(ls8_freeze.get("status") == "LSNEW8_FREEZE_BOUNDARY_READY_NO_EXECUTION", "ls-new8 freeze status mismatch", errors)
    req(ls8_rollback.get("status") == "LSNEW8_ROLLBACK_BOUNDARY_READY_NO_EXECUTION", "ls-new8 rollback status mismatch", errors)
    req(ls8_abort.get("status") == "LSNEW8_ABORT_CONDITIONS_READY_NO_EXECUTION", "ls-new8 abort status mismatch", errors)
    req(ls8_handoff.get("status") == "LSNEW8_NEXT_APPROVAL_GATE_HANDOFF_READY_NO_EXECUTION", "ls-new8 handoff status mismatch", errors)

    content = {
        "content_item_id": str(ls8_manifest.get("content_item_id", "")),
        "title": str(ls8_manifest.get("title", "")),
        "volume": str(ls8_manifest.get("volume", "")),
        "author": str(ls8_manifest.get("author", "")),
        "publisher": str(ls8_manifest.get("publisher", "")),
        "release_date": str(ls8_manifest.get("release_date", "")),
    }
    for key, value in content.items():
        req(value.strip() != "", f"missing ls-new8 manifest field: {key}", errors)

    request = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST_CREATED_NO_EXECUTION",
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_GATE_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new8_validated": len(errors) == 0,
        "content_item_id": content["content_item_id"],
        "title": content["title"],
        "volume": content["volume"],
        "author": content["author"],
        "publisher": content["publisher"],
        "release_date": content["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "required_approval_label": REQ_LABEL,
        "approval_label": "",
        "approval_label_consumed": False,
        "request_scope": [
            "Approve moving to the next no-execution execution-prep phase only",
            "Do not approve WordPress API call in LS-NEW-9",
            "Do not approve credential.env read in LS-NEW-9",
            "Do not approve WordPress draft creation in LS-NEW-9",
        ],
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
    }

    checklist_template = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_CHECKLIST_TEMPLATE",
        "candidate_review": {
            "content_item_id_checked": False,
            "title_checked": False,
            "volume_checked": False,
            "author_checked": False,
            "publisher_checked": False,
            "release_date_checked": False,
            "post_status_target_checked": False,
        },
        "preflight_review": {
            "ls_new8_validated_checked": False,
            "freeze_boundary_checked": False,
            "rollback_boundary_checked": False,
            "abort_conditions_checked": False,
            "handoff_ready_checked": False,
            "abort_triggered_false_checked": False,
        },
        "safety_review": {
            "runner_execution_not_allowed_checked": False,
            "final_execution_command_not_created_checked": False,
            "wordpress_api_not_executed_checked": False,
            "wordpress_draft_not_created_checked": False,
            "credential_env_not_read_checked": False,
            "credential_existence_not_checked": False,
            "target_post_id_not_allocated_checked": False,
            "post119_not_updated_checked": False,
            "post183_not_updated_checked": False,
            "secret_not_output_checked": False,
        },
        "human_decision": {
            "human_approval_completed": False,
            "human_approved_for_execution": False,
            "approval_label": "",
            "reviewer_notes": "",
        },
    }

    decision_template = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_TEMPLATE",
        "instructions": "Human reviewer must fill this manually. AI must not auto-approve.",
        "allowed_approval_label": REQ_LABEL,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
    }

    decision_record = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORD",
        "status": "LSNEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION",
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "reviewer_notes": "",
        "ready_for_ls_new_9_decision": True,
        "ready_for_ls_new_10": False,
        "execution_allowed": False,
    }

    safety_summary = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_APPROVAL_GATE_SAFETY_SUMMARY",
        "status": "LSNEW9_APPROVAL_GATE_SAFETY_SUMMARY_READY_NO_EXECUTION",
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
        "approval_label_consumed": False,
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
        "credential_env_read_executed": False,
        "credential_existence_check_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
    }

    result = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_RESULT",
        "status": READY if len(errors) == 0 else FAILED,
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_GATE_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new8_validated": len(errors) == 0,
        "approval_request_created": len(errors) == 0,
        "approval_checklist_template_created": len(errors) == 0,
        "approval_decision_template_created": len(errors) == 0,
        "approval_decision_record_created": len(errors) == 0,
        "approval_scope_summary_created": len(errors) == 0,
        "approval_gate_safety_summary_created": len(errors) == 0,
        "content_item_id": content["content_item_id"],
        "title": content["title"],
        "volume": content["volume"],
        "author": content["author"],
        "publisher": content["publisher"],
        "release_date": content["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_execution": False,
        "required_approval_label": REQ_LABEL,
        "approval_label": "",
        "approval_label_consumed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
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
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_9_decision": True,
        "ready_for_ls_new_10": False,
        "recommended_next_action": "WAIT_FOR_SEPARATE_EXECUTION_APPROVAL_DECISION",
        "recommended_next_phase_options": ["LS-NEW-9-DECISION", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if len(errors) == 0:
        write_json(Path(args.output_request), request)
        write_json(Path(args.output_checklist_template), checklist_template)
        write_json(Path(args.output_decision_template), decision_template)
        write_json(Path(args.output_decision_record), decision_record)
        write_text(Path(args.output_scope_summary), _summary_md())
        write_json(Path(args.output_safety_summary), safety_summary)

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), _lock())
    _report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
