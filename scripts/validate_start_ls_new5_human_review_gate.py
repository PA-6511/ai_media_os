#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATED = "LSNEW5_HUMAN_REVIEW_GATE_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW5_HUMAN_REVIEW_GATE_NOT_VALIDATED"
RUN_READY = "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION"
PRODUCTION = "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION"
REQUIRED_LS4_VALIDATION = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION"
REQUIRED_APPROVAL_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new5_human_review_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new5_human_review_checklist_schema.json")
    p.add_argument("--review-request", default="exchange/new_release/start_ls_new5_human_review_request.json")
    p.add_argument("--checklist-template", default="exchange/new_release/start_ls_new5_human_review_checklist.template.json")
    p.add_argument("--decision-template", default="exchange/new_release/start_ls_new5_human_review_decision.template.json")
    p.add_argument("--decision-record", default="exchange/new_release/start_ls_new5_human_review_decision.json")
    p.add_argument("--wp-review-snapshot", default="exchange/new_release/start_ls_new5_wp_payload_review_snapshot.md")
    p.add_argument("--x-review-snapshot", default="exchange/new_release/start_ls_new5_x_payload_review_snapshot.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new5_human_review_gate_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new5_human_review_gate.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new5_human_review_gate_result.json")
    p.add_argument("--ls-new4-validation-result", default="exchange/logs/start_ls_new4_purchase_navigation_payload_dry_run_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new5_human_review_gate_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new5_human_review_gate_validation_report.md")
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


