#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATED = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_NOT_VALIDATED"
RUN_READY = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION"
RUN_PRODUCTION = "NO_EXECUTION_WP_DRAFT_PAYLOAD_PREP_ONLY"
REQ_NEW5_VALID = "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new6_wp_draft_payload_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new6_wp_draft_payload_schema.json")
    p.add_argument("--payload", default="exchange/new_release/start_ls_new6_wp_draft_payload_prep.json")
    p.add_argument("--preview", default="exchange/new_release/start_ls_new6_wp_draft_payload_preview.md")
    p.add_argument("--safety-summary", default="exchange/new_release/start_ls_new6_wp_draft_payload_safety_summary.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new6_wp_draft_payload_prep_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new6_wp_draft_payload_prep.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new6_wp_draft_payload_prep_result.json")
    p.add_argument("--ls-new5-decision-validation-result", default="exchange/logs/start_ls_new5_decision_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new6_wp_draft_payload_prep_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new6_wp_draft_payload_prep_validation_report.md")
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


def _validate_preview(preview: str, errors: list[str]) -> None:
    req(preview.startswith("# LS-NEW-6 WordPress Draft Payload Prep Preview"), "preview header mismatch", errors)
    required_lines = [
        "- Phase: LS-NEW-6",
        "- Status: READY_NO_EXECUTION",
        "- WordPress API executed: false",
        "- WordPress write executed: false",
        "- WordPress draft created: false",
        "- Target post ID allocated: false",
        "- Execution allowed: false",
        "- Source approval: APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "- Approval label consumed: false",
    ]
    for line in required_lines:
        req(line in preview, f"preview missing line: {line}", errors)


def _validate_payload(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-6", "payload phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP", "payload document_type mismatch", errors)
    req(payload.get("status") == RUN_READY, "payload status mismatch", errors)
    req(payload.get("execution_mode") == "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION", "payload execution_mode mismatch", errors)
    req(payload.get("production_status") == RUN_PRODUCTION, "payload production_status mismatch", errors)
    req(payload.get("ls_new5_decision_validated") is True, "payload ls_new5_decision_validated mismatch", errors)
    req(payload.get("ls_new5_decision_approved") is True, "payload ls_new5_decision_approved mismatch", errors)
    req(payload.get("source_approval_label") == REQ_LABEL, "payload source_approval_label mismatch", errors)
    req(payload.get("approval_label_consumed") is False, "approval_label_consumed=true", errors)
    req(payload.get("post_status_target") == "draft", "post_status_target mismatch", errors)
    req(payload.get("target_post_id") is None, "target_post_id must be null", errors)
    req(payload.get("target_post_id_allocated") is False, "target_post_id_allocated=true", errors)
    req(payload.get("purchase_navigation_media") is True, "purchase_navigation_media mismatch", errors)
    req(payload.get("work_explanation_media") is False, "work_explanation_media=true", errors)
    req(payload.get("affiliate_disclosure_included") is True, "missing affiliate disclosure", errors)
    req(payload.get("external_fetch_notice_included") is True, "missing external fetch notice", errors)
    req(payload.get("source_unverified_notice_included") is True, "source_unverified_notice_included mismatch", errors)
    req(payload.get("official_synopsis_copy_included") is False, "official_synopsis_copy_included=true", errors)
    req(payload.get("store_description_copy_included") is False, "store_description_copy_included=true", errors)
    req(payload.get("review_copy_included") is False, "review_copy_included=true", errors)
    req(payload.get("long_work_explanation_included") is False, "long_work_explanation_included=true", errors)
    req(payload.get("execution_allowed") is False, "execution_allowed=true", errors)
    req(payload.get("ready_for_ls_new_7") is True, "ready_for_ls_new_7=false", errors)
    req(payload.get("recommended_next_action") == "BEGIN_LS_NEW_7_WP_DRAFT_RUNNER_PREP_NO_EXECUTION", "recommended_next_action mismatch", errors)
    req(list(payload.get("recommended_next_phase_options", [])) == ["LS-NEW-7", "LS-MON-2"], "recommended_next_phase_options mismatch", errors)

    false_keys = [
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
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ]
    for key in false_keys:
        req(payload.get(key) is False, f"{key}=true", errors)


def _validate_safety(safety: dict[str, Any], errors: list[str]) -> None:
    req(safety.get("phase") == "LS-NEW-6", "safety phase mismatch", errors)
    req(safety.get("document_type") == "START_LS_NEW6_WP_DRAFT_PAYLOAD_SAFETY_SUMMARY", "safety document_type mismatch", errors)
    req(safety.get("status") == "LSNEW6_SAFETY_SUMMARY_READY_NO_EXECUTION", "safety status mismatch", errors)
    req(safety.get("ready_for_ls_new_7") is True, "safety ready_for_ls_new_7 mismatch", errors)
    false_keys = [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "x_api_call_executed",
        "x_post_executed",
        "external_fetch_executed",
        "http_get_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "target_post_id_allocated",
        "approval_label_consumed",
        "execution_allowed",
    ]
    for key in false_keys:
        req(safety.get(key) is False, f"safety {key}=true", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-6", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("execution_mode") == "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION", "result execution_mode mismatch", errors)
    req(result.get("production_status") == RUN_PRODUCTION, "result production_status mismatch", errors)
    req(result.get("wp_draft_payload_created") is True, "wp_draft_payload_created mismatch", errors)
    req(result.get("wp_draft_payload_preview_created") is True, "wp_draft_payload_preview_created mismatch", errors)
    req(result.get("safety_summary_created") is True, "safety_summary_created mismatch", errors)
    req(result.get("execution_allowed") is False, "result execution_allowed=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-6", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW6_WP_DRAFT_PAYLOAD_PREP_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    false_keys = [
        "execution_allowed",
        "approval_label_consumed",
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
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in false_keys:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-6 WP Draft Payload Prep Validation Report",
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
    payload = try_load_json(Path(args.payload), errors, "payload")
    preview = read_text(Path(args.preview), errors, "preview")
    safety = try_load_json(Path(args.safety_summary), errors, "safety-summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls5_validation = try_load_json(Path(args.ls_new5_decision_validation_result), errors, "ls-new5-decision-validation-result")

    req(policy.get("phase") == "LS-NEW-6", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-6", "schema phase mismatch", errors)
    req(ls5_validation.get("validation_status") == REQ_NEW5_VALID, "ls-new5 decision validation mismatch", errors)

    _validate_payload(payload, errors)
    _validate_preview(preview, errors)
    _validate_safety(safety, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)

    validation_status = VALIDATED if len(errors) == 0 else NOT_VALIDATED
    out = {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), out)
    _write_report(Path(args.report), out)

    print(validation_status)
    return 0 if validation_status == VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())