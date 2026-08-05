#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW9_DECISION_NOT_VALIDATED"
REQ_LS9_VALID = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"
MODE = "SEPARATE_EXECUTION_APPROVAL_DECISION_ONLY_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new9_decision_policy.json")
    p.add_argument("--schema", default="config/start_ls_new9_decision_schema.json")
    p.add_argument("--decision-input", default="exchange/new_release/start_ls_new9_decision_input.json")
    p.add_argument("--decision-record", default="exchange/new_release/start_ls_new9_decision_result_record.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new9_decision_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new9_decision.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new9_decision_result.json")
    p.add_argument("--ls-new9-validation-result", default="exchange/logs/start_ls_new9_separate_execution_approval_gate_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new9_decision_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new9_decision_validation_report.md")
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


def _strict_bool(value: Any) -> tuple[bool, bool]:
    if isinstance(value, bool):
        return value, False
    return False, True


def _calc_expected(input_data: dict[str, Any]) -> tuple[bool, str, list[str], bool, bool, bool, bool]:
    warnings: list[str] = []
    human_completed, bad1 = _strict_bool(input_data.get("human_approval_completed"))
    human_approved, bad2 = _strict_bool(input_data.get("human_approved_for_execution"))
    input_execution_allowed, bad3 = _strict_bool(input_data.get("execution_allowed"))
    input_runner_allowed, bad4 = _strict_bool(input_data.get("runner_execution_allowed"))
    input_final_command, bad5 = _strict_bool(input_data.get("final_execution_command_created"))
    if bad1 or bad2 or bad3 or bad4 or bad5:
        warnings.append("invalid_boolean_type")
    if input_execution_allowed:
        warnings.append("input_execution_allowed_true_forced_false")
    if input_runner_allowed:
        warnings.append("input_runner_execution_allowed_true_forced_false")
    if input_final_command:
        warnings.append("input_final_execution_command_created_true_forced_false")
    label = str(input_data.get("approval_label", ""))
    normalized = label.strip()
    ready = (
        human_completed
        and human_approved
        and normalized == REQ_LABEL
        and not input_execution_allowed
        and not input_runner_allowed
        and not input_final_command
        and "invalid_boolean_type" not in warnings
    )
    expected_status = "LSNEW9_DECISION_HUMAN_APPROVED_NO_EXECUTION" if ready else "LSNEW9_DECISION_NOT_APPROVED_NO_EXECUTION"
    return ready, expected_status, warnings, human_completed, human_approved, input_execution_allowed, input_runner_allowed


