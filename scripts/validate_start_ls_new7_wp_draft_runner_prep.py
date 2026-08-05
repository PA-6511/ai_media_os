#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW7_WP_DRAFT_RUNNER_PREP_NOT_VALIDATED"
RUN_READY = "LSNEW7_WP_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"
RUN_MODE = "WP_DRAFT_RUNNER_PREP_ONLY_NO_EXECUTION"
RUN_PROD = "NO_EXECUTION_WP_DRAFT_RUNNER_PREP_ONLY"
REQ_LS6_VALID = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_VALIDATED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new7_wp_draft_runner_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new7_wp_draft_runner_prep_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_manifest.json")
    p.add_argument("--safety-contract", default="exchange/new_release/start_ls_new7_wp_draft_runner_safety_contract.json")
    p.add_argument("--preflight-checklist", default="exchange/new_release/start_ls_new7_wp_draft_runner_preflight_checklist.json")
    p.add_argument("--command-template", default="exchange/new_release/start_ls_new7_blocked_execution_command_template.md")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new7_wp_draft_runner_prep_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new7_wp_draft_runner_prep_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new7_wp_draft_runner_prep.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new7_wp_draft_runner_prep_result.json")
    p.add_argument("--ls-new6-validation-result", default="exchange/logs/start_ls_new6_wp_draft_payload_prep_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new7_wp_draft_runner_prep_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new7_wp_draft_runner_prep_validation_report.md")
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
        "runner_execution_allowed",
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
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
    ]


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-7", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == "LSNEW7_WP_DRAFT_RUNNER_PREP_MANIFEST_READY_NO_EXECUTION", "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == RUN_MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == RUN_PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new6_validated") is True, "manifest ls_new6_validated mismatch", errors)
    req(manifest.get("runner_prep_manifest_created") is True, "manifest created flag mismatch", errors)
    req(manifest.get("runner_safety_contract_created") is True, "manifest safety flag mismatch", errors)
    req(manifest.get("runner_preflight_checklist_created") is True, "manifest checklist flag mismatch", errors)
    req(manifest.get("blocked_execution_command_template_created") is True, "manifest command template flag mismatch", errors)
    req(manifest.get("target_post_id") is None, "manifest target_post_id must be null", errors)
    req(manifest.get("ready_for_ls_new_8") is True, "manifest ready_for_ls_new_8=false", errors)
    req(manifest.get("recommended_next_action") == "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION", "manifest recommended_next_action mismatch", errors)
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-8", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)
    for key in _false_keys():
        req(manifest.get(key) is False, f"{key}=true", errors)


def _validate_safety(contract: dict[str, Any], errors: list[str]) -> None:
    req(contract.get("phase") == "LS-NEW-7", "safety contract phase mismatch", errors)
    req(contract.get("document_type") == "START_LS_NEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT", "safety contract document_type mismatch", errors)
    req(contract.get("status") == "LSNEW7_WP_DRAFT_RUNNER_SAFETY_CONTRACT_READY_NO_EXECUTION", "safety contract status mismatch", errors)
    req(contract.get("runner_execution_allowed") is False, "runner_execution_allowed=true", errors)
    req(contract.get("blocked_until_explicit_approval") is True, "blocked_until_explicit_approval mismatch", errors)
    req(contract.get("separate_execution_command_required") is True, "separate_execution_command_required mismatch", errors)
    req(contract.get("final_preflight_required") is True, "final_preflight_required mismatch", errors)
    req(contract.get("human_approval_required_before_any_wp_call") is True, "human_approval_required_before_any_wp_call mismatch", errors)
    req(contract.get("wordpress_api_call_allowed") is False, "wordpress_api_call_allowed=true", errors)
    req(contract.get("wordpress_write_allowed") is False, "wordpress_write_allowed=true", errors)
    req(contract.get("wordpress_draft_create_allowed") is False, "wordpress_draft_create_allowed=true", errors)
    req(contract.get("credential_env_read_allowed") is False, "credential_env_read_allowed=true", errors)
    req(contract.get("target_post_id_allocation_allowed") is False, "target_post_id_allocation_allowed=true", errors)
    req(contract.get("approval_label_consumption_allowed") is False, "approval_label_consumption_allowed=true", errors)
    req(contract.get("execution_allowed") is False, "safety contract execution_allowed=true", errors)
    forbidden = list(contract.get("always_forbidden", []))
    for item in ["post_id=119 update", "post_id=183 update", "WordPress API call in LS-NEW-7", "WordPress draft creation in LS-NEW-7", "external fetch in LS-NEW-7"]:
        req(item in forbidden, f"safety contract missing forbidden item: {item}", errors)


