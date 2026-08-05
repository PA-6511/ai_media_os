#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATED_NO_WRITE"
NOT_VALID = "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_NOT_VALIDATED"
REQ_RUN = "LSNEW11_CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_READY_NO_WRITE"
REQ_LS10_VALID = "LSNEW10_EXECUTION_PREP_VALIDATED_NO_DRAFT_CREATION"
MODE = "CREDENTIAL_AND_WP_CONNECTIVITY_PREFLIGHT_NO_WRITE"
PROD = "NO_WRITE_CONNECTIVITY_PREFLIGHT_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new11_credential_wp_connectivity_preflight_policy.json")
    p.add_argument("--schema", default="config/start_ls_new11_credential_wp_connectivity_preflight_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new11_credential_preflight_manifest.json")
    p.add_argument("--credential-summary", default="exchange/new_release/start_ls_new11_credential_presence_summary.json")
    p.add_argument("--wp-connectivity-result", default="exchange/new_release/start_ls_new11_wp_connectivity_preflight_result.json")
    p.add_argument("--no-write-safety-contract", default="exchange/new_release/start_ls_new11_no_write_safety_contract.json")
    p.add_argument("--next-phase-handoff", default="exchange/new_release/start_ls_new11_next_phase_handoff.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new11_credential_wp_connectivity_preflight_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new11_credential_wp_connectivity_preflight_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new11_credential_wp_connectivity_preflight.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new11_credential_wp_connectivity_preflight_result.json")
    p.add_argument("--ls-new10-validation-result", default="exchange/logs/start_ls_new10_execution_prep_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new11_credential_wp_connectivity_preflight_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new11_credential_wp_connectivity_preflight_validation_report.md")
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


