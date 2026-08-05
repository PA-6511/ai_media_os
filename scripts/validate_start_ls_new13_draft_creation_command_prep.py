#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_NOT_VALIDATED"
REQ_RUN = "LSNEW13_DRAFT_CREATION_COMMAND_PREP_READY_NO_EXECUTION"
REQ_LS12_VALID = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"
MODE = "DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION"
PROD = "NO_EXECUTION_DRAFT_CREATION_COMMAND_PREP_ONLY"
KEY_B64 = "base" + "64_auth_output"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new13_draft_creation_command_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new13_draft_creation_command_prep_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new13_draft_creation_command_prep_manifest.json")
    p.add_argument("--payload-map", default="exchange/new_release/start_ls_new13_draft_creation_payload_map.json")
    p.add_argument("--blocked-command-template", default="exchange/new_release/start_ls_new13_blocked_draft_creation_command_template.md")
    p.add_argument("--one-shot-boundary", default="exchange/new_release/start_ls_new13_one_shot_draft_creation_boundary.json")
    p.add_argument("--pre-execution-checklist", default="exchange/new_release/start_ls_new13_pre_execution_checklist.json")
    p.add_argument("--no-execution-safety-contract", default="exchange/new_release/start_ls_new13_no_execution_safety_contract.json")
    p.add_argument("--next-phase-approval-handoff", default="exchange/new_release/start_ls_new13_next_phase_approval_handoff.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new13_draft_creation_command_prep_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new13_draft_creation_command_prep_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new13_draft_creation_command_prep.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new13_draft_creation_command_prep_result.json")
    p.add_argument("--ls-new12-validation-result", default="exchange/logs/start_ls_new12_authenticated_wp_read_preflight_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new13_draft_creation_command_prep_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new13_draft_creation_command_prep_validation_report.md")
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
        "approval_label_consumed",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    keys.append(KEY_B64)
    for key in keys:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)
    req(payload.get("target_post_id") is None, f"{prefix} target_post_id must be null", errors)


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-13", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == REQ_RUN, "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new12_validated") is True, "manifest ls_new12_validated mismatch", errors)
    req(manifest.get("ls_new12_authenticated_read_ready") is True, "manifest ls_new12_authenticated_read_ready mismatch", errors)
    req(manifest.get("draft_creation_command_prep_manifest_created") is True, "manifest draft_creation_command_prep_manifest_created mismatch", errors)
    req(manifest.get("draft_creation_payload_map_created") is True, "manifest draft_creation_payload_map_created mismatch", errors)
    req(manifest.get("blocked_draft_creation_command_template_created") is True, "manifest blocked_draft_creation_command_template_created mismatch", errors)
    req(manifest.get("one_shot_draft_creation_boundary_created") is True, "manifest one_shot_draft_creation_boundary_created mismatch", errors)
    req(manifest.get("pre_execution_checklist_created") is True, "manifest pre_execution_checklist_created mismatch", errors)
    req(manifest.get("no_execution_safety_contract_created") is True, "manifest no_execution_safety_contract_created mismatch", errors)
    req(manifest.get("next_phase_approval_handoff_created") is True, "manifest next_phase_approval_handoff_created mismatch", errors)
    req(manifest.get("command_prep_summary_created") is True, "manifest command_prep_summary_created mismatch", errors)
    req(manifest.get("one_shot_execution_count_target") == 1, "manifest one_shot_execution_count_target mismatch", errors)
    req(manifest.get("one_shot_execution_actual_count") == 0, "manifest one_shot_execution_actual_count mismatch", errors)
    req(manifest.get("ready_for_ls_new_14") is True, "manifest ready_for_ls_new_14 mismatch", errors)
    req(
        manifest.get("recommended_next_action")
        == "BEGIN_LS_NEW_14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "manifest recommended_next_action mismatch",
        errors,
    )
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-14", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)
    _validate_fixed_false(manifest, "manifest", errors)


def _validate_payload_map(payload_map: dict[str, Any], errors: list[str]) -> None:
    req(payload_map.get("phase") == "LS-NEW-13", "payload-map phase mismatch", errors)
    req(payload_map.get("document_type") == "START_LS_NEW13_DRAFT_CREATION_PAYLOAD_MAP", "payload-map document_type mismatch", errors)
    req(payload_map.get("status") == "LSNEW13_DRAFT_CREATION_PAYLOAD_MAP_READY_NO_EXECUTION", "payload-map status mismatch", errors)
    req(payload_map.get("post_status_target") == "draft", "payload-map post_status_target mismatch", errors)
    req(payload_map.get("target_post_id") is None, "payload-map target_post_id must be null", errors)
    req(payload_map.get("target_post_id_allocated") is False, "payload-map target_post_id_allocated mismatch", errors)
    req(payload_map.get("payload_title_confirmed") is True, "payload-map payload_title_confirmed mismatch", errors)
    req(payload_map.get("payload_body_present") is True, "payload-map payload_body_present mismatch", errors)
    req(payload_map.get("payload_status_draft_confirmed") is True, "payload-map payload_status_draft_confirmed mismatch", errors)
    req(payload_map.get("payload_source_not_modified") is True, "payload-map payload_source_not_modified mismatch", errors)
    req(payload_map.get("execution_allowed") is False, "payload-map execution_allowed=true", errors)


