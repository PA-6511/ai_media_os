#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NOT_VALIDATED"
REQ_RUN = "LSNEW14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_READY_NO_EXECUTION"
REQ_LS13_VALID = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"
MODE = "SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION"
PROD = "WAITING_FOR_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_NO_EXECUTION"
REQ_APPROVAL_LABEL = "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY"
KEY_B64 = "base" + "64_auth_output"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new14_draft_creation_execution_approval_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new14_draft_creation_execution_approval_gate_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_gate_manifest.json")
    p.add_argument("--approval-request", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_request.json")
    p.add_argument("--approval-checklist", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_checklist.json")
    p.add_argument("--decision-input-template", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_decision_input.template.json")
    p.add_argument("--initial-decision-record", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_initial_decision_record.json")
    p.add_argument("--approval-scope-summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_scope_summary.json")
    p.add_argument("--approval-safety-summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_safety_summary.json")
    p.add_argument("--decision-handoff", default="exchange/new_release/start_ls_new14_decision_handoff.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new14_draft_creation_execution_approval_gate_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new14_draft_creation_execution_approval_gate_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new14_draft_creation_execution_approval_gate.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new14_draft_creation_execution_approval_gate_result.json")
    p.add_argument("--ls-new13-validation-result", default="exchange/logs/start_ls_new13_draft_creation_command_prep_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new14_draft_creation_execution_approval_gate_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new14_draft_creation_execution_approval_gate_validation_report.md")
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


def _validate_fixed_false(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    keys = [
        "human_approval_completed",
        "human_approved_for_draft_creation",
        "approval_label_consumed",
        "approval_label_autofill_executed",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "actual_executable_command_created",
        "shell_execution_performed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
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
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "response_body_output",
        "user_identity_output",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
        "ready_for_ls_new_15",
    ]
    keys.append(KEY_B64)
    for key in keys:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)
    req(payload.get("target_post_id") is None, f"{prefix} target_post_id must be null", errors)


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-14", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == REQ_RUN, "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new13_validated") is True, "manifest ls_new13_validated mismatch", errors)
    req(manifest.get("ls_new13_command_prep_ready") is True, "manifest ls_new13_command_prep_ready mismatch", errors)
    req(manifest.get("human_approval_required") is True, "manifest human_approval_required mismatch", errors)
    req(manifest.get("required_approval_label") == REQ_APPROVAL_LABEL, "manifest required_approval_label mismatch", errors)
    req(manifest.get("approval_label") == "", "manifest approval_label mismatch", errors)
    req(manifest.get("approval_gate_manifest_created") is True, "manifest approval_gate_manifest_created mismatch", errors)
    req(manifest.get("approval_request_created") is True, "manifest approval_request_created mismatch", errors)
    req(manifest.get("approval_checklist_created") is True, "manifest approval_checklist_created mismatch", errors)
    req(manifest.get("approval_decision_input_template_created") is True, "manifest approval_decision_input_template_created mismatch", errors)
    req(manifest.get("initial_decision_record_created") is True, "manifest initial_decision_record_created mismatch", errors)
    req(manifest.get("approval_scope_summary_created") is True, "manifest approval_scope_summary_created mismatch", errors)
    req(manifest.get("approval_safety_summary_created") is True, "manifest approval_safety_summary_created mismatch", errors)
    req(manifest.get("decision_handoff_created") is True, "manifest decision_handoff_created mismatch", errors)
    req(manifest.get("approval_gate_summary_created") is True, "manifest approval_gate_summary_created mismatch", errors)
    req(manifest.get("one_shot_execution_count_target") == 1, "manifest one_shot_execution_count_target mismatch", errors)
    req(manifest.get("one_shot_execution_actual_count") == 0, "manifest one_shot_execution_actual_count mismatch", errors)
    req(manifest.get("ready_for_ls_new_14_decision") is True, "manifest ready_for_ls_new_14_decision mismatch", errors)
    req(manifest.get("recommended_next_action") == "WAIT_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION", "manifest recommended_next_action mismatch", errors)
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-14-DECISION", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)
    _validate_fixed_false(manifest, "manifest", errors)


def _validate_approval_request(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "approval-request phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST", "approval-request document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_REQUEST_READY", "approval-request status mismatch", errors)
    req(payload.get("human_approval_required") is True, "approval-request human_approval_required mismatch", errors)
    req(payload.get("approval_scope") == "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY", "approval-request approval_scope mismatch", errors)
    req(payload.get("required_approval_label") == REQ_APPROVAL_LABEL, "approval-request required_approval_label mismatch", errors)
    req(payload.get("approval_label_consumed") is False, "approval-request approval_label_consumed=true", errors)
    req(payload.get("approval_label_autofill_executed") is False, "approval-request approval_label_autofill_executed=true", errors)
    req(payload.get("auto_approval_executed") is False, "approval-request auto_approval_executed=true", errors)
    req(payload.get("ai_self_approval_executed") is False, "approval-request ai_self_approval_executed=true", errors)
    req(payload.get("post_status_target") == "draft", "approval-request post_status_target mismatch", errors)
    req(payload.get("target_post_id") is None, "approval-request target_post_id must be null", errors)
    req(payload.get("target_post_id_allocated") is False, "approval-request target_post_id_allocated=true", errors)
    req(payload.get("one_shot_execution_count_target") == 1, "approval-request one_shot_execution_count_target mismatch", errors)
    req(payload.get("one_shot_execution_actual_count") == 0, "approval-request one_shot_execution_actual_count mismatch", errors)
    req(payload.get("execution_allowed") is False, "approval-request execution_allowed=true", errors)


def _validate_approval_checklist(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "approval-checklist phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST", "approval-checklist document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_CHECKLIST_READY", "approval-checklist status mismatch", errors)
    checks = payload.get("check_items", {})
    req(bool(checks), "approval-checklist check_items missing", errors)
    for key in [
        "ls_new13_validated",
        "blocked_command_template_exists",
        "blocked_command_template_not_executable",
        "payload_map_confirmed",
        "payload_status_is_draft",
        "one_shot_execution_target_is_one",
        "one_shot_execution_actual_count_is_zero",
        "target_post_id_is_null",
        "target_post_id_allocated_false",
        "post119_update_forbidden",
        "post183_update_forbidden",
        "wordpress_draft_not_created",
        "wordpress_publish_not_executed",
        "separate_decision_required",
        "human_approval_required",
        "auto_approval_forbidden",
        "ai_self_approval_forbidden",
        "approval_label_autofill_forbidden",
        "approval_label_consumption_forbidden_in_gate",
    ]:
        req(checks.get(key) is True, f"approval-checklist {key} mismatch", errors)
    req(payload.get("all_required_checks_passed") is True, "approval-checklist all_required_checks_passed mismatch", errors)
    req(payload.get("execution_allowed") is False, "approval-checklist execution_allowed=true", errors)


def _validate_decision_input_template(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14-DECISION", "decision-input-template phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION_INPUT", "decision-input-template document_type mismatch", errors)
    req(payload.get("human_approval_completed") is False, "decision-input-template human_approval_completed=true", errors)
    req(payload.get("human_approved_for_draft_creation") is False, "decision-input-template human_approved_for_draft_creation=true", errors)
    req(payload.get("approval_label") == "", "decision-input-template approval_label mismatch", errors)
    req(payload.get("execution_allowed") is False, "decision-input-template execution_allowed=true", errors)
    req(payload.get("runner_execution_allowed") is False, "decision-input-template runner_execution_allowed=true", errors)
    req(payload.get("final_execution_command_created") is False, "decision-input-template final_execution_command_created=true", errors)
    req(payload.get("actual_executable_command_created") is False, "decision-input-template actual_executable_command_created=true", errors)
    req(payload.get("wordpress_draft_creation_allowed_for_later_phase") is False, "decision-input-template wordpress_draft_creation_allowed_for_later_phase=true", errors)
    req(payload.get("ready_for_ls_new_15") is False, "decision-input-template ready_for_ls_new_15=true", errors)


def _validate_initial_decision_record(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "initial-decision-record phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_RECORD", "initial-decision-record document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_INITIAL_DECISION_NOT_APPROVED", "initial-decision-record status mismatch", errors)
    req(payload.get("human_approval_completed") is False, "initial-decision-record human_approval_completed=true", errors)
    req(payload.get("human_approved_for_draft_creation") is False, "initial-decision-record human_approved_for_draft_creation=true", errors)
    req(payload.get("approval_label") == "", "initial-decision-record approval_label mismatch", errors)
    req(payload.get("approval_label_consumed") is False, "initial-decision-record approval_label_consumed=true", errors)
    req(payload.get("approval_label_autofill_executed") is False, "initial-decision-record approval_label_autofill_executed=true", errors)
    req(payload.get("auto_approval_executed") is False, "initial-decision-record auto_approval_executed=true", errors)
    req(payload.get("ai_self_approval_executed") is False, "initial-decision-record ai_self_approval_executed=true", errors)
    req(payload.get("ready_for_ls_new_15") is False, "initial-decision-record ready_for_ls_new_15=true", errors)
    req(payload.get("execution_allowed") is False, "initial-decision-record execution_allowed=true", errors)


def _validate_scope_summary(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "approval-scope-summary phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_SUMMARY", "approval-scope-summary document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SCOPE_READY", "approval-scope-summary status mismatch", errors)
    req(payload.get("approval_scope") == "ONE_SHOT_WORDPRESS_DRAFT_CREATION_ONLY", "approval-scope-summary approval_scope mismatch", errors)
    req(payload.get("allowed_future_execution_count_after_later_decision") == 1, "approval-scope-summary allowed_future_execution_count_after_later_decision mismatch", errors)
    req(payload.get("current_execution_count") == 0, "approval-scope-summary current_execution_count mismatch", errors)
    req(payload.get("publish_scope_allowed") is False, "approval-scope-summary publish_scope_allowed=true", errors)
    req(payload.get("update_existing_post_allowed") is False, "approval-scope-summary update_existing_post_allowed=true", errors)
    req(payload.get("target_post_id_allocation_allowed") is False, "approval-scope-summary target_post_id_allocation_allowed=true", errors)
    req(payload.get("post119_forbidden") is True, "approval-scope-summary post119_forbidden mismatch", errors)
    req(payload.get("post183_forbidden") is True, "approval-scope-summary post183_forbidden mismatch", errors)
    req(payload.get("rerun_allowed") is False, "approval-scope-summary rerun_allowed=true", errors)
    req(payload.get("publish_rerun_allowed") is False, "approval-scope-summary publish_rerun_allowed=true", errors)
    req(payload.get("execution_allowed") is False, "approval-scope-summary execution_allowed=true", errors)


def _validate_safety_summary(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "approval-safety-summary phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_SUMMARY", "approval-safety-summary document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_SAFETY_READY_NO_EXECUTION", "approval-safety-summary status mismatch", errors)
    req(payload.get("human_approval_required") is True, "approval-safety-summary human_approval_required mismatch", errors)
    for key in [
        "human_approval_completed",
        "human_approved_for_draft_creation",
        "approval_label_consumed",
        "approval_label_autofill_executed",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "actual_executable_command_created",
        "shell_execution_performed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "credential_env_read_executed",
        "target_post_id_allocated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(payload.get(key) is False, f"approval-safety-summary {key}=true", errors)
    req(payload.get("target_post_id") is None, "approval-safety-summary target_post_id must be null", errors)


def _validate_decision_handoff(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-14", "decision-handoff phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW14_DECISION_HANDOFF", "decision-handoff document_type mismatch", errors)
    req(payload.get("status") == "LSNEW14_DECISION_HANDOFF_READY", "decision-handoff status mismatch", errors)
    req(payload.get("next_phase") == "LS-NEW-14-DECISION", "decision-handoff next_phase mismatch", errors)
    req(payload.get("next_phase_name") == "Separate Draft Creation Execution Approval Decision", "decision-handoff next_phase_name mismatch", errors)
    req(payload.get("handoff_ready") is True, "decision-handoff handoff_ready mismatch", errors)
    req(payload.get("ready_for_ls_new_14_decision") is True, "decision-handoff ready_for_ls_new_14_decision mismatch", errors)
    req(payload.get("ready_for_ls_new_15") is False, "decision-handoff ready_for_ls_new_15=true", errors)
    req(payload.get("required_approval_label") == REQ_APPROVAL_LABEL, "decision-handoff required_approval_label mismatch", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-14", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == REQ_RUN, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == PROD, "result production_status mismatch", errors)
    req(result.get("ls_new13_validated") is True, "result ls_new13_validated mismatch", errors)
    req(result.get("ls_new13_command_prep_ready") is True, "result ls_new13_command_prep_ready mismatch", errors)
    req(result.get("human_approval_required") is True, "result human_approval_required mismatch", errors)
    req(result.get("required_approval_label") == REQ_APPROVAL_LABEL, "result required_approval_label mismatch", errors)
    req(result.get("approval_label") == "", "result approval_label mismatch", errors)
    req(result.get("approval_gate_manifest_created") is True, "result approval_gate_manifest_created mismatch", errors)
    req(result.get("approval_request_created") is True, "result approval_request_created mismatch", errors)
    req(result.get("approval_checklist_created") is True, "result approval_checklist_created mismatch", errors)
    req(result.get("approval_decision_input_template_created") is True, "result approval_decision_input_template_created mismatch", errors)
    req(result.get("initial_decision_record_created") is True, "result initial_decision_record_created mismatch", errors)
    req(result.get("approval_scope_summary_created") is True, "result approval_scope_summary_created mismatch", errors)
    req(result.get("approval_safety_summary_created") is True, "result approval_safety_summary_created mismatch", errors)
    req(result.get("decision_handoff_created") is True, "result decision_handoff_created mismatch", errors)
    req(result.get("approval_gate_summary_created") is True, "result approval_gate_summary_created mismatch", errors)
    req(result.get("one_shot_execution_count_target") == 1, "result one_shot_execution_count_target mismatch", errors)
    req(result.get("one_shot_execution_actual_count") == 0, "result one_shot_execution_actual_count mismatch", errors)
    req(result.get("ready_for_ls_new_14_decision") is True, "result ready_for_ls_new_14_decision mismatch", errors)
    req(result.get("recommended_next_action") == "WAIT_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_DECISION", "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-14-DECISION", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)
    _validate_fixed_false(result, "result", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-14", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "human_approval_completed",
        "human_approved_for_draft_creation",
        "approval_label_consumed",
        "approval_label_autofill_executed",
        "auto_approval_executed",
        "ai_self_approval_executed",
        "actual_executable_command_created",
        "shell_execution_performed",
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "credential_env_read_executed",
        "target_post_id_allocated",
        "ready_for_ls_new_15",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _validate_summary(summary_text: str, errors: list[str]) -> None:
    req("# LS-NEW-14 Separate Draft Creation Execution Approval Gate Summary" in summary_text, "summary header mismatch", errors)
    req("- Human approval required: true" in summary_text, "summary human_approval_required mismatch", errors)
    req("- Human approval completed: false" in summary_text, "summary human_approval_completed mismatch", errors)
    req("- Human approved for draft creation: false" in summary_text, "summary human_approved_for_draft_creation mismatch", errors)
    req("- Execution allowed: false" in summary_text, "summary execution_allowed mismatch", errors)
    req("- Actual executable command created: false" in summary_text, "summary actual_executable_command_created mismatch", errors)
    req("- Shell execution performed: false" in summary_text, "summary shell_execution_performed mismatch", errors)
    req("- Ready for LS-NEW-14-DECISION: true" in summary_text, "summary ready_for_ls_new_14_decision mismatch", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-14 Draft Creation Execution Approval Gate Validation Report",
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
    manifest = try_load_json(Path(args.manifest), errors, "manifest")
    approval_request = try_load_json(Path(args.approval_request), errors, "approval-request")
    approval_checklist = try_load_json(Path(args.approval_checklist), errors, "approval-checklist")
    decision_input_template = try_load_json(Path(args.decision_input_template), errors, "decision-input-template")
    initial_decision_record = try_load_json(Path(args.initial_decision_record), errors, "initial-decision-record")
    approval_scope_summary = try_load_json(Path(args.approval_scope_summary), errors, "approval-scope-summary")
    approval_safety_summary = try_load_json(Path(args.approval_safety_summary), errors, "approval-safety-summary")
    decision_handoff = try_load_json(Path(args.decision_handoff), errors, "decision-handoff")
    summary = try_load_text(Path(args.summary), errors, "summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls13_validation = try_load_json(Path(args.ls_new13_validation_result), errors, "ls-new13-validation-result")

    req(policy.get("phase") == "LS-NEW-14", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-14", "schema phase mismatch", errors)
    req(ls13_validation.get("validation_status") == REQ_LS13_VALID, "ls-new13 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_approval_request(approval_request, errors)
    _validate_approval_checklist(approval_checklist, errors)
    _validate_decision_input_template(decision_input_template, errors)
    _validate_initial_decision_record(initial_decision_record, errors)
    _validate_scope_summary(approval_scope_summary, errors)
    _validate_safety_summary(approval_safety_summary, errors)
    _validate_decision_handoff(decision_handoff, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)
    _validate_summary(summary, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-14",
        "document_type": "START_LS_NEW14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_VALIDATION_RESULT",
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
