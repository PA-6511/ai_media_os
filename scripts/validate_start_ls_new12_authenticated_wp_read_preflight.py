#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATED_NO_WRITE"
NOT_VALID = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_NOT_VALIDATED"
REQ_RUN = "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_READY_NO_WRITE"
REQ_LS11_VALID = "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"
MODE = "AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE"
PROD = "NO_WRITE_AUTHENTICATED_READ_PREFLIGHT_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new12_authenticated_wp_read_preflight_policy.json")
    p.add_argument("--schema", default="config/start_ls_new12_authenticated_wp_read_preflight_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new12_authenticated_wp_read_preflight_manifest.json")
    p.add_argument("--authenticated-read-result", default="exchange/new_release/start_ls_new12_authenticated_wp_read_result.json")
    p.add_argument("--secret-non-output-summary", default="exchange/new_release/start_ls_new12_secret_non_output_summary.json")
    p.add_argument("--no-write-safety-contract", default="exchange/new_release/start_ls_new12_no_write_safety_contract.json")
    p.add_argument("--draft-creation-hold-boundary", default="exchange/new_release/start_ls_new12_draft_creation_hold_boundary.json")
    p.add_argument("--next-phase-handoff", default="exchange/new_release/start_ls_new12_next_phase_handoff.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new12_authenticated_wp_read_preflight_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new12_authenticated_wp_read_preflight_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new12_authenticated_wp_read_preflight.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new12_authenticated_wp_read_preflight_result.json")
    p.add_argument("--ls-new11-validation-result", default="exchange/logs/start_ls_new11_credential_wp_connectivity_preflight_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new12_authenticated_wp_read_preflight_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new12_authenticated_wp_read_preflight_validation_report.md")
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


def _validate_no_write_block(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in [
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
        "x_api_call_executed",
        "x_post_executed",
        "generic_external_fetch_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
    ]:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)
    req(payload.get("target_post_id") is None, f"{prefix} target_post_id must be null", errors)


def _validate_secret_non_output_block(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in [
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "response_body_output",
        "user_identity_output",
        "wordpress_authenticated_read_response_body_saved",
        "wordpress_authenticated_user_identity_saved",
    ]:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-12", "manifest phase mismatch", errors)
    req(
        manifest.get("document_type") == "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_MANIFEST",
        "manifest document_type mismatch",
        errors,
    )
    req(manifest.get("status") == REQ_RUN, "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new11_validated") is True, "manifest ls_new11_validated mismatch", errors)
    req(manifest.get("ls_new11_ready") is True, "manifest ls_new11_ready mismatch", errors)
    req(manifest.get("credential_env_exists") is True, "manifest credential_env_exists mismatch", errors)
    req(manifest.get("credential_existence_check_executed") is True, "manifest credential_existence_check_executed mismatch", errors)
    req(manifest.get("credential_env_read_executed") is True, "manifest credential_env_read_executed mismatch", errors)
    req(manifest.get("wordpress_authenticated_read_get_attempted") is True, "manifest wordpress_authenticated_read_get_attempted mismatch", errors)
    req(manifest.get("wordpress_authenticated_read_get_succeeded") is True, "manifest wordpress_authenticated_read_get_succeeded mismatch", errors)
    req(manifest.get("wordpress_authenticated_read_status_class") == "2xx", "manifest wordpress_authenticated_read_status_class mismatch", errors)
    req(manifest.get("wordpress_authenticated_read_endpoint_kind") == "users_me", "manifest wordpress_authenticated_read_endpoint_kind mismatch", errors)
    _validate_secret_non_output_block(manifest, "manifest", errors)
    _validate_no_write_block(manifest, "manifest", errors)
    req(manifest.get("ready_for_ls_new_13") is True, "manifest ready_for_ls_new_13 mismatch", errors)
    req(
        manifest.get("recommended_next_action") == "BEGIN_LS_NEW_13_DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION",
        "manifest recommended_next_action mismatch",
        errors,
    )
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-13", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)