def _validate_blocked_template(text: str, errors: list[str]) -> None:
    req("# LS-NEW-13 Blocked Draft Creation Command Template" in text, "blocked-template header mismatch", errors)
    req("This is not an executable command." in text, "blocked-template executable warning missing", errors)
    req("Do not run" in text, "blocked-template do-not-run warning missing", errors)
    req("Execution allowed: false" in text, "blocked-template execution_allowed mismatch", errors)


def _validate_one_shot_boundary(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-13", "one-shot-boundary phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY", "one-shot-boundary document_type mismatch", errors)
    req(payload.get("status") == "LSNEW13_ONE_SHOT_DRAFT_CREATION_BOUNDARY_READY_NO_EXECUTION", "one-shot-boundary status mismatch", errors)
    req(payload.get("one_shot_draft_creation_planned") is True, "one-shot-boundary one_shot_draft_creation_planned mismatch", errors)
    req(payload.get("one_shot_execution_count_target") == 1, "one-shot-boundary one_shot_execution_count_target mismatch", errors)
    req(payload.get("one_shot_execution_actual_count") == 0, "one-shot-boundary one_shot_execution_actual_count mismatch", errors)
    req(payload.get("draft_creation_executed_in_current_phase") is False, "one-shot-boundary draft_creation_executed_in_current_phase=true", errors)
    req(payload.get("wordpress_draft_created") is False, "one-shot-boundary wordpress_draft_created=true", errors)
    req(payload.get("target_post_id") is None, "one-shot-boundary target_post_id must be null", errors)
    req(payload.get("target_post_id_allocated") is False, "one-shot-boundary target_post_id_allocated=true", errors)
    req(payload.get("rerun_allowed") is False, "one-shot-boundary rerun_allowed=true", errors)
    req(payload.get("publish_rerun_allowed") is False, "one-shot-boundary publish_rerun_allowed=true", errors)
    req(payload.get("execution_allowed") is False, "one-shot-boundary execution_allowed=true", errors)


def _validate_checklist(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-13", "pre-execution-checklist phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW13_PRE_EXECUTION_CHECKLIST", "pre-execution-checklist document_type mismatch", errors)
    req(payload.get("status") == "LSNEW13_PRE_EXECUTION_CHECKLIST_READY_NO_EXECUTION", "pre-execution-checklist status mismatch", errors)
    check_items = payload.get("check_items", {})
    req(bool(check_items), "pre-execution-checklist check_items missing", errors)
    req(check_items.get("ls_new12_authenticated_read_validated") is True, "pre-execution-checklist ls_new12_authenticated_read_validated mismatch", errors)
    req(check_items.get("payload_source_confirmed") is True, "pre-execution-checklist payload_source_confirmed mismatch", errors)
    req(check_items.get("payload_status_is_draft") is True, "pre-execution-checklist payload_status_is_draft mismatch", errors)
    req(check_items.get("target_post_id_is_null") is True, "pre-execution-checklist target_post_id_is_null mismatch", errors)
    req(check_items.get("target_post_id_allocated") is False, "pre-execution-checklist target_post_id_allocated mismatch", errors)
    req(check_items.get("execution_allowed") is False, "pre-execution-checklist execution_allowed mismatch", errors)
    req(payload.get("all_required_checks_passed") is True, "pre-execution-checklist all_required_checks_passed mismatch", errors)


def _validate_no_exec_contract(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-13", "no-execution-safety-contract phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW13_NO_EXECUTION_SAFETY_CONTRACT", "no-execution-safety-contract document_type mismatch", errors)
    req(payload.get("status") == "LSNEW13_NO_EXECUTION_SAFETY_CONTRACT_READY", "no-execution-safety-contract status mismatch", errors)
    req(payload.get("no_execution_required") is True, "no-execution-safety-contract no_execution_required mismatch", errors)
    for key in [
        "wordpress_api_call_allowed",
        "wordpress_post_allowed",
        "wordpress_put_allowed",
        "wordpress_patch_allowed",
        "wordpress_delete_allowed",
        "wordpress_draft_create_allowed",
        "wordpress_publish_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "actual_executable_command_created",
        "shell_execution_allowed",
        "credential_env_read_allowed",
        "target_post_id_allocation_allowed",
        "execution_allowed",
    ]:
        req(payload.get(key) is False, f"no-execution-safety-contract {key}=true", errors)


def _validate_handoff(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-13", "handoff phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW13_NEXT_PHASE_APPROVAL_HANDOFF", "handoff document_type mismatch", errors)
    req(payload.get("status") == "LSNEW13_NEXT_PHASE_APPROVAL_HANDOFF_READY", "handoff status mismatch", errors)
    req(payload.get("next_phase") == "LS-NEW-14", "handoff next_phase mismatch", errors)
    req(payload.get("next_phase_name") == "Separate Draft Creation Execution Approval Gate", "handoff next_phase_name mismatch", errors)
    req(payload.get("handoff_ready") is True, "handoff handoff_ready mismatch", errors)
    req(payload.get("ready_for_ls_new_14") is True, "handoff ready_for_ls_new_14 mismatch", errors)
    req(
        payload.get("required_approval_label_next_phase")
        == "APPROVED_FOR_LS_NEW_14_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_ONLY",
        "handoff required_approval_label_next_phase mismatch",
        errors,
    )


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-13", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == REQ_RUN, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == PROD, "result production_status mismatch", errors)
    req(result.get("ls_new12_validated") is True, "result ls_new12_validated mismatch", errors)
    req(result.get("ls_new12_authenticated_read_ready") is True, "result ls_new12_authenticated_read_ready mismatch", errors)
    req(result.get("draft_creation_command_prep_manifest_created") is True, "result draft_creation_command_prep_manifest_created mismatch", errors)
    req(result.get("draft_creation_payload_map_created") is True, "result draft_creation_payload_map_created mismatch", errors)
    req(result.get("blocked_draft_creation_command_template_created") is True, "result blocked_draft_creation_command_template_created mismatch", errors)
    req(result.get("one_shot_draft_creation_boundary_created") is True, "result one_shot_draft_creation_boundary_created mismatch", errors)
    req(result.get("pre_execution_checklist_created") is True, "result pre_execution_checklist_created mismatch", errors)
    req(result.get("no_execution_safety_contract_created") is True, "result no_execution_safety_contract_created mismatch", errors)
    req(result.get("next_phase_approval_handoff_created") is True, "result next_phase_approval_handoff_created mismatch", errors)
    req(result.get("command_prep_summary_created") is True, "result command_prep_summary_created mismatch", errors)
    req(result.get("one_shot_execution_count_target") == 1, "result one_shot_execution_count_target mismatch", errors)
    req(result.get("one_shot_execution_actual_count") == 0, "result one_shot_execution_actual_count mismatch", errors)
    req(result.get("ready_for_ls_new_14") is True, "result ready_for_ls_new_14 mismatch", errors)
    req(
        result.get("recommended_next_action")
        == "BEGIN_LS_NEW_14_SEPARATE_DRAFT_CREATION_EXECUTION_APPROVAL_GATE_NO_EXECUTION",
        "result recommended_next_action mismatch",
        errors,
    )
    _validate_fixed_false(result, "result", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-13", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW13_DRAFT_CREATION_COMMAND_PREP_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
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
        "credential_env_read_executed",
        "target_post_id_allocated",
        "approval_label_consumed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _validate_summary(summary_text: str, errors: list[str]) -> None:
    req("# LS-NEW-13 Draft Creation Command Prep Summary" in summary_text, "summary header mismatch", errors)
    req("- Execution allowed: false" in summary_text, "summary execution allowed mismatch", errors)
    req("- Actual executable command created: false" in summary_text, "summary actual executable command mismatch", errors)
    req("- Shell execution performed: false" in summary_text, "summary shell execution mismatch", errors)
    req("- Ready for LS-NEW-14: true" in summary_text, "summary ready_for_ls_new_14 mismatch", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-13 Draft Creation Command Prep Validation Report",
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
    payload_map = try_load_json(Path(args.payload_map), errors, "payload-map")
    blocked_template = try_load_text(Path(args.blocked_command_template), errors, "blocked-command-template")
    one_shot_boundary = try_load_json(Path(args.one_shot_boundary), errors, "one-shot-boundary")
    pre_execution_checklist = try_load_json(Path(args.pre_execution_checklist), errors, "pre-execution-checklist")
    no_execution_safety_contract = try_load_json(Path(args.no_execution_safety_contract), errors, "no-execution-safety-contract")
    next_phase_handoff = try_load_json(Path(args.next_phase_approval_handoff), errors, "next-phase-approval-handoff")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls12_validation = try_load_json(Path(args.ls_new12_validation_result), errors, "ls-new12-validation-result")
    summary = try_load_text(Path(args.summary), errors, "summary")

    req(policy.get("phase") == "LS-NEW-13", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-13", "schema phase mismatch", errors)
    req(ls12_validation.get("validation_status") == REQ_LS12_VALID, "ls-new12 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_payload_map(payload_map, errors)
    _validate_blocked_template(blocked_template, errors)
    _validate_one_shot_boundary(one_shot_boundary, errors)
    _validate_checklist(pre_execution_checklist, errors)
    _validate_no_exec_contract(no_execution_safety_contract, errors)
    _validate_handoff(next_phase_handoff, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)
    _validate_summary(summary, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-13",
        "document_type": "START_LS_NEW13_DRAFT_CREATION_COMMAND_PREP_VALIDATION_RESULT",
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
