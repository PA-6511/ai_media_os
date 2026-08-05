#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW10_EXECUTION_PREP_VALIDATED_NO_DRAFT_CREATION"
NOT_VALID = "LSNEW10_EXECUTION_PREP_NOT_VALIDATED"
RUN_READY = "LSNEW10_EXECUTION_PREP_READY_NO_DRAFT_CREATION"
MODE = "EXECUTION_PREP_ONLY_NO_DRAFT_CREATION"
PROD = "NO_EXECUTION_EXECUTION_PREP_ONLY"
REQ_LS9_VALID = "LSNEW9_DECISION_VALIDATED_NO_EXECUTION"
REQ_NEXT = "BEGIN_LS_NEW_11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new10_execution_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new10_execution_prep_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new10_execution_prep_manifest.json")
    p.add_argument("--input-map", default="exchange/new_release/start_ls_new10_execution_input_map.json")
    p.add_argument("--dry-boundary", default="exchange/new_release/start_ls_new10_draft_creation_dry_boundary.json")
    p.add_argument("--credential-handoff", default="exchange/new_release/start_ls_new10_credential_preflight_handoff_request.json")
    p.add_argument("--blocked-command-template", default="exchange/new_release/start_ls_new10_blocked_execution_command_template.md")
    p.add_argument("--safety-summary", default="exchange/new_release/start_ls_new10_execution_prep_safety_summary.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new10_execution_prep_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new10_execution_prep_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new10_execution_prep.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new10_execution_prep_result.json")
    p.add_argument("--ls-new9-decision-validation-result", default="exchange/logs/start_ls_new9_decision_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new10_execution_prep_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new10_execution_prep_validation_report.md")
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