def _validate_preflight(preflight: dict[str, Any], errors: list[str]) -> None:
    req(preflight.get("phase") == "LS-NEW-7", "preflight phase mismatch", errors)
    req(preflight.get("document_type") == "START_LS_NEW7_WP_DRAFT_RUNNER_PREFLIGHT_CHECKLIST", "preflight document_type mismatch", errors)
    req(preflight.get("status") == "LSNEW7_PREFLIGHT_CHECKLIST_READY_NO_EXECUTION", "preflight status mismatch", errors)
    required = list(preflight.get("required_before_later_execution", []))
    req("final preflight completed in later phase" in required, "preflight missing final preflight item", errors)
    checks = dict(preflight.get("current_phase_checks", {}))
    for key in ["runner_execution_allowed", "wordpress_api_call_executed", "wordpress_write_executed", "wordpress_draft_created", "credential_env_read_executed", "target_post_id_allocated", "execution_allowed"]:
        req(checks.get(key) is False, f"preflight current_phase_checks {key}=true", errors)


def _validate_command_template(text: str, errors: list[str]) -> None:
    req(text.startswith("# LS-NEW-7 Blocked Execution Command Template"), "command template header mismatch", errors)
    for line in [
        "This is not an executable command.",
        "This file documents that execution is blocked in LS-NEW-7.",
        "- Runner execution allowed: false",
        "- WordPress API allowed: false",
        "- WordPress draft creation allowed: false",
        "- Execution allowed: false",
        "Actual execution must not be attempted in LS-NEW-7.",
    ]:
        req(line in text, f"command template missing line: {line}", errors)


def _validate_summary(text: str, errors: list[str]) -> None:
    req(text.startswith("# LS-NEW-7 WordPress Draft Runner Prep Summary"), "summary header mismatch", errors)
    for line in [
        "- Phase: LS-NEW-7",
        "- Status: READY_NO_EXECUTION",
        "- Runner execution allowed: false",
        "- WordPress API executed: false",
        "- WordPress write executed: false",
        "- WordPress draft created: false",
        "- Credential read executed: false",
        "- Target post ID allocated: false",
        "- Execution allowed: false",
        "- Source payload: exchange/new_release/start_ls_new6_wp_draft_payload_prep.json",
    ]:
        req(line in text, f"summary missing line: {line}", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-7", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("execution_mode") == RUN_MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == RUN_PROD, "result production_status mismatch", errors)
    req(result.get("ls_new6_validated") is True, "result ls_new6_validated mismatch", errors)
    req(result.get("runner_prep_manifest_created") is True, "result runner_prep_manifest_created mismatch", errors)
    req(result.get("runner_safety_contract_created") is True, "result runner_safety_contract_created mismatch", errors)
    req(result.get("runner_preflight_checklist_created") is True, "result runner_preflight_checklist_created mismatch", errors)
    req(result.get("blocked_execution_command_template_created") is True, "result blocked_execution_command_template_created mismatch", errors)
    req(result.get("runner_prep_summary_created") is True, "result runner_prep_summary_created mismatch", errors)
    req(result.get("target_post_id") is None, "result target_post_id must be null", errors)
    req(result.get("ready_for_ls_new_8") is True, "ready_for_ls_new_8=false", errors)
    req(result.get("recommended_next_action") == "BEGIN_LS_NEW_8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NO_EXECUTION", "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-8", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)
    for key in _false_keys():
        req(result.get(key) is False, f"result {key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-7", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW7_WP_DRAFT_RUNNER_PREP_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "runner_execution_allowed",
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
        "credential_existence_check_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]:
        req(lock.get(key) is False, f"lock {key}=true", errors)


def _report(path: Path, out: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-7 WP Draft Runner Prep Validation Report",
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
    manifest = try_load_json(Path(args.manifest), errors, "manifest")
    safety = try_load_json(Path(args.safety_contract), errors, "safety-contract")
    preflight = try_load_json(Path(args.preflight_checklist), errors, "preflight-checklist")
    command = read_text(Path(args.command_template), errors, "command-template")
    summary = read_text(Path(args.summary), errors, "summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls6_valid = try_load_json(Path(args.ls_new6_validation_result), errors, "ls-new6-validation-result")

    req(policy.get("phase") == "LS-NEW-7", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-7", "schema phase mismatch", errors)
    req(ls6_valid.get("validation_status") == REQ_LS6_VALID, "ls-new6 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_safety(safety, errors)
    _validate_preflight(preflight, errors)
    _validate_command_template(command, errors)
    _validate_summary(summary, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-7",
        "document_type": "START_LS_NEW7_WP_DRAFT_RUNNER_PREP_VALIDATION_RESULT",
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