def _validate_secret_output_block(payload: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in [
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "credential_values_saved",
    ]:
        req(payload.get(key) is False, f"{prefix} {key}=true", errors)


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
        "wordpress_authenticated_get_executed",
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


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-11", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW11_CREDENTIAL_PREFLIGHT_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == REQ_RUN, "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new10_validated") is True, "manifest ls_new10_validated mismatch", errors)
    req(manifest.get("ls_new10_ready") is True, "manifest ls_new10_ready mismatch", errors)
    req(manifest.get("credential_env_exists") is True, "manifest credential_env_exists mismatch", errors)
    req(manifest.get("credential_existence_check_executed") is True, "manifest credential_existence_check_executed mismatch", errors)
    req(manifest.get("credential_env_read_executed") is True, "manifest credential_env_read_executed mismatch", errors)
    req(manifest.get("required_url_key_present") is True, "manifest required_url_key_present mismatch", errors)
    req(manifest.get("required_username_key_present") is True, "manifest required_username_key_present mismatch", errors)
    req(manifest.get("required_app_password_key_present") is True, "manifest required_app_password_key_present mismatch", errors)
    req(manifest.get("required_url_value_nonempty") is True, "manifest required_url_value_nonempty mismatch", errors)
    req(manifest.get("required_username_value_nonempty") is True, "manifest required_username_value_nonempty mismatch", errors)
    req(manifest.get("required_app_password_value_nonempty") is True, "manifest required_app_password_value_nonempty mismatch", errors)
    req(manifest.get("wordpress_rest_index_get_attempted") is True, "manifest wordpress_rest_index_get_attempted mismatch", errors)
    req(manifest.get("wordpress_rest_index_get_succeeded") is True, "manifest wordpress_rest_index_get_succeeded mismatch", errors)
    req(manifest.get("wordpress_rest_index_status_class") == "2xx", "manifest wordpress_rest_index_status_class mismatch", errors)
    req(manifest.get("wordpress_rest_response_body_saved") is False, "manifest wordpress_rest_response_body_saved=true", errors)
    _validate_no_write_block(manifest, "manifest", errors)
    _validate_secret_output_block(manifest, "manifest", errors)
    req(manifest.get("ready_for_ls_new_12") is True, "manifest ready_for_ls_new_12 mismatch", errors)
    req(manifest.get("recommended_next_action") == "BEGIN_LS_NEW_12_AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE", "manifest recommended_next_action mismatch", errors)
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-12", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)


def _validate_credential_summary(credential_summary: dict[str, Any], errors: list[str]) -> None:
    req(credential_summary.get("phase") == "LS-NEW-11", "credential-summary phase mismatch", errors)
    req(credential_summary.get("document_type") == "START_LS_NEW11_CREDENTIAL_PRESENCE_SUMMARY", "credential-summary document_type mismatch", errors)
    req(
        credential_summary.get("status") == "LSNEW11_CREDENTIAL_PRESENCE_SUMMARY_READY_NO_SECRET_OUTPUT",
        "credential-summary status mismatch",
        errors,
    )
    req(credential_summary.get("credential_env_exists") is True, "credential-summary credential_env_exists mismatch", errors)
    req(credential_summary.get("credential_existence_check_executed") is True, "credential-summary credential_existence_check_executed mismatch", errors)
    req(credential_summary.get("credential_env_read_executed") is True, "credential-summary credential_env_read_executed mismatch", errors)
    req(credential_summary.get("required_url_key_present") is True, "credential-summary required_url_key_present mismatch", errors)
    req(credential_summary.get("required_username_key_present") is True, "credential-summary required_username_key_present mismatch", errors)
    req(credential_summary.get("required_app_password_key_present") is True, "credential-summary required_app_password_key_present mismatch", errors)
    req(credential_summary.get("required_url_value_nonempty") is True, "credential-summary required_url_value_nonempty mismatch", errors)
    req(credential_summary.get("required_username_value_nonempty") is True, "credential-summary required_username_value_nonempty mismatch", errors)
    req(credential_summary.get("required_app_password_value_nonempty") is True, "credential-summary required_app_password_value_nonempty mismatch", errors)
    _validate_secret_output_block(credential_summary, "credential-summary", errors)


def _validate_wp_connectivity(wp_connectivity: dict[str, Any], errors: list[str]) -> None:
    req(wp_connectivity.get("phase") == "LS-NEW-11", "wp-connectivity phase mismatch", errors)
    req(
        wp_connectivity.get("document_type") == "START_LS_NEW11_WP_CONNECTIVITY_PREFLIGHT_RESULT",
        "wp-connectivity document_type mismatch",
        errors,
    )
    req(wp_connectivity.get("status") == "LSNEW11_WP_REST_CONNECTIVITY_READY_NO_WRITE", "wp-connectivity status mismatch", errors)
    req(wp_connectivity.get("wordpress_rest_index_get_attempted") is True, "wp-connectivity wordpress_rest_index_get_attempted mismatch", errors)
    req(wp_connectivity.get("wordpress_rest_index_get_succeeded") is True, "wp-connectivity wordpress_rest_index_get_succeeded mismatch", errors)
    req(wp_connectivity.get("wordpress_rest_index_status_class") == "2xx", "wp-connectivity wordpress_rest_index_status_class mismatch", errors)
    req(wp_connectivity.get("wordpress_rest_response_body_saved") is False, "wp-connectivity wordpress_rest_response_body_saved=true", errors)
    req(wp_connectivity.get("wordpress_authenticated_get_executed") is False, "wp-connectivity wordpress_authenticated_get_executed=true", errors)
    req(wp_connectivity.get("wordpress_write_executed") is False, "wp-connectivity wordpress_write_executed=true", errors)
    req(wp_connectivity.get("wordpress_draft_created") is False, "wp-connectivity wordpress_draft_created=true", errors)
    req(wp_connectivity.get("wordpress_publish_executed") is False, "wp-connectivity wordpress_publish_executed=true", errors)
    req(wp_connectivity.get("wordpress_update_executed") is False, "wp-connectivity wordpress_update_executed=true", errors)
    req(wp_connectivity.get("wordpress_delete_executed") is False, "wp-connectivity wordpress_delete_executed=true", errors)
    req(wp_connectivity.get("execution_allowed") is False, "wp-connectivity execution_allowed=true", errors)


def _validate_no_write_contract(no_write_contract: dict[str, Any], errors: list[str]) -> None:
    req(no_write_contract.get("phase") == "LS-NEW-11", "no-write-contract phase mismatch", errors)
    req(no_write_contract.get("document_type") == "START_LS_NEW11_NO_WRITE_SAFETY_CONTRACT", "no-write-contract document_type mismatch", errors)
    req(no_write_contract.get("status") == "LSNEW11_NO_WRITE_SAFETY_CONTRACT_READY", "no-write-contract status mismatch", errors)
    req(no_write_contract.get("no_write_required") is True, "no-write-contract no_write_required mismatch", errors)
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
        req(no_write_contract.get(key) is False, f"no-write-contract {key}=true", errors)


def _validate_handoff(handoff: dict[str, Any], errors: list[str]) -> None:
    req(handoff.get("phase") == "LS-NEW-11", "handoff phase mismatch", errors)
    req(handoff.get("document_type") == "START_LS_NEW11_NEXT_PHASE_HANDOFF", "handoff document_type mismatch", errors)
    req(handoff.get("status") == "LSNEW11_NEXT_PHASE_HANDOFF_READY", "handoff status mismatch", errors)
    req(handoff.get("next_phase") == "LS-NEW-12", "handoff next_phase mismatch", errors)
    req(handoff.get("next_phase_name") == "Authenticated WP Read Preflight / No Write", "handoff next_phase_name mismatch", errors)
    req(handoff.get("handoff_ready") is True, "handoff handoff_ready mismatch", errors)
    req(handoff.get("ready_for_ls_new_12") is True, "handoff ready_for_ls_new_12 mismatch", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-11", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == REQ_RUN, "result status mismatch", errors)
    req(result.get("execution_mode") == MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == PROD, "result production_status mismatch", errors)
    req(result.get("ls_new10_validated") is True, "result ls_new10_validated mismatch", errors)
    req(result.get("ls_new10_ready") is True, "result ls_new10_ready mismatch", errors)
    req(result.get("credential_env_exists") is True, "result credential_env_exists mismatch", errors)
    req(result.get("credential_existence_check_executed") is True, "result credential_existence_check_executed mismatch", errors)
    req(result.get("credential_env_read_executed") is True, "result credential_env_read_executed mismatch", errors)
    req(result.get("required_url_key_present") is True, "result required_url_key_present mismatch", errors)
    req(result.get("required_username_key_present") is True, "result required_username_key_present mismatch", errors)
    req(result.get("required_app_password_key_present") is True, "result required_app_password_key_present mismatch", errors)
    req(result.get("required_url_value_nonempty") is True, "result required_url_value_nonempty mismatch", errors)
    req(result.get("required_username_value_nonempty") is True, "result required_username_value_nonempty mismatch", errors)
    req(result.get("required_app_password_value_nonempty") is True, "result required_app_password_value_nonempty mismatch", errors)
    req(result.get("wordpress_rest_index_get_attempted") is True, "result wordpress_rest_index_get_attempted mismatch", errors)
    req(result.get("wordpress_rest_index_get_succeeded") is True, "result wordpress_rest_index_get_succeeded mismatch", errors)
    req(result.get("wordpress_rest_index_status_class") == "2xx", "result wordpress_rest_index_status_class mismatch", errors)
    req(result.get("wordpress_rest_response_body_saved") is False, "result wordpress_rest_response_body_saved=true", errors)
    _validate_no_write_block(result, "result", errors)
    _validate_secret_output_block(result, "result", errors)
    req(result.get("ready_for_ls_new_12") is True, "result ready_for_ls_new_12 mismatch", errors)
    req(result.get("recommended_next_action") == "BEGIN_LS_NEW_12_AUTHENTICATED_WP_READ_PREFLIGHT_NO_WRITE", "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-12", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-11", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_LOCKED_NO_WRITE", "lock status mismatch", errors)
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
        "wordpress_authenticated_get_executed",
        "credential_value_output",
        "credential_secret_output",
        "credential_length_output",
        "credential_hash_output",
        "authorization_header_output",
        "basic_auth_output",
        "base64_auth_output",
        "target_post_id_allocated",
        "approval_label_consumed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _validate_summary_text(summary_text: str, errors: list[str]) -> None:
    req("# LS-NEW-11 Credential and WP Connectivity Preflight Summary" in summary_text, "summary header mismatch", errors)
    req("- Credential values output: false" in summary_text, "summary credential values output mismatch", errors)
    req("- Authorization header output: false" in summary_text, "summary authorization header output mismatch", errors)
    req("- WordPress REST index GET succeeded: true" in summary_text, "summary wordpress_rest_index_get_succeeded mismatch", errors)
    req("- Ready for LS-NEW-12: true" in summary_text, "summary ready_for_ls_new_12 mismatch", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-11 Credential and WP Connectivity Preflight Validation Report",
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
    credential_summary = try_load_json(Path(args.credential_summary), errors, "credential-summary")
    wp_connectivity = try_load_json(Path(args.wp_connectivity_result), errors, "wp-connectivity-result")
    no_write_contract = try_load_json(Path(args.no_write_safety_contract), errors, "no-write-safety-contract")
    handoff = try_load_json(Path(args.next_phase_handoff), errors, "next-phase-handoff")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls10_validation = try_load_json(Path(args.ls_new10_validation_result), errors, "ls-new10-validation-result")
    summary_text = try_load_text(Path(args.summary), errors, "summary")

    req(policy.get("phase") == "LS-NEW-11", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-11", "schema phase mismatch", errors)
    req(ls10_validation.get("validation_status") == REQ_LS10_VALID, "ls-new10 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_credential_summary(credential_summary, errors)
    _validate_wp_connectivity(wp_connectivity, errors)
    _validate_no_write_contract(no_write_contract, errors)
    _validate_handoff(handoff, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)
    _validate_summary_text(summary_text, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-11",
        "document_type": "START_LS_NEW11_CREDENTIAL_WP_CONNECTIVITY_PREFLIGHT_VALIDATION_RESULT",
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