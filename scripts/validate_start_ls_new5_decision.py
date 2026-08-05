#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATED = "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW5_DECISION_NOT_VALIDATED"
APPROVED_STATUS = "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION"
NOT_APPROVED_STATUS = "LSNEW5_HUMAN_REVIEW_DECISION_NOT_APPROVED_NO_EXECUTION"
RUN_PRODUCTION = "NO_EXECUTION_HUMAN_REVIEW_DECISION_RECORDED"
REQUIRED_LS_NEW5_VALIDATION = "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION"
VALID_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new5_decision_policy.json")
    p.add_argument("--schema", default="config/start_ls_new5_decision_schema.json")
    p.add_argument("--decision-input", default="exchange/new_release/start_ls_new5_decision_input.json")
    p.add_argument("--decision-record", default="exchange/new_release/start_ls_new5_decision_result_record.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new5_decision_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new5_decision.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new5_decision_result.json")
    p.add_argument("--ls-new5-validation-result", default="exchange/logs/start_ls_new5_human_review_gate_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new5_decision_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new5_decision_validation_report.md")
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


def _validate_types(record: dict[str, Any], errors: list[str]) -> None:
    for key in ["human_review_completed", "human_approved", "execution_allowed", "ready_for_ls_new_6", "approval_label_consumed"]:
        req(isinstance(record.get(key), bool), f"{key} must be boolean", errors)


def _decision_conditions(record: dict[str, Any], warnings: list[str]) -> bool:
    return (
        record.get("human_review_completed") is True
        and record.get("human_approved") is True
        and str(record.get("normalized_approval_label", "")) == VALID_LABEL
        and record.get("execution_allowed") is False
        and "invalid_boolean_type" not in warnings
        and "input_execution_allowed_true_forced_false" not in warnings
    )


def _validate_decision_record(record: dict[str, Any], errors: list[str]) -> None:
    req(record.get("phase") == "LS-NEW-5-DECISION", "decision record phase mismatch", errors)
    req(record.get("document_type") == "START_LS_NEW5_HUMAN_REVIEW_DECISION_RESULT_RECORD", "decision record document_type mismatch", errors)
    req(record.get("approval_label_consumed") is False, "approval_label_consumed=true", errors)
    req(record.get("execution_allowed") is False, "execution_allowed=true", errors)

    warnings = list(record.get("warnings", []))
    req(isinstance(warnings, list), "warnings must be list", errors)
    for w in warnings:
        req(w in ["input_execution_allowed_true_forced_false", "invalid_boolean_type"], f"unexpected warning: {w}", errors)

    _validate_types(record, errors)

    expected_ready = _decision_conditions(record, warnings)
    if record.get("ready_for_ls_new_6") is True and not expected_ready:
        errors.append("ready_for_ls_new_6=true without valid approval conditions")

    status = str(record.get("status", ""))
    if status == APPROVED_STATUS:
        req(expected_ready is True, "approved status without valid conditions", errors)
        req(str(record.get("recommended_next_action", "")) == "PROCEED_TO_LS_NEW_6_PREP_ONLY", "approved recommended_next_action mismatch", errors)
    elif status == NOT_APPROVED_STATUS:
        req(record.get("ready_for_ls_new_6") is False, "not approved status with ready_for_ls_new_6=true", errors)
        req(str(record.get("recommended_next_action", "")) == "WAIT_OR_REVIEW_REWORK", "not approved recommended_next_action mismatch", errors)
    else:
        errors.append("decision record status mismatch")


def _validate_result(result: dict[str, Any], record: dict[str, Any], errors: list[str]) -> None:
    req(result.get("phase") == "LS-NEW-5-DECISION", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW5_DECISION_RESULT", "result document_type mismatch", errors)
    req(result.get("execution_mode") == "HUMAN_REVIEW_DECISION_ONLY_NO_EXECUTION", "result execution_mode mismatch", errors)
    req(result.get("production_status") == RUN_PRODUCTION, "result production_status mismatch", errors)
    req(result.get("execution_allowed") is False, "result execution_allowed=true", errors)
    req(result.get("approval_label_consumed") is False, "result approval_label_consumed=true", errors)

    req(result.get("status") == record.get("status"), "result status mismatch", errors)
    req(result.get("human_review_completed") == record.get("human_review_completed"), "result human_review_completed mismatch", errors)
    req(result.get("human_approved") == record.get("human_approved"), "result human_approved mismatch", errors)
    req(result.get("approval_label") == record.get("approval_label"), "result approval_label mismatch", errors)
    req(result.get("normalized_approval_label") == record.get("normalized_approval_label"), "result normalized_approval_label mismatch", errors)
    req(result.get("ready_for_ls_new_6") == record.get("ready_for_ls_new_6"), "result ready_for_ls_new_6 mismatch", errors)
    req(list(result.get("warnings", [])) == list(record.get("warnings", [])), "result warnings mismatch", errors)

    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-6", "LS-MON-2"], "recommended_next_phase_options mismatch", errors)

    must_false = [
        "auto_approval_executed",
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(result.get(key) is False, f"{key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-5-DECISION", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW5_DECISION_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW5_DECISION_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    must_false = [
        "approval_label_consumed",
        "execution_allowed",
        "auto_approval_executed",
        "external_fetch_executed",
        "http_get_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "x_api_call_executed",
        "x_post_executed",
        "credential_env_read_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-5-DECISION Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        "",
        "## Errors",
    ]
    errs = list(payload.get("errors", []))
    if errs:
        lines.extend(f"- {e}" for e in errs)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    decision_input = try_load_json(Path(args.decision_input), errors, "decision-input")
    decision_record = try_load_json(Path(args.decision_record), errors, "decision-record")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls_new5_validation = try_load_json(Path(args.ls_new5_validation_result), errors, "ls-new5-validation-result")

    req(policy.get("phase") == "LS-NEW-5-DECISION", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-5-DECISION", "schema phase mismatch", errors)
    req(str(policy.get("allowed_approval_label", "")) == VALID_LABEL, "policy allowed approval label mismatch", errors)
    req(str(schema.get("allowed_approval_label", "")) == VALID_LABEL, "schema allowed approval label mismatch", errors)
    req(ls_new5_validation.get("validation_status") == REQUIRED_LS_NEW5_VALIDATION, "ls-new5 validation mismatch", errors)

    req(decision_input.get("phase") == "LS-NEW-5-DECISION", "decision input phase mismatch", errors)
    req(decision_input.get("document_type") == "START_LS_NEW5_DECISION_INPUT", "decision input document_type mismatch", errors)
    req(result == run_result, "result and run_result mismatch", errors)

    _validate_decision_record(decision_record, errors)
    _validate_result(result, decision_record, errors)
    _validate_lock(lock, errors)

    validation_status = VALIDATED if len(errors) == 0 else NOT_VALIDATED
    payload = {
        "phase": "LS-NEW-5-DECISION",
        "document_type": "START_LS_NEW5_DECISION_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), payload)
    _write_report(Path(args.report), payload)

    print(validation_status)
    return 0 if validation_status == VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())