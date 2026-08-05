#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_NOT_VALIDATED"
RUN_READY = "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
RUN_MODE = "SEPARATE_EXECUTION_APPROVAL_GATE_ONLY_NO_EXECUTION"
RUN_PROD = "WAITING_FOR_SEPARATE_EXECUTION_APPROVAL_NO_EXECUTION"
REQ_LS8_VALID = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new9_separate_execution_approval_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new9_separate_execution_approval_gate_schema.json")
    p.add_argument("--request", default="exchange/new_release/start_ls_new9_separate_execution_approval_request.json")
    p.add_argument("--checklist-template", default="exchange/new_release/start_ls_new9_separate_execution_approval_checklist.template.json")
    p.add_argument("--decision-template", default="exchange/new_release/start_ls_new9_separate_execution_approval_decision.template.json")
    p.add_argument("--decision-record", default="exchange/new_release/start_ls_new9_separate_execution_approval_decision.json")
    p.add_argument("--scope-summary", default="exchange/new_release/start_ls_new9_approval_scope_summary.md")
    p.add_argument("--safety-summary", default="exchange/new_release/start_ls_new9_approval_gate_safety_summary.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new9_separate_execution_approval_gate_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new9_separate_execution_approval_gate.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new9_separate_execution_approval_gate_result.json")
    p.add_argument("--ls-new8-validation-result", default="exchange/logs/start_ls_new8_wp_draft_runner_final_preflight_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new9_separate_execution_approval_gate_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new9_separate_execution_approval_gate_validation_report.md")
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


def _false_keys() -> list[str]:
    return [
        "human_approval_completed",
        "human_approved_for_execution",
        "approval_label_consumed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "credential_env_read_executed",
        "credential_existence_check_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
    ]