def _validate_record(record: dict[str, Any], expected_ready: bool, expected_status: str, expected_warnings: list[str], errors: list[str]) -> None:
    req(record.get("phase") == "LS-NEW-9-DECISION", "decision record phase mismatch", errors)
    req(record.get("document_type") == "START_LS_NEW9_DECISION_RESULT_RECORD", "decision record document_type mismatch", errors)
    req(record.get("status") == expected_status, "decision record status mismatch", errors)
    req(record.get("ready_for_ls_new_10") is expected_ready, "decision record ready_for_ls_new_10 mismatch", errors)
    req(record.get("execution_allowed") is False, "decision record execution_allowed=true", errors)
    req(record.get("runner_execution_allowed") is False, "decision record runner_execution_allowed=true", errors)
    req(record.get("final_execution_command_created") is False, "decision record final_execution_command_created=true", errors)
    req(record.get("approval_label_consumed") is False, "decision record approval_label_consumed=true", errors)
    req(list(record.get("warnings", [])) == expected_warnings, "decision record warnings mismatch", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], expected_ready: bool, expected_status: str, expected_warnings: list[str], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-9-DECISION", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW9_DECISION_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == expected_status, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == "NO_EXECUTION_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORDED", "result production_status mismatch", errors)
    req(result.get("ls_new9_validated") is True, "result ls_new9_validated mismatch", errors)
    req(result.get("ready_for_ls_new_10") is expected_ready, "result ready_for_ls_new_10 mismatch", errors)
    req(result.get("execution_allowed") is False, "result execution_allowed=true", errors)
    req(result.get("runner_execution_allowed") is False, "result runner_execution_allowed=true", errors)
    req(result.get("final_execution_command_created") is False, "result final_execution_command_created=true", errors)
    req(result.get("approval_label_consumed") is False, "result approval_label_consumed=true", errors)
    req(list(result.get("warnings", [])) == expected_warnings, "result warnings mismatch", errors)
    req(result.get("auto_approval_executed") is False, "auto_approval_executed=true", errors)
    req(result.get("ai_self_approval_executed") is False, "ai_self_approval_executed=true", errors)
    req(result.get("approval_label_autofill_executed") is False, "approval_label_autofill_executed=true", errors)
    req(result.get("wordpress_api_call_executed") is False, "wordpress_api_call_executed=true", errors)
    req(result.get("wordpress_write_executed") is False, "wordpress_write_executed=true", errors)
    req(result.get("wordpress_draft_created") is False, "wordpress_draft_created=true", errors)
    req(result.get("wordpress_publish_executed") is False, "wordpress_publish_executed=true", errors)
    req(result.get("x_api_call_executed") is False, "x_api_call_executed=true", errors)
    req(result.get("x_post_executed") is False, "x_post_executed=true", errors)
    req(result.get("external_fetch_executed") is False, "external_fetch_executed=true", errors)
    req(result.get("http_get_executed") is False, "http_get_executed=true", errors)
    req(result.get("credential_env_read_executed") is False, "credential_env_read_executed=true", errors)
    req(result.get("credential_existence_check_executed") is False, "credential_existence_check_executed=true", errors)
    req(result.get("credential_secret_output") is False, "credential_secret_output=true", errors)
    req(result.get("target_post_id") is None, "target_post_id must be null", errors)
    req(result.get("target_post_id_allocated") is False, "target_post_id_allocated=true", errors)

    if expected_ready:
        req(result.get("recommended_next_action") == "PROCEED_TO_LS_NEW_10_EXECUTION_PREP_ONLY", "recommended_next_action mismatch for approved", errors)
    else:
        req(result.get("recommended_next_action") == "WAIT_OR_REVIEW_REWORK", "recommended_next_action mismatch for not approved", errors)

    opts = list(result.get("recommended_next_phase_options", []))
    req(opts == ["LS-NEW-10", "LS-MON-2"], "recommended_next_phase_options mismatch", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-9-DECISION", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW9_DECISION_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW9_DECISION_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "approval_label_consumed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "approval_label_autofill_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "credential_env_read_executed",
        "credential_existence_check_executed",
        "target_post_id_allocated",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-9-DECISION Validation Report",
        "",
        f"- generated_at: {out.get('generated_at', '')}",
        f"- validation_status: {out.get('validation_status', '')}",
        f"- run_status: {out.get('run_status', '')}",
        "",
        "## Errors",
    ]
    errs = list(out.get("errors", []))
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
    ls9_validation = try_load_json(Path(args.ls_new9_validation_result), errors, "ls-new9-validation-result")

    req(policy.get("phase") == "LS-NEW-9-DECISION", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-9-DECISION", "schema phase mismatch", errors)
    req(ls9_validation.get("validation_status") == REQ_LS9_VALID, "ls-new9 validation status mismatch", errors)
    req(decision_input.get("phase") == "LS-NEW-9-DECISION", "decision-input phase mismatch", errors)
    req(decision_input.get("document_type") == "START_LS_NEW9_DECISION_INPUT", "decision-input document_type mismatch", errors)

    expected_ready, expected_status, expected_warnings, _, _, _, _ = _calc_expected(decision_input)
    _validate_record(decision_record, expected_ready, expected_status, expected_warnings, errors)
    _validate_result(result, run_result, expected_ready, expected_status, expected_warnings, errors)
    _validate_lock(lock, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-9-DECISION",
        "document_type": "START_LS_NEW9_DECISION_VALIDATION_RESULT",
        "validation_status": status,
        "run_status": str(result.get("status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), out)
    _report(Path(args.report), out)

    print(status)
    return 0 if status == VALID else 1


if __name__ == "__main__":
    raise SystemExit(main())
