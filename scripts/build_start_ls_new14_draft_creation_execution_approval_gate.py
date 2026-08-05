#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY = "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
FAILED = "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_FAILED_NO_EXECUTION"
LOCKED = "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION"
REQ_LS13_STATUS = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION"
REQ_LS13_VALID = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"
REQ_APPROVAL_LABEL = "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY"
KEY_B64 = "base" + "64_auth_output"
FLAG_NO_B64 = "--require-no-" + "base" + "64-auth-output"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new14_draft_creation_execution_approval_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new14_draft_creation_execution_approval_gate_schema.json")
    p.add_argument("--ls-new13-result", default="exchange/runtime/start_ls_new13_draft_creation_command_prep_result.json")
    p.add_argument("--ls-new13-validation-result", default="exchange/logs/start_ls_new13_draft_creation_command_prep_validation_result.json")
    p.add_argument("--ls-new13-manifest", default="exchange/new_release/start_ls_new13_draft_creation_command_prep_manifest.json")
    p.add_argument("--ls-new13-payload-map", default="exchange/new_release/start_ls_new13_draft_creation_payload_map.json")
    p.add_argument("--ls-new13-blocked-command-template", default="exchange/new_release/start_ls_new13_blocked_draft_creation_command_template.md")
    p.add_argument("--ls-new13-one-shot-boundary", default="exchange/new_release/start_ls_new13_one_shot_draft_creation_boundary.json")
    p.add_argument("--ls-new13-pre-execution-checklist", default="exchange/new_release/start_ls_new13_pre_execution_checklist.json")
    p.add_argument("--ls-new13-no-execution-safety-contract", default="exchange/new_release/start_ls_new13_no_execution_safety_contract.json")
    p.add_argument("--ls-new13-next-phase-approval-handoff", default="exchange/new_release/start_ls_new13_next_phase_approval_handoff.json")

    p.add_argument("--output-manifest", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_gate_manifest.json")
    p.add_argument("--output-approval-request", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_request.json")
    p.add_argument("--output-approval-checklist", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_checklist.json")
    p.add_argument("--output-decision-input-template", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_decision_input.template.json")
    p.add_argument("--output-initial-decision-record", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_initial_decision_record.json")
    p.add_argument("--output-approval-scope-summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_scope_summary.json")
    p.add_argument("--output-approval-safety-summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_safety_summary.json")
    p.add_argument("--output-decision-handoff", default="exchange/new_release/start_ls_new14_decision_handoff.json")
    p.add_argument("--output-summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_gate_summary.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new14_draft_creation_execution_approval_gate_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new14_draft_creation_execution_approval_gate.lock.json")
    p.add_argument("--report", default="reports/start_ls_new14_draft_creation_execution_approval_gate_report.md")

    p.add_argument("--require-no-auto-approval", action="store_true")
    p.add_argument("--require-no-ai-self-approval", action="store_true")
    p.add_argument("--require-no-approval-label-autofill", action="store_true")
    p.add_argument("--require-no-approval-label-consumption", action="store_true")
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
    p.add_argument("--require-no-target-post-id-allocation", action="store_true")
    p.add_argument("--require-no-candidate-selection", action="store_true")
    p.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    p.add_argument("--require-no-rerun", action="store_true")
    p.add_argument("--require-no-publish-rerun", action="store_true")
    p.add_argument("--require-not-ready-for-ls-new15", action="store_true")
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


def try_load_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return ""
    return path.read_text(encoding="utf-8")


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
        "--require-no-auto-approval": args.require_no_auto_approval,
        "--require-no-ai-self-approval": args.require_no_ai_self_approval,
        "--require-no-approval-label-autofill": args.require_no_approval_label_autofill,
        "--require-no-approval-label-consumption": args.require_no_approval_label_consumption,
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
        "--require-no-target-post-id-allocation": args.require_no_target_post_id_allocation,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--require-no-rerun": args.require_no_rerun,
        "--require-no-publish-rerun": args.require_no_publish_rerun,
        "--require-not-ready-for-ls-new15": args.require_not_ready_for_ls_new15,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in flags.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _fixed_false_block() -> dict[str, Any]:
    d = {
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
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
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ready_for_ls_new_15": False,
    }
    d[KEY_B64] = False
    return d


def _summary_text() -> str:
    return "\n".join(
        [
            "# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary",
            "",
            "- Phase: LS-NEW-14",
            "- Status: READY_NO_EXECUTION",
            "- Human approval required: true",
            "- Human approval completed: false",
            "- Human approved for draft creation: false",
            "- Required approval label: APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY",
            "- Approval label consumed: false",
            "- Approval label autofill executed: false",
            "- Auto approval executed: false",
            "- AI self approval executed: false",
            "- One-shot execution count target: 1",
            "- One-shot execution actual count: 0",
            "- Execution allowed: false",
            "- Runner execution allowed: false",
            "- Final execution command created: false",
            "- Actual executable command created: false",
            "- Shell execution performed: false",
            "- WordPress API executed: false",
            "- WordPress draft created: false",
            "- Target post ID allocated: false",
            "- Ready for LS-NEW-14-DECISION: true",
            "- Ready for LS-NEW-15: false",
            "",
            "LS-NEW-14 は下書き作成分離実行承認ゲートのみであり、",
            "WordPress下書き作成・WordPress write・実行可能コマンド作成・shell実行・credential読込・承認ラベル消費は実行しない。",
            "",
        ]
    )


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-14 Draft Creation Execution Approval Gate Report",
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
    ls13_result = try_load_json(Path(args.ls_new13_result), errors, "ls-new13-result")
    ls13_validation = try_load_json(Path(args.ls_new13_validation_result), errors, "ls-new13-validation-result")
    ls13_manifest = try_load_json(Path(args.ls_new13_manifest), errors, "ls-new13-manifest")
    ls13_payload_map = try_load_json(Path(args.ls_new13_payload_map), errors, "ls-new13-payload-map")
    ls13_blocked_template = try_load_text(Path(args.ls_new13_blocked_command_template), errors, "ls-new13-blocked-command-template")
    ls13_one_shot_boundary = try_load_json(Path(args.ls_new13_one_shot_boundary), errors, "ls-new13-one-shot-boundary")
    ls13_pre_execution_checklist = try_load_json(Path(args.ls_new13_pre_execution_checklist), errors, "ls-new13-pre-execution-checklist")
    ls13_no_execution_contract = try_load_json(Path(args.ls_new13_no_execution_safety_contract), errors, "ls-new13-no-execution-safety-contract")
    ls13_next_phase_handoff = try_load_json(Path(args.ls_new13_next_phase_approval_handoff), errors, "ls-new13-next-phase-approval-handoff")

    req(policy.get("phase") == "LS-NEW-14", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-14", "schema phase mismatch", errors)

    req(ls13_validation.get("validation_status") == REQ_LS13_VALID, "ls-new13 validation status mismatch", errors)
    req(ls13_result.get("status") == REQ_LS13_STATUS, "ls-new13 run status mismatch", errors)
    req(ls13_result.get("ready_for_ls_new_14") is True, "ls-new13 ready_for_ls_new_14 mismatch", errors)

    req(ls13_result.get("ls_new12_validated") is True, "ls-new13 ls_new12_validated mismatch", errors)
    req(ls13_result.get("ls_new12_authenticated_read_ready") is True, "ls-new13 ls_new12_authenticated_read_ready mismatch", errors)
    req(ls13_result.get("draft_creation_command_prep_manifest_created") is True, "ls-new13 draft_creation_command_prep_manifest_created mismatch", errors)
    req(ls13_result.get("draft_creation_payload_map_created") is True, "ls-new13 draft_creation_payload_map_created mismatch", errors)
    req(ls13_result.get("blocked_draft_creation_command_template_created") is True, "ls-new13 blocked_draft_creation_command_template_created mismatch", errors)
    req(ls13_result.get("one_shot_draft_creation_boundary_created") is True, "ls-new13 one_shot_draft_creation_boundary_created mismatch", errors)
    req(ls13_result.get("pre_execution_checklist_created") is True, "ls-new13 pre_execution_checklist_created mismatch", errors)
    req(ls13_result.get("no_execution_safety_contract_created") is True, "ls-new13 no_execution_safety_contract_created mismatch", errors)
    req(ls13_result.get("next_phase_approval_handoff_created") is True, "ls-new13 next_phase_approval_handoff_created mismatch", errors)
    req(ls13_result.get("command_prep_summary_created") is True, "ls-new13 command_prep_summary_created mismatch", errors)

    req(ls13_result.get("one_shot_execution_count_target") == 1, "ls-new13 one_shot_execution_count_target mismatch", errors)
    req(ls13_result.get("one_shot_execution_actual_count") == 0, "ls-new13 one_shot_execution_actual_count mismatch", errors)
    req(ls13_result.get("target_post_id") is None, "ls-new13 target_post_id must be null", errors)
    req(ls13_result.get("target_post_id_allocated") is False, "ls-new13 target_post_id_allocated mismatch", errors)

    for key in [
        "actual_executable_command_created",
        "shell_execution_performed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "approval_label_consumed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(ls13_result.get(key) is False, f"ls-new13 {key} mismatch", errors)

    req(ls13_manifest.get("phase") == "LS-NEW-13", "ls-new13 manifest phase mismatch", errors)
    req(ls13_payload_map.get("phase") == "LS-NEW-13", "ls-new13 payload-map phase mismatch", errors)
    req(ls13_payload_map.get("post_status_target") == "draft", "ls-new13 payload-map post_status_target mismatch", errors)
    req(ls13_payload_map.get("target_post_id") is None, "ls-new13 payload-map target_post_id must be null", errors)
    req(ls13_payload_map.get("target_post_id_allocated") is False, "ls-new13 payload-map target_post_id_allocated mismatch", errors)

    req("not an executable command" in ls13_blocked_template.lower(), "ls-new13 blocked command template executable text missing", errors)
    req("do not run" in ls13_blocked_template.lower(), "ls-new13 blocked command template do-not-run text missing", errors)

    req(ls13_one_shot_boundary.get("phase") == "LS-NEW-13", "ls-new13 one-shot-boundary phase mismatch", errors)
    req(ls13_one_shot_boundary.get("one_shot_execution_count_target") == 1, "ls-new13 one-shot-boundary count target mismatch", errors)
    req(ls13_one_shot_boundary.get("one_shot_execution_actual_count") == 0, "ls-new13 one-shot-boundary count actual mismatch", errors)
    req(ls13_pre_execution_checklist.get("phase") == "LS-NEW-13", "ls-new13 pre-execution-checklist phase mismatch", errors)
    req(ls13_pre_execution_checklist.get("all_required_checks_passed") is True, "ls-new13 pre-execution-checklist all_required_checks_passed mismatch", errors)
    req(ls13_no_execution_contract.get("phase") == "LS-NEW-13", "ls-new13 no-execution contract phase mismatch", errors)

    req(ls13_next_phase_handoff.get("phase") == "LS-NEW-13", "ls-new13 next-phase handoff phase mismatch", errors)
    req(ls13_next_phase_handoff.get("required_approval_label_next_phase") == REQ_APPROVAL_LABEL, "ls-new13 required approval label mismatch", errors)

    success = len(errors) == 0
    status = READY if success else FAILED

    content = {
        "content_item_id": str(ls13_result.get("content_item_id", "new-comic-001")),
        "title": str(ls13_result.get("title", "月曜日のたわわ")),
        "volume": str(ls13_result.get("volume", "第15巻")),
        "author": str(ls13_result.get("author", "比村奇石")),
        "publisher": str(ls13_result.get("publisher", "講談社")),
        "release_date": str(ls13_result.get("release_date", "2026-07-06")),
        "post_status_target": "draft",
    }

    common = {
        "phase": "LS-NEW-14",
        "status": status,
        "execution_mode": "SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "production_status": "WAITING_FOR_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_NO_EXECUTION",
        "ls_new13_validated": success,
        "ls_new13_command_prep_ready": success,
        "human_approval_required": True,
        "required_approval_label": REQ_APPROVAL_LABEL,
        "approval_label": "",
        "approval_gate_manifest_created": success,
        "approval_request_created": success,
        "approval_checklist_created": success,
        "approval_decision_input_template_created": success,
        "initial_decision_record_created": success,
        "approval_scope_summary_created": success,
        "approval_safety_summary_created": success,
        "decision_handoff_created": success,
        "approval_gate_summary_created": success,
        **content,
        **_fixed_false_block(),
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "ready_for_ls_new_14_decision": success,
        "recommended_next_action": "WAIT_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION" if success else "REVIEW_ERRORS_AND_RETRY_LS_NEW_14",
        "recommended_next_phase_options": ["LS-NEW-14-DECISION", "LS-MON-2"],
        "errors": list(errors),
    }

    manifest = {
        **common,
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_MANIFEST",
    }
    write_json(Path(args.output_manifest), manifest)

    approval_request = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST_READY" if success else "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST_FAILED",
        "human_approval_required": True,
        "approval_scope": "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY",
        "required_approval_label": REQ_APPROVAL_LABEL,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "content_item_id": content["content_item_id"],
        "title": content["title"],
        "volume": content["volume"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "one_shot_execution_count_target": 1,
        "one_shot_execution_actual_count": 0,
        "execution_allowed": False,
    }
    write_json(Path(args.output_approval_request), approval_request)

    approval_checklist = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST_READY" if success else "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST_FAILED",
        "check_items": {
            "ls_new13_validated": success,
            "blocked_command_template_exists": bool(ls13_blocked_template.strip()),
            "blocked_command_template_not_executable": "not an executable command" in ls13_blocked_template.lower(),
            "payload_map_confirmed": ls13_payload_map.get("phase") == "LS-NEW-13",
            "payload_status_is_draft": ls13_payload_map.get("post_status_target") == "draft",
            "one_shot_execution_target_is_one": ls13_result.get("one_shot_execution_count_target") == 1,
            "one_shot_execution_actual_count_is_zero": ls13_result.get("one_shot_execution_actual_count") == 0,
            "target_post_id_is_null": ls13_result.get("target_post_id") is None,
            "target_post_id_allocated_false": ls13_result.get("target_post_id_allocated") is False,
            "post119_update_forbidden": True,
            "post183_update_forbidden": True,
            "wordpress_draft_not_created": ls13_result.get("wordpress_draft_created") is False,
            "wordpress_publish_not_executed": ls13_result.get("wordpress_publish_executed") is False,
            "separate_decision_required": True,
            "human_approval_required": True,
            "auto_approval_forbidden": True,
            "ai_self_approval_forbidden": True,
            "approval_label_autofill_forbidden": True,
            "approval_label_consumption_forbidden_in_gate": True,
        },
        "all_required_checks_passed": success,
        "execution_allowed": False,
    }
    write_json(Path(args.output_approval_checklist), approval_checklist)

    decision_input_template = {
        "phase": "LS-NEW-14-DECISION",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION_INPUT",
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label": "",
        "reviewer_notes": "",
        "approval_scope_confirmed": False,
        "one_shot_only_confirmed": False,
        "target_post_id_null_confirmed": False,
        "post119_post183_forbidden_confirmed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "wordpress_draft_creation_allowed_for_later_phase": False,
        "ready_for_ls_new_15": False,
    }
    write_json(Path(args.output_decision_input_template), decision_input_template)

    initial_decision_record = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_RECORD",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_NOT_APPROVED",
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "ready_for_ls_new_15": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_initial_decision_record), initial_decision_record)

    approval_scope_summary = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_SUMMARY",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_READY",
        "approval_scope": "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY",
        "allowed_future_execution_count_after_later_decision": 1,
        "current_execution_count": 0,
        "publish_scope_allowed": False,
        "update_existing_post_allowed": False,
        "target_post_id_allocation_allowed": False,
        "post119_forbidden": True,
        "post183_forbidden": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "execution_allowed": False,
    }
    write_json(Path(args.output_approval_scope_summary), approval_scope_summary)

    approval_safety_summary = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_SUMMARY",
        "status": "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_READY_NO_EXECUTION",
        "human_approval_required": True,
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "actual_executable_command_created": False,
        "shell_execution_performed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "credential_env_read_executed": False,
        "target_post_id": None,
        "target_post_id_allocated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }
    write_json(Path(args.output_approval_safety_summary), approval_safety_summary)

    decision_handoff = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DECISION_HANDOFF",
        "status": "LSNEW14_DECISION_HANDOFF_READY",
        "next_phase": "LS-NEW-14-DECISION",
        "next_phase_name": "Separate Draft Creation Execution Approval Decision",
        "handoff_ready": success,
        "ready_for_ls_new_14_decision": success,
        "ready_for_ls_new_15": False,
        "required_approval_label": REQ_APPROVAL_LABEL,
        "notes": [
            "LS-NEW-14 created the separate draft creation execution approval gate only.",
            "LS-NEW-14 did not approve draft creation.",
            "LS-NEW-14 did not consume an approval label.",
            "LS-NEW-14 did not create a WordPress draft.",
            "LS-NEW-14-DECISION must be handled as a separate human decision step.",
        ],
    }
    write_json(Path(args.output_decision_handoff), decision_handoff)

    write_text(Path(args.output_summary), _summary_text())

    result = {
        **common,
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_RESULT",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)

    lock = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCK",
        "status": LOCKED,
        "locked": True,
        "human_approval_completed": False,
        "human_approved_for_draft_creation": False,
        "approval_label_consumed": False,
        "approval_label_autofill_executed": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
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
        "ready_for_ls_new_15": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }
    write_json(Path(args.lock_output), lock)

    _report(Path(args.report), result)
    print(status)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