def _validate_request(request: dict[str, Any], errors: list[str]) -> None:
    req(request.get("phase") == "LS-NEW-9", "request phase mismatch", errors)
    req(request.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST", "request document_type mismatch", errors)
    req(request.get("status") == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_REQUEST_CREATED_NO_EXECUTION", "request status mismatch", errors)
    req(request.get("execution_mode") == RUN_MODE, "request execution_mode mismatch", errors)
    req(request.get("production_status") == RUN_PROD, "request production_status mismatch", errors)
    req(request.get("ls_new8_validated") is True, "request ls_new8_validated mismatch", errors)
    req(request.get("target_post_id") is None, "request target_post_id must be null", errors)
    req(request.get("human_approval_required") is True, "request human_approval_required mismatch", errors)
    req(request.get("human_approval_completed") is False, "request human_approval_completed=true", errors)
    req(request.get("human_approved_for_execution") is False, "request human_approved_for_execution=true", errors)
    req(request.get("required_approval_label") == REQ_LABEL, "request required_approval_label mismatch", errors)
    req(request.get("approval_label") == "", "request approval_label must be empty", errors)
    req(request.get("approval_label_consumed") is False, "request approval_label_consumed=true", errors)
    req(request.get("execution_allowed") is False, "request execution_allowed=true", errors)
    req(request.get("runner_execution_allowed") is False, "request runner_execution_allowed=true", errors)
    req(request.get("final_execution_command_created") is False, "request final_execution_command_created=true", errors)


def _validate_checklist(checklist: dict[str, Any], errors: list[str]) -> None:
    req(checklist.get("phase") == "LS-NEW-9", "checklist phase mismatch", errors)
    req(checklist.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_CHECKLIST_TEMPLATE", "checklist document_type mismatch", errors)
    cr = dict(checklist.get("candidate_review", {}))
    for key in [
        "content_item_id_checked",
        "title_checked",
        "volume_checked",
        "author_checked",
        "publisher_checked",
        "release_date_checked",
        "post_status_target_checked",
    ]:
        req(cr.get(key) is False, f"checklist candidate_review {key}=true", errors)


def _validate_decision_template(template: dict[str, Any], errors: list[str]) -> None:
    req(template.get("phase") == "LS-NEW-9", "decision template phase mismatch", errors)
    req(template.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_TEMPLATE", "decision template document_type mismatch", errors)
    req("AI must not auto-approve" in str(template.get("instructions", "")), "decision template instructions mismatch", errors)
    req(template.get("allowed_approval_label") == REQ_LABEL, "decision template label mismatch", errors)
    req(template.get("human_approval_completed") is False, "decision template human_approval_completed=true", errors)
    req(template.get("human_approved_for_execution") is False, "decision template human_approved_for_execution=true", errors)
    req(template.get("approval_label") == "", "decision template approval_label must be empty", errors)
    req(template.get("execution_allowed") is False, "decision template execution_allowed=true", errors)


def _validate_decision_record(record: dict[str, Any], errors: list[str]) -> None:
    req(record.get("phase") == "LS-NEW-9", "decision record phase mismatch", errors)
    req(record.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_RECORD", "decision record document_type mismatch", errors)
    req(record.get("status") == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION", "decision record status mismatch", errors)
    req(record.get("human_approval_completed") is False, "decision record human_approval_completed=true", errors)
    req(record.get("human_approved_for_execution") is False, "decision record human_approved_for_execution=true", errors)
    req(record.get("approval_label") == "", "decision record approval_label must be empty", errors)
    req(record.get("approval_label_consumed") is False, "decision record approval_label_consumed=true", errors)
    req(record.get("ready_for_ls_new_9_decision") is True, "decision record ready_for_ls_new_9_decision=false", errors)
    req(record.get("ready_for_ls_new_10") is False, "decision record ready_for_ls_new_10=true", errors)
    req(record.get("execution_allowed") is False, "decision record execution_allowed=true", errors)


def _validate_scope_summary(text: str, errors: list[str]) -> None:
    req(text.startswith("# LS-NEW-9 Separate Execution Approval Gate Scope Summary"), "scope summary header mismatch", errors)
    for line in [
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
        "LS-NEW-9 自体では WordPress API / credential.env / draft creation を許可しない。",
    ]:
        req(line in text, f"scope summary missing line: {line}", errors)


def _validate_safety_summary(safety: dict[str, Any], errors: list[str]) -> None:
    req(safety.get("phase") == "LS-NEW-9", "safety summary phase mismatch", errors)
    req(safety.get("document_type") == "START_LS_NEW9_APPROVAL_GATE_SAFETY_SUMMARY", "safety summary document_type mismatch", errors)
    req(safety.get("status") == "LSNEW9_APPROVAL_GATE_SAFETY_SUMMARY_READY_NO_EXECUTION", "safety summary status mismatch", errors)
    req(safety.get("auto_approval_executed") is False, "auto_approval_executed=true", errors)
    req(safety.get("ai_self_approval_executed") is False, "ai_self_approval_executed=true", errors)
    req(safety.get("approval_label_autofill_executed") is False, "approval_label_autofill_executed=true", errors)
    for key in [
        "approval_label_consumed",
        "runner_execution_allowed",
        "final_execution_command_created",
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
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
    ]:
        req(safety.get(key) is False, f"safety summary {key}=true", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-9", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("execution_mode") == RUN_MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == RUN_PROD, "result production_status mismatch", errors)
    req(result.get("ls_new8_validated") is True, "result ls_new8_validated mismatch", errors)
    req(result.get("approval_request_created") is True, "result approval_request_created mismatch", errors)
    req(result.get("approval_checklist_template_created") is True, "result approval_checklist_template_created mismatch", errors)
    req(result.get("approval_decision_template_created") is True, "result approval_decision_template_created mismatch", errors)
    req(result.get("approval_decision_record_created") is True, "result approval_decision_record_created mismatch", errors)
    req(result.get("approval_scope_summary_created") is True, "result approval_scope_summary_created mismatch", errors)
    req(result.get("approval_gate_safety_summary_created") is True, "result approval_gate_safety_summary_created mismatch", errors)
    req(result.get("target_post_id") is None, "result target_post_id must be null", errors)
    req(result.get("human_approval_required") is True, "result human_approval_required mismatch", errors)
    req(result.get("human_approval_completed") is False, "result human_approval_completed=true", errors)
    req(result.get("human_approved_for_execution") is False, "result human_approved_for_execution=true", errors)
    req(result.get("required_approval_label") == REQ_LABEL, "result required_approval_label mismatch", errors)
    req(result.get("approval_label") == "", "result approval_label must be empty", errors)
    req(result.get("ready_for_ls_new_9_decision") is True, "result ready_for_ls_new_9_decision=false", errors)
    req(result.get("ready_for_ls_new_10") is False, "result ready_for_ls_new_10=true", errors)
    req(result.get("recommended_next_action") == "WAIT_FOR_SEPARATE_EXECUTION_APPROVAL_DECISION", "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-9-DECISION", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)
    for key in _false_keys():
        req(result.get(key) is False, f"result {key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-9", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW9_SEPARATE_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    req(lock.get("human_approval_required") is True, "lock human_approval_required mismatch", errors)
    req(lock.get("human_approval_completed") is False, "lock human_approval_completed=true", errors)
    req(lock.get("human_approved_for_execution") is False, "lock human_approved_for_execution=true", errors)
    for key in [
        "approval_label_consumed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "execution_allowed",
        "target_post_id_allocated",
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
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-9 Separate Execution Approval Gate Validation Report",
        "",
        f"- generated_at: {out.get('generated_at', '')}",
        f"- validation_status: {out.get('validation_status', '')}",
        f"- run_status: {out.get('run_status', '')}",
        f"- production_status: {out.get('production_status', '')}",
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
    request = try_load_json(Path(args.request), errors, "request")
    checklist = try_load_json(Path(args.checklist_template), errors, "checklist-template")
    decision_template = try_load_json(Path(args.decision_template), errors, "decision-template")
    decision_record = try_load_json(Path(args.decision_record), errors, "decision-record")
    scope_summary = read_text(Path(args.scope_summary), errors, "scope-summary")
    safety_summary = try_load_json(Path(args.safety_summary), errors, "safety-summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls8_valid = try_load_json(Path(args.ls_new8_validation_result), errors, "ls-new8-validation-result")

    req(policy.get("phase") == "LS-NEW-9", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-9", "schema phase mismatch", errors)
    req(ls8_valid.get("validation_status") == REQ_LS8_VALID, "ls-new8 validation status mismatch", errors)

    _validate_request(request, errors)
    _validate_checklist(checklist, errors)
    _validate_decision_template(decision_template, errors)
    _validate_decision_record(decision_record, errors)
    _validate_scope_summary(scope_summary, errors)
    _validate_safety_summary(safety_summary, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-9",
        "document_type": "START_LS_NEW9_SEPARATE_EXECUTION_APPROVAL_GATE_VALIDATION_RESULT",
        "validation_status": status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
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