def _validate_result(result: dict[str, Any], errors: list[str]) -> None:
    req(result.get("phase") == "LS-NEW-5", "result phase mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("production_status") == PRODUCTION, "result production_status mismatch", errors)
    req(bool(result.get("ls_new4_validated", False)) is True, "ls_new4_validated mismatch", errors)
    req(bool(result.get("review_request_created", False)) is True, "review_request_created mismatch", errors)
    req(bool(result.get("checklist_template_created", False)) is True, "checklist_template_created mismatch", errors)
    req(bool(result.get("decision_template_created", False)) is True, "decision_template_created mismatch", errors)
    req(bool(result.get("decision_record_created", False)) is True, "decision_record_created mismatch", errors)
    req(bool(result.get("wp_review_snapshot_created", False)) is True, "wp_review_snapshot_created mismatch", errors)
    req(bool(result.get("x_review_snapshot_created", False)) is True, "x_review_snapshot_created mismatch", errors)

    req(bool(result.get("human_review_required", False)) is True, "human_review_required=false", errors)
    req(bool(result.get("human_review_completed", False)) is False, "human_review_completed=true", errors)
    req(bool(result.get("human_approved", False)) is False, "human_approved=true", errors)
    req(str(result.get("approval_label", "")) == "", "approval_label must be empty", errors)
    req(bool(result.get("approval_label_consumed", False)) is False, "approval_label_consumed=true", errors)
    req(str(result.get("required_approval_label_for_next", "")) == REQUIRED_APPROVAL_LABEL, "required approval label mismatch", errors)
    req(bool(result.get("ready_for_ls_new_6", False)) is False, "ready_for_ls_new_6=true", errors)
    req(bool(result.get("execution_allowed", False)) is False, "execution_allowed=true", errors)
    req(bool(result.get("auto_approval_executed", False)) is False, "auto_approval_executed=true", errors)

    must_false = [
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
        req(bool(result.get(key, False)) is False, f"{key}=true", errors)

    req(str(result.get("recommended_next_action", "")) == "WAIT_FOR_HUMAN_REVIEW_DECISION", "recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-5-DECISION", "LS-MON-2"], "recommended_next_phase_options mismatch", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-5", "lock phase mismatch", errors)
    req(lock.get("status") == "LSNEW5_HUMAN_REVIEW_GATE_LOCKED_WAITING_FOR_HUMAN_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(lock.get("locked", False)) is True, "lock mismatch", errors)
    req(bool(lock.get("human_review_required", False)) is True, "lock human_review_required mismatch", errors)
    req(bool(lock.get("human_review_completed", False)) is False, "lock human_review_completed=true", errors)
    req(bool(lock.get("human_approved", False)) is False, "lock human_approved=true", errors)
    req(bool(lock.get("approval_label_consumed", False)) is False, "lock approval_label_consumed=true", errors)
    req(bool(lock.get("ready_for_ls_new_6", False)) is False, "lock ready_for_ls_new_6=true", errors)
    req(bool(lock.get("execution_allowed", False)) is False, "lock execution_allowed=true", errors)


def _validate_request(request: dict[str, Any], errors: list[str]) -> None:
    req(request.get("phase") == "LS-NEW-5", "review request phase mismatch", errors)
    req(bool(request.get("review_required", False)) is True, "review_required=false", errors)
    req(bool(request.get("review_completed", False)) is False, "review_completed=true", errors)
    req(bool(request.get("human_approved", False)) is False, "request human_approved=true", errors)
    req(str(request.get("approval_label_required_for_next", "")) == REQUIRED_APPROVAL_LABEL, "request required label mismatch", errors)


def _validate_templates(checklist: dict[str, Any], decision_template: dict[str, Any], decision_record: dict[str, Any], errors: list[str]) -> None:
    req(checklist.get("document_type") == "START_LS_NEW5_HUMAN_REVIEW_CHECKLIST_TEMPLATE", "checklist document_type mismatch", errors)
    req(decision_template.get("document_type") == "START_LS_NEW5_HUMAN_REVIEW_DECISION_TEMPLATE", "decision template document_type mismatch", errors)
    req(decision_record.get("document_type") == "START_LS_NEW5_HUMAN_REVIEW_DECISION_RECORD", "decision record document_type mismatch", errors)

    req(bool(decision_template.get("human_review_completed", False)) is False, "decision template review completed true", errors)
    req(bool(decision_template.get("human_approved", False)) is False, "decision template approved true", errors)
    req(str(decision_template.get("approval_label", "")) == "", "decision template approval label not empty", errors)

    req(bool(decision_record.get("human_review_completed", False)) is False, "decision record review completed true", errors)
    req(bool(decision_record.get("human_approved", False)) is False, "decision record approved true", errors)
    req(str(decision_record.get("approval_label", "")) == "", "decision record approval label not empty", errors)
    req(bool(decision_record.get("approval_label_consumed", False)) is False, "decision record approval label consumed true", errors)
    req(bool(decision_record.get("ready_for_ls_new_6", False)) is False, "decision record ready_for_ls_new_6 true", errors)


def _validate_snapshots(wp_snapshot: str, x_snapshot: str, errors: list[str]) -> None:
    req("WordPress write executed: false" in wp_snapshot, "snapshot missing WordPress no-write notice", errors)
    req("X post executed: false" in x_snapshot, "snapshot missing X no-post notice", errors)
    req("#PR" in x_snapshot, "x snapshot missing #PR", errors)
    req("URL" in x_snapshot, "x snapshot missing URL placeholder", errors)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-5 Human Review Gate Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        "",
        "## Errors",
    ]
    errs = payload.get("errors", [])
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
    review_request = try_load_json(Path(args.review_request), errors, "review-request")
    checklist_template = try_load_json(Path(args.checklist_template), errors, "checklist-template")
    decision_template = try_load_json(Path(args.decision_template), errors, "decision-template")
    decision_record = try_load_json(Path(args.decision_record), errors, "decision-record")
    wp_snapshot = read_text(Path(args.wp_review_snapshot), errors, "wp-review-snapshot")
    x_snapshot = read_text(Path(args.x_review_snapshot), errors, "x-review-snapshot")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls4_validation = try_load_json(Path(args.ls_new4_validation_result), errors, "ls-new4-validation-result")

    req(policy.get("phase") == "LS-NEW-5", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-5", "schema phase mismatch", errors)
    req(ls4_validation.get("validation_status") == REQUIRED_LS4_VALIDATION, "ls-new4 validation mismatch", errors)
    req(result == run_result, "result and run_result mismatch", errors)

    _validate_request(review_request, errors)
    _validate_templates(checklist_template, decision_template, decision_record, errors)
    _validate_snapshots(wp_snapshot, x_snapshot, errors)
    _validate_result(result, errors)
    _validate_lock(lock, errors)

    validation_status = VALIDATED if len(errors) == 0 else NOT_VALIDATED
    payload = {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_GATE_VALIDATION_RESULT",
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
