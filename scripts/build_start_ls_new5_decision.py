#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVED_STATUS = "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION"
NOT_APPROVED_STATUS = "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION"
LOCK_STATUS = "LSNEW5_DECISION_LOCKED_NO_EXECUTION"
REQUIRED_LS_NEW5_STATUS = "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION"
REQUIRED_LS_NEW5_VALIDATION = "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION"
VALID_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new5_decision_policy.json")
    p.add_argument("--schema", default="config/start_ls_new5_decision_schema.json")
    p.add_argument("--ls-new5-result", default="exchange/runtime/start_ls_new5_human_review_gate_result.json")
    p.add_argument("--ls-new5-validation-result", default="exchange/logs/start_ls_new5_human_review_gate_validation_result.json")
    p.add_argument("--decision-input", default="exchange/new_release/start_ls_new5_decision_input.json")
    p.add_argument("--output-decision-record", default="exchange/new_release/start_ls_new5_decision_result_record.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new5_decision_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new5_decision.lock.json")
    p.add_argument("--report", default="reports/start_ls_new5_decision_report.md")

    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-wordpress-draft", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
    p.add_argument("--require-no-auto-approval", action="store_true")
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


def _validate_required_flags(args: argparse.Namespace, errors: list[str]) -> None:
    required = {
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-http-get": args.require_no_http_get,
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-wordpress-write": args.require_no_wordpress_write,
        "--require-no-wordpress-draft": args.require_no_wordpress_draft,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-auto-approval": args.require_no_auto_approval,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in required.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _strict_bool(value: Any, warnings: list[str]) -> tuple[bool, bool]:
    if isinstance(value, bool):
        return True, value
    if "invalid_boolean_type" not in warnings:
        warnings.append("invalid_boolean_type")
    return False, False


def _normalize_decision_input(decision_input: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []

    hrc_valid, hrc = _strict_bool(decision_input.get("human_review_completed"), warnings)
    hap_valid, hap = _strict_bool(decision_input.get("human_approved"), warnings)
    ex_valid, ex_in = _strict_bool(decision_input.get("execution_allowed"), warnings)

    approval_label = str(decision_input.get("approval_label", ""))
    reviewer_notes = str(decision_input.get("reviewer_notes", ""))
    normalized_label = approval_label.strip()

    input_execution_safe = ex_valid and (ex_in is False)
    if ex_valid and ex_in is True:
        warnings.append("input_execution_allowed_true_forced_false")

    ready_for_ls_new_6 = (
        hrc_valid
        and hap_valid
        and ex_valid
        and hrc is True
        and hap is True
        and normalized_label == VALID_LABEL
        and input_execution_safe
    )

    status = APPROVED_STATUS if ready_for_ls_new_6 else NOT_APPROVED_STATUS
    recommended_next_action = (
        "PROCEED_TO_LS_NEW_6_PREP_ONLY" if ready_for_ls_new_6 else "WAIT_OR_REVIEW_REWORK"
    )

    return {
        "human_review_completed": hrc,
        "human_approved": hap,
        "approval_label": approval_label,
        "normalized_approval_label": normalized_label,
        "reviewer_notes": reviewer_notes,
        "ready_for_ls_new_6": ready_for_ls_new_6,
        "execution_allowed": False,
        "approval_label_consumed": False,
        "status": status,
        "recommended_next_action": recommended_next_action,
        "warnings": warnings,
    }


def _decision_record_payload(n: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_RESULT_RECORD",
        "status": n["status"],
        "human_review_completed": n["human_review_completed"],
        "human_approved": n["human_approved"],
        "approval_label": n["approval_label"],
        "normalized_approval_label": n["normalized_approval_label"],
        "approval_label_consumed": False,
        "reviewer_notes": n["reviewer_notes"],
        "ready_for_ls_new_6": n["ready_for_ls_new_6"],
        "execution_allowed": False,
        "warnings": list(n["warnings"]),
        "recommended_next_action": n["recommended_next_action"],
    }


def _result_payload(n: dict[str, Any], ls_new5_validated: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_RESULT",
        "status": n["status"],
        "execution_mode": "HUMAN_REVIEW_DECISION_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_HUMAN_REVIEW_DECISION_RECORDED",
        "ls_new5_validated": ls_new5_validated,
        "human_review_completed": n["human_review_completed"],
        "human_approved": n["human_approved"],
        "approval_label": n["approval_label"],
        "normalized_approval_label": n["normalized_approval_label"],
        "approval_label_consumed": False,
        "ready_for_ls_new_6": n["ready_for_ls_new_6"],
        "execution_allowed": False,
        "warnings": list(n["warnings"]),
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": n["recommended_next_action"],
        "recommended_next_phase_options": ["LS-NEW-6", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _lock_payload() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_LOCK",
        "status": LOCK_STATUS,
        "locked": True,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-5-DECISION Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- ls_new5_validated: {str(result.get('ls_new5_validated', False)).lower()}",
        f"- recommended_next_action: {result.get('recommended_next_action', '')}",
        "",
        "## Warnings",
    ]
    warnings = list(result.get("warnings", []))
    if warnings:
        lines.extend(f"- {w}" for w in warnings)
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Errors")
    errors = list(result.get("errors", []))
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    _validate_required_flags(args, errors)

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    ls_new5_result = try_load_json(Path(args.ls_new5_result), errors, "ls-new5-result")
    ls_new5_validation = try_load_json(Path(args.ls_new5_validation_result), errors, "ls-new5-validation-result")
    decision_input = try_load_json(Path(args.decision_input), errors, "decision-input")

    req(policy.get("phase") == "LS-NEW-5-DECISION", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-5-DECISION", "schema phase mismatch", errors)
    req(str(policy.get("allowed_approval_label", "")) == VALID_LABEL, "policy allowed approval label mismatch", errors)
    req(str(schema.get("allowed_approval_label", "")) == VALID_LABEL, "schema allowed approval label mismatch", errors)

    req(ls_new5_result.get("status") == REQUIRED_LS_NEW5_STATUS, "ls-new5 status mismatch", errors)
    req(ls_new5_validation.get("validation_status") == REQUIRED_LS_NEW5_VALIDATION, "ls-new5 validation mismatch", errors)
    req(bool(ls_new5_result.get("execution_allowed", True)) is False, "ls-new5 execution_allowed mismatch", errors)
    req(bool(ls_new5_result.get("human_review_required", False)) is True, "ls-new5 human_review_required mismatch", errors)
    req(bool(ls_new5_result.get("human_review_completed", True)) is False, "ls-new5 human_review_completed mismatch", errors)
    req(bool(ls_new5_result.get("human_approved", True)) is False, "ls-new5 human_approved mismatch", errors)
    req(bool(ls_new5_result.get("ready_for_ls_new_6", True)) is False, "ls-new5 ready_for_ls_new_6 mismatch", errors)

    normalized = _normalize_decision_input(decision_input)
    decision_record = _decision_record_payload(normalized)
    result = _result_payload(normalized, len(errors) == 0, errors)
    lock = _lock_payload()

    write_json(Path(args.output_decision_record), decision_record)
    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock)
    _write_report(Path(args.report), result)

    print(result["status"])
    return 0 if len(errors) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())