def _req_false_block(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in [
        "execution_allowed",
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
        "approval_label_consumed",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ]:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)
    req(payload.get("target_post_id") is None, f"{prefix} target_post_id must be null", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-10", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW10_EXECUTION_PREP_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == PROD, "result production_status mismatch", errors)
    req(result.get("ls_new9_decision_validated") is True, "result ls_new9_decision_validated mismatch", errors)
    req(result.get("ls_new9_decision_approved") is True, "result ls_new9_decision_approved mismatch", errors)
    for key in [
        "execution_prep_manifest_created",
        "execution_input_map_created",
        "draft_creation_dry_boundary_created",
        "credential_preflight_handoff_request_created",
        "blocked_execution_command_template_created",
        "execution_prep_safety_summary_created",
        "execution_prep_summary_created",
    ]:
        req(result.get(key) is True, f"result {key} mismatch", errors)
    req(result.get("content_item_id") == "new-comic-001", "result content_item_id mismatch", errors)
    req(result.get("title") == "月曜日のたわわ", "result title mismatch", errors)
    req(result.get("volume") == "第15巻", "result volume mismatch", errors)
    req(result.get("author") == "比村奇石", "result author mismatch", errors)
    req(result.get("publisher") == "講談社", "result publisher mismatch", errors)
    req(result.get("release_date") == "2026-07-06", "result release_date mismatch", errors)
    req(result.get("post_status_target") == "draft", "result post_status_target mismatch", errors)
    _req_false_block(result, "result", errors)
    req(result.get("ready_for_ls_new_11") is True, "result ready_for_ls_new_11 mismatch", errors)
    req(result.get("recommended_next_action") == REQ_NEXT, "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-11", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-10", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW10_EXECUTION_PREP_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == RUN_READY, "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new9_decision_validated") is True, "manifest ls_new9_decision_validated mismatch", errors)
    req(manifest.get("ls_new9_decision_approved") is True, "manifest ls_new9_decision_approved mismatch", errors)
    _req_false_block(manifest, "manifest", errors)
    req(manifest.get("ready_for_ls_new_11") is True, "manifest ready_for_ls_new_11 mismatch", errors)


def _validate_input_map(input_map: dict[str, Any], errors: list[str]) -> None:
    req(input_map.get("phase") == "LS-NEW-10", "input-map phase mismatch", errors)
    req(input_map.get("document_type") == "START_LS_NEW10_EXECUTION_INPUT_MAP", "input-map document_type mismatch", errors)
    req(input_map.get("status") == "LSNEW10_EXECUTION_INPUT_MAP_READY_NO_DRAFT_CREATION", "input-map status mismatch", errors)
    req(input_map.get("credential_source") is None, "input-map credential_source must be null", errors)
    req(input_map.get("credential_env_path_recorded") is False, "input-map credential_env_path_recorded mismatch", errors)
    req(input_map.get("credential_env_read_executed") is False, "input-map credential_env_read_executed=true", errors)
    req(input_map.get("credential_existence_check_executed") is False, "input-map credential_existence_check_executed=true", errors)
    req(input_map.get("target_post_id") is None, "input-map target_post_id must be null", errors)
    req(input_map.get("target_post_id_allocated") is False, "input-map target_post_id_allocated=true", errors)
    req(input_map.get("execution_allowed") is False, "input-map execution_allowed=true", errors)


def _validate_dry_boundary(dry_boundary: dict[str, Any], errors: list[str]) -> None:
    req(dry_boundary.get("phase") == "LS-NEW-10", "dry-boundary phase mismatch", errors)
    req(dry_boundary.get("document_type") == "START_LS_NEW10_DRAFT_CREATION_DRY_BOUNDARY", "dry-boundary document_type mismatch", errors)
    req(dry_boundary.get("status") == "LSNEW10_DRAFT_CREATION_DRY_BOUNDARY_READY_NO_DRAFT_CREATION", "dry-boundary status mismatch", errors)
    req(dry_boundary.get("draft_creation_planned_for_later_phase") is True, "dry-boundary draft_creation_planned_for_later_phase mismatch", errors)
    req(dry_boundary.get("draft_creation_executed_in_current_phase") is False, "dry-boundary draft_creation_executed_in_current_phase=true", errors)
    req(dry_boundary.get("wordpress_api_call_executed") is False, "dry-boundary wordpress_api_call_executed=true", errors)
    req(dry_boundary.get("wordpress_draft_created") is False, "dry-boundary wordpress_draft_created=true", errors)
    req(dry_boundary.get("target_post_id") is None, "dry-boundary target_post_id must be null", errors)
    req(dry_boundary.get("target_post_id_allocated") is False, "dry-boundary target_post_id_allocated=true", errors)
    req(dry_boundary.get("execution_allowed") is False, "dry-boundary execution_allowed=true", errors)


def _validate_credential_handoff(credential_handoff: dict[str, Any], errors: list[str]) -> None:
    req(credential_handoff.get("phase") == "LS-NEW-10", "credential-handoff phase mismatch", errors)
    req(credential_handoff.get("document_type") == "START_LS_NEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST", "credential-handoff document_type mismatch", errors)
    req(
        credential_handoff.get("status") == "LSNEW10_CREDENTIAL_PREFLIGHT_HANDOFF_REQUEST_READY_NO_CREDENTIAL_READ",
        "credential-handoff status mismatch",
        errors,
    )
    req(credential_handoff.get("next_phase") == "LS-NEW-11", "credential-handoff next_phase mismatch", errors)
    req(
        credential_handoff.get("next_phase_name") == "Credential and WordPress Connectivity Preflight",
        "credential-handoff next_phase_name mismatch",
        errors,
    )
    req(credential_handoff.get("credential_env_read_executed") is False, "credential-handoff credential_env_read_executed=true", errors)
    req(credential_handoff.get("credential_existence_check_executed") is False, "credential-handoff credential_existence_check_executed=true", errors)
    req(credential_handoff.get("credential_value_output") is False, "credential-handoff credential_value_output=true", errors)
    req(credential_handoff.get("credential_secret_output") is False, "credential-handoff credential_secret_output=true", errors)
    req(credential_handoff.get("execution_allowed") is False, "credential-handoff execution_allowed=true", errors)
    req(credential_handoff.get("handoff_ready") is True, "credential-handoff handoff_ready mismatch", errors)


def _validate_safety(safety: dict[str, Any], errors: list[str]) -> None:
    req(safety.get("phase") == "LS-NEW-10", "safety-summary phase mismatch", errors)
    req(safety.get("document_type") == "START_LS_NEW10_EXECUTION_PREP_SAFETY_SUMMARY", "safety-summary document_type mismatch", errors)
    req(safety.get("status") == "LSNEW10_EXECUTION_PREP_SAFETY_SUMMARY_READY_NO_DRAFT_CREATION", "safety-summary status mismatch", errors)
    _req_false_block(safety, "safety-summary", errors)
    req(safety.get("ready_for_ls_new_11") is True, "safety-summary ready_for_ls_new_11 mismatch", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-10", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW10_EXECUTION_PREP_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW10_EXECUTION_PREP_LOCKED_NO_DRAFT_CREATION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
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
        "credential_existence_check_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _validate_texts(blocked_text: str, summary_text: str, errors: list[str]) -> None:
    req("This is not an executable command." in blocked_text, "blocked command template missing non-executable statement", errors)
    req("Execution allowed: false" in blocked_text, "blocked command template missing execution allowed false", errors)
    req("WordPress draft creation allowed: false" in blocked_text, "blocked command template missing draft creation allowed false", errors)
    req("# LS-NEW-10 Execution Prep Summary" in summary_text, "summary header mismatch", errors)
    req("- Ready for LS-NEW-11: true" in summary_text, "summary ready_for_ls_new_11 mismatch", errors)
    req("WordPress下書き作成" in summary_text, "summary explanatory sentence missing", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-10 Execution Prep Validation Report",
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
    input_map = try_load_json(Path(args.input_map), errors, "input-map")
    dry_boundary = try_load_json(Path(args.dry_boundary), errors, "dry-boundary")
    credential_handoff = try_load_json(Path(args.credential_handoff), errors, "credential-handoff")
    safety_summary = try_load_json(Path(args.safety_summary), errors, "safety-summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls9_validation = try_load_json(Path(args.ls_new9_decision_validation_result), errors, "ls-new9-decision-validation-result")
    blocked_template = try_load_text(Path(args.blocked_command_template), errors, "blocked-command-template")
    summary_text = try_load_text(Path(args.summary), errors, "summary")

    req(policy.get("phase") == "LS-NEW-10", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-10", "schema phase mismatch", errors)
    req(ls9_validation.get("validation_status") == REQ_LS9_VALID, "ls-new9 decision validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_input_map(input_map, errors)
    _validate_dry_boundary(dry_boundary, errors)
    _validate_credential_handoff(credential_handoff, errors)
    _validate_safety(safety_summary, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)
    _validate_texts(blocked_template, summary_text, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-10",
        "document_type": "START_LS_NEW10_EXECUTION_PREP_VALIDATION_RESULT",
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