def _validate_authenticated_read_result(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-12", "authenticated-read-result phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW12_AUTHENTICATED_WP_READ_RESULT", "authenticated-read-result document_type mismatch", errors)
    req(payload.get("status") == "LSNEW12_AUTHENTICATED_WP_READ_READY_NO_WRITE", "authenticated-read-result status mismatch", errors)
    req(payload.get("wordpress_authenticated_read_get_attempted") is True, "authenticated-read-result wordpress_authenticated_read_get_attempted mismatch", errors)
    req(payload.get("wordpress_authenticated_read_get_succeeded") is True, "authenticated-read-result wordpress_authenticated_read_get_succeeded mismatch", errors)
    req(payload.get("wordpress_authenticated_read_status_class") == "2xx", "authenticated-read-result wordpress_authenticated_read_status_class mismatch", errors)
    req(payload.get("wordpress_authenticated_read_endpoint_kind") == "users_me", "authenticated-read-result wordpress_authenticated_read_endpoint_kind mismatch", errors)
    req(payload.get("wordpress_write_executed") is False, "authenticated-read-result wordpress_write_executed=true", errors)
    req(payload.get("wordpress_draft_created") is False, "authenticated-read-result wordpress_draft_created=true", errors)
    req(payload.get("wordpress_publish_executed") is False, "authenticated-read-result wordpress_publish_executed=true", errors)
    req(payload.get("execution_allowed") is False, "authenticated-read-result execution_allowed=true", errors)
    _validate_secret_non_output_block(payload, "authenticated-read-result", errors)


def _validate_secret_non_output_summary(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-12", "secret-non-output-summary phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW12_SECRET_NON_OUTPUT_SUMMARY", "secret-non-output-summary document_type mismatch", errors)
    req(payload.get("status") == "LSNEW12_SECRET_NON_OUTPUT_CONFIRMED", "secret-non-output-summary status mismatch", errors)
    req(payload.get("credential_env_read_executed") is True, "secret-non-output-summary credential_env_read_executed mismatch", errors)
    _validate_secret_non_output_block(payload, "secret-non-output-summary", errors)


def _validate_no_write_contract(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-12", "no-write-contract phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW12_NO_WRITE_SAFETY_CONTRACT", "no-write-contract document_type mismatch", errors)
    req(payload.get("status") == "LSNEW12_NO_WRITE_SAFETY_CONTRACT_READY", "no-write-contract status mismatch", errors)
    req(payload.get("no_write_required") is True, "no-write-contract no_write_required mismatch", errors)
    req(payload.get("wordpress_get_only") is True, "no-write-contract wordpress_get_only mismatch", errors)
    for key in [
        "wordpress_post_allowed",
        "wordpress_put_allowed",
        "wordpress_patch_allowed",
        "wordpress_delete_allowed",
        "wordpress_draft_create_allowed",
        "wordpress_publish_allowed",
        "wordpress_update_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "target_post_id_allocation_allowed",
        "execution_allowed",
    ]:
        req(payload.get(key) is False, f"no-write-contract {key}=true", errors)


def _validate_draft_hold_boundary(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-12", "draft-hold-boundary phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW12_DRAFT_CREATION_HOLD_BOUNDARY", "draft-hold-boundary document_type mismatch", errors)
    req(payload.get("status") == "LSNEW12_DRAFT_CREATION_HOLD_BOUNDARY_READY_NO_DRAFT_CREATION", "draft-hold-boundary status mismatch", errors)
    req(payload.get("draft_creation_still_blocked") is True, "draft-hold-boundary draft_creation_still_blocked mismatch", errors)
    req(payload.get("draft_creation_executed_in_current_phase") is False, "draft-hold-boundary draft_creation_executed_in_current_phase=true", errors)
    req(payload.get("wordpress_draft_created") is False, "draft-hold-boundary wordpress_draft_created=true", errors)
    req(payload.get("target_post_id") is None, "draft-hold-boundary target_post_id must be null", errors)
    req(payload.get("target_post_id_allocated") is False, "draft-hold-boundary target_post_id_allocated=true", errors)
    req(payload.get("execution_allowed") is False, "draft-hold-boundary execution_allowed=true", errors)


def _validate_handoff(payload: dict[str, Any], errors: list[str]) -> None:
    req(payload.get("phase") == "LS-NEW-12", "handoff phase mismatch", errors)
    req(payload.get("document_type") == "START_LS_NEW12_NEXT_PHASE_HANDOFF", "handoff document_type mismatch", errors)
    req(payload.get("status") == "LSNEW12_NEXT_PHASE_HANDOFF_READY", "handoff status mismatch", errors)
    req(payload.get("next_phase") == "LS-NEW-13", "handoff next_phase mismatch", errors)
    req(payload.get("next_phase_name") == "Draft Creation Command Prep / No Execution", "handoff next_phase_name mismatch", errors)
    req(payload.get("handoff_ready") is True, "handoff handoff_ready mismatch", errors)
    req(payload.get("ready_for_ls_new_13") is True, "handoff ready_for_ls_new_13 mismatch", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-12", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == REQ_RUN, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == PROD, "result production_status mismatch", errors)
    req(result.get("ls_new11_validated") is True, "result ls_new11_validated mismatch", errors)
    req(result.get("ls_new11_ready") is True, "result ls_new11_ready mismatch", errors)
    req(result.get("credential_env_exists") is True, "result credential_env_exists mismatch", errors)
    req(result.get("credential_existence_check_executed") is True, "result credential_existence_check_executed mismatch", errors)
    req(result.get("credential_env_read_executed") is True, "result credential_env_read_executed mismatch", errors)
    req(result.get("wordpress_authenticated_read_get_attempted") is True, "result wordpress_authenticated_read_get_attempted mismatch", errors)
    req(result.get("wordpress_authenticated_read_get_succeeded") is True, "result wordpress_authenticated_read_get_succeeded mismatch", errors)
    req(result.get("wordpress_authenticated_read_status_class") == "2xx", "result wordpress_authenticated_read_status_class mismatch", errors)
    req(result.get("wordpress_authenticated_read_endpoint_kind") == "users_me", "result wordpress_authenticated_read_endpoint_kind mismatch", errors)
    _validate_secret_non_output_block(result, "result", errors)
    _validate_no_write_block(result, "result", errors)
    req(result.get("ready_for_ls_new_13") is True, "result ready_for_ls_new_13 mismatch", errors)
    req(
        result.get("recommended_next_action") == "BEGIN_LS_NEW_13_DRAFT_CREATION_COMMAND_PREP_NO_EXECUTION",
        "result recommended_next_action mismatch",
        errors,
    )
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-13", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-12", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW12_AUTHENTICATED_WP_READ_PREFLIGHT_LOCKED_NO_WRITE", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "execution_allowed",
        "runner_execution_allowed",
        "final_execution_command_created",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "wordpress_publish_executed",
        "wordpress_update_executed",
        "wordpress_delete_executed",
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "response_body_output",
        "user_identity_output",
        "wordpress_authenticated_read_response_body_saved",
        "wordpress_authenticated_user_identity_saved",
        "target_post_id_allocated",
        "approval_label_consumed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _validate_summary_text(summary_text: str, errors: list[str]) -> None:
    req("# LS-NEW-12 Authenticated WP Read Preflight Summary" in summary_text, "summary header mismatch", errors)
    req("- Authenticated WP read GET succeeded: true" in summary_text, "summary authenticated read succeeded mismatch", errors)
    req("- Response body saved: false" in summary_text, "summary response body saved mismatch", errors)
    req("- Authenticated user identity saved: false" in summary_text, "summary authenticated user identity saved mismatch", errors)
    req("- Authorization header output: false" in summary_text, "summary authorization header output mismatch", errors)
    req("- Ready for LS-NEW-13: true" in summary_text, "summary ready_for_ls_new_13 mismatch", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-12 Authenticated WP Read Preflight Validation Report",
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
    authenticated_read_result = try_load_json(Path(args.authenticated_read_result), errors, "authenticated-read-result")
    secret_non_output_summary = try_load_json(Path(args.secret_non_output_summary), errors, "secret-non-output-summary")
    no_write_contract = try_load_json(Path(args.no_write_safety_contract), errors, "no-write-safety-contract")
    draft_hold_boundary = try_load_json(Path(args.draft_creation_hold_boundary), errors, "draft-creation-hold-boundary")
    handoff = try_load_json(Path(args.next_phase_handoff), errors, "next-phase-handoff")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls11_validation = try_load_json(Path(args.ls_new11_validation_result), errors, "ls-new11-validation-result")
    summary_text = try_load_text(Path(args.summary), errors, "summary")

    req(policy.get("phase") == "LS-NEW-12", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-12", "schema phase mismatch", errors)
    req(ls11_validation.get("validation_status") == REQ_LS11_VALID, "ls-new11 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_authenticated_read_result(authenticated_read_result, errors)
    _validate_secret_non_output_summary(secret_non_output_summary, errors)
    _validate_no_write_contract(no_write_contract, errors)
    _validate_draft_hold_boundary(draft_hold_boundary, errors)
    _validate_handoff(handoff, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)
    _validate_summary_text(summary_text, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-12",
        "document_type": "START_LS_NEW12_AUTHENTICATED_WP_READ_PREFLIGHT_VALIDATION_RESULT",
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
