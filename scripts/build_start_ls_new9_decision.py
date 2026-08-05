#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVED = "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION"
NOT_APPROVED = "LSNEW9_DECISION_NOT_APPROVED_NO_EXECUTION"
LOCKED = "LSNEW9_DECISION_LOCKED_NO_EXECUTION"
REQ_LS9_STATUS = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
REQ_LS9_VALID = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new9_decision_policy.json")
    p.add_argument("--schema", default="config/start_ls_new9_decision_schema.json")
    p.add_argument("--ls-new9-result", default="exchange/runtime/start_ls_new9_separate_execution_approval_gate_result.json")
    p.add_argument("--ls-new9-validation-result", default="exchange/logs/start_ls_new9_separate_execution_approval_gate_validation_result.json")
    p.add_argument("--ls-new9-approval-request", default="exchange/new_release/start_ls_new9_separate_execution_approval_request.json")
    p.add_argument("--ls-new9-decision-template", default="exchange/new_release/start_ls_new9_separate_execution_approval_decision.template.json")
    p.add_argument("--decision-input", default="exchange/new_release/start_ls_new9_decision_input.json")
    p.add_argument("--output-decision-record", default="exchange/new_release/start_ls_new9_decision_result_record.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new9_decision_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new9_decision.lock.json")
    p.add_argument("--report", default="reports/start_ls_new9_decision_report.md")

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


def _strict_bool(value: Any, warnings: list[str]) -> bool:
    if isinstance(value, bool):
        return value
    if "invalid_boolean_type" not in warnings:
        warnings.append("invalid_boolean_type")
    return False


def _lock() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_LOCK",
        "status": LOCKED,
        "locked": True,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
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
        "target_post_id_allocated": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-9-DECISION Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- validation_input: {result.get('ls_new9_validated', False)}",
        f"- ready_for_ls_new_10: {result.get('ready_for_ls_new_10', False)}",
        "",
        "## Warnings",
    ]
    warns = list(result.get("warnings", []))
    if warns:
        lines.extend(f"- {w}" for w in warns)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Errors")
    errs = list(result.get("errors", []))
    if errs:
        lines.extend(f"- {e}" for e in errs)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    _validate_flags(args, errors)

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    ls9_result = try_load_json(Path(args.ls_new9_result), errors, "ls-new9-result")
    ls9_validation = try_load_json(Path(args.ls_new9_validation_result), errors, "ls-new9-validation-result")
    _ = try_load_json(Path(args.ls_new9_approval_request), errors, "ls-new9-approval-request")
    _ = try_load_json(Path(args.ls_new9_decision_template), errors, "ls-new9-decision-template")
    decision_input = try_load_json(Path(args.decision_input), errors, "decision-input")

    req(policy.get("phase") == "LS-NEW-9-DECISION", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-9-DECISION", "schema phase mismatch", errors)
    req(ls9_result.get("status") == REQ_LS9_STATUS, "ls-new9 run status mismatch", errors)
    req(ls9_validation.get("validation_status") == REQ_LS9_VALID, "ls-new9 validation status mismatch", errors)
    req(ls9_result.get("ready_for_ls_new_9_decision") is True, "ls-new9 ready_for_ls_new_9_decision mismatch", errors)
    req(ls9_result.get("ready_for_ls_new_10") is False, "ls-new9 ready_for_ls_new_10 mismatch", errors)
    req(ls9_result.get("human_approval_required") is True, "ls-new9 human_approval_required mismatch", errors)
    req(ls9_result.get("human_approval_completed") is False, "ls-new9 human_approval_completed mismatch", errors)
    req(ls9_result.get("human_approved_for_execution") is False, "ls-new9 human_approved_for_execution mismatch", errors)
    req(ls9_result.get("execution_allowed") is False, "ls-new9 execution_allowed mismatch", errors)
    req(ls9_result.get("runner_execution_allowed") is False, "ls-new9 runner_execution_allowed mismatch", errors)
    req(ls9_result.get("final_execution_command_created") is False, "ls-new9 final_execution_command_created mismatch", errors)
    req(ls9_result.get("wordpress_api_call_executed") is False, "ls-new9 wordpress_api_call_executed=true", errors)
    req(ls9_result.get("wordpress_draft_created") is False, "ls-new9 wordpress_draft_created=true", errors)
    req(ls9_result.get("credential_env_read_executed") is False, "ls-new9 credential_env_read_executed=true", errors)
    req(ls9_result.get("credential_existence_check_executed") is False, "ls-new9 credential_existence_check_executed=true", errors)
    req(ls9_result.get("target_post_id_allocated") is False, "ls-new9 target_post_id_allocated=true", errors)

    human_completed = _strict_bool(decision_input.get("human_approval_completed"), warnings)
    human_approved = _strict_bool(decision_input.get("human_approved_for_execution"), warnings)
    input_execution_allowed = _strict_bool(decision_input.get("execution_allowed"), warnings)
    input_runner_allowed = _strict_bool(decision_input.get("runner_execution_allowed"), warnings)
    input_final_command = _strict_bool(decision_input.get("final_execution_command_created"), warnings)

    if input_execution_allowed:
        warnings.append("input_execution_allowed_true_forced_false")
    if input_runner_allowed:
        warnings.append("input_runner_execution_allowed_true_forced_false")
    if input_final_command:
        warnings.append("input_final_execution_command_created_true_forced_false")

    approval_label = str(decision_input.get("approval_label", ""))
    normalized_label = approval_label.strip()
    reviewer_notes = str(decision_input.get("reviewer_notes", ""))

    ready_for_ls_new_10 = (
        human_completed
        and human_approved
        and normalized_label == REQ_LABEL
        and not input_execution_allowed
        and not input_runner_allowed
        and not input_final_command
        and "invalid_boolean_type" not in warnings
    )

    status = APPROVED if ready_for_ls_new_10 else NOT_APPROVED
    next_action = (
        "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY"
        if status == APPROVED
        else "WAIT_OR_REVIEW_REWORK"
    )

    decision_record = {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_RESULT_RECORD",
        "status": status,
        "human_approval_completed": human_completed,
        "human_approved_for_execution": human_approved,
        "approval_label": approval_label,
        "normalized_approval_label": normalized_label,
        "approval_label_consumed": False,
        "reviewer_notes": reviewer_notes,
        "ready_for_ls_new_10": ready_for_ls_new_10,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "warnings": list(warnings),
        "recommended_next_action": next_action,
    }
    write_json(Path(args.output_decision_record), decision_record)

    result = {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_RESULT",
        "status": status,
        "execution_mode": "SEPARATE_EXECUTION_APPROVAL_DECISION_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORDED",
        "ls_new9_validated": len(errors) == 0,
        "human_approval_completed": human_completed,
        "human_approved_for_execution": human_approved,
        "approval_label": approval_label,
        "normalized_approval_label": normalized_label,
        "approval_label_consumed": False,
        "ready_for_ls_new_10": ready_for_ls_new_10,
        "execution_allowed": False,
        "runner_execution_allowed": False,
        "final_execution_command_created": False,
        "warnings": list(warnings),
        "auto_approval_executed": False,
        "ai_self_approval_executed": False,
        "approval_label_autofill_executed": False,
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
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": next_action,
        "recommended_next_phase_options": ["LS-NEW-10", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), _lock())
    _report(Path(args.report), result)

    print(status)
    return 0 if len(errors) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
