#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_EXECUTION"
NOT_VALID = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_NOT_VALIDATED"
RUN_READY = "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_READY_NO_EXECUTION"
RUN_MODE = "WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY_NO_EXECUTION"
RUN_PROD = "NO_EXECUTION_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_ONLY"
REQ_LS7_VALID = "LSNEW7_WP_DRAFT_RUNNER_PREP_VALIDATED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new8_wp_draft_runner_final_preflight_policy.json")
    p.add_argument("--schema", default="config/start_ls_new8_wp_draft_runner_final_preflight_schema.json")
    p.add_argument("--manifest", default="exchange/new_release/start_ls_new8_final_preflight_manifest.json")
    p.add_argument("--freeze-boundary", default="exchange/new_release/start_ls_new8_freeze_boundary.json")
    p.add_argument("--rollback-boundary", default="exchange/new_release/start_ls_new8_rollback_boundary.json")
    p.add_argument("--abort-conditions", default="exchange/new_release/start_ls_new8_abort_conditions.json")
    p.add_argument("--handoff", default="exchange/new_release/start_ls_new8_next_approval_gate_handoff.json")
    p.add_argument("--summary", default="exchange/new_release/start_ls_new8_final_preflight_summary.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new8_wp_draft_runner_final_preflight_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new8_wp_draft_runner_final_preflight.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new8_wp_draft_runner_final_preflight_result.json")
    p.add_argument("--ls-new7-validation-result", default="exchange/logs/start_ls_new7_wp_draft_runner_prep_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new8_wp_draft_runner_final_preflight_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new8_wp_draft_runner_final_preflight_validation_report.md")
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
        "approval_label_consumed",
        "target_post_id_allocated",
        "post119_update_executed",
        "post183_update_executed",
        "candidate_selected",
        "ls_next1_fill_updated",
        "execution_allowed",
    ]


def _validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    req(manifest.get("phase") == "LS-NEW-8", "manifest phase mismatch", errors)
    req(manifest.get("document_type") == "START_LS_NEW8_FINAL_PREFLIGHT_MANIFEST", "manifest document_type mismatch", errors)
    req(manifest.get("status") == "LSNEW8_FINAL_PREFLIGHT_MANIFEST_READY_NO_EXECUTION", "manifest status mismatch", errors)
    req(manifest.get("execution_mode") == RUN_MODE, "manifest execution_mode mismatch", errors)
    req(manifest.get("production_status") == RUN_PROD, "manifest production_status mismatch", errors)
    req(manifest.get("ls_new7_validated") is True, "manifest ls_new7_validated mismatch", errors)
    req(manifest.get("final_preflight_manifest_created") is True, "manifest final_preflight_manifest_created mismatch", errors)
    req(manifest.get("freeze_boundary_created") is True, "manifest freeze_boundary_created mismatch", errors)
    req(manifest.get("rollback_boundary_created") is True, "manifest rollback_boundary_created mismatch", errors)
    req(manifest.get("abort_conditions_created") is True, "manifest abort_conditions_created mismatch", errors)
    req(manifest.get("next_approval_gate_handoff_created") is True, "manifest next_approval_gate_handoff_created mismatch", errors)
    req(manifest.get("target_post_id") is None, "manifest target_post_id must be null", errors)
    req(manifest.get("ready_for_ls_new_9") is True, "manifest ready_for_ls_new_9=false", errors)
    req(manifest.get("recommended_next_action") == "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION", "manifest recommended_next_action mismatch", errors)
    req(list(manifest.get("recommended_next_phase_options", [])) == ["LS-NEW-9", "LS-MON-2"], "manifest recommended_next_phase_options mismatch", errors)
    for key in _false_keys():
        req(manifest.get(key) is False, f"{key}=true", errors)


def _validate_freeze(freeze: dict[str, Any], errors: list[str]) -> None:
    req(freeze.get("phase") == "LS-NEW-8", "freeze phase mismatch", errors)
    req(freeze.get("document_type") == "START_LS_NEW8_FREEZE_BOUNDARY", "freeze document_type mismatch", errors)
    req(freeze.get("status") == "LSNEW8_FREEZE_BOUNDARY_READY_NO_EXECUTION", "freeze status mismatch", errors)
    req(freeze.get("freeze_required_before_later_execution") is True, "freeze_required_before_later_execution mismatch", errors)
    req(freeze.get("frozen_in_current_phase") is False, "frozen_in_current_phase=true", errors)
    req(freeze.get("freeze_execution_allowed") is False, "freeze_execution_allowed=true", errors)
    req(freeze.get("execution_allowed") is False, "freeze execution_allowed=true", errors)
    scope = list(freeze.get("freeze_scope", []))
    req("LS-NEW-8 final preflight manifest" in scope, "freeze scope missing ls-new8 manifest", errors)


def _validate_rollback(rollback: dict[str, Any], errors: list[str]) -> None:
    req(rollback.get("phase") == "LS-NEW-8", "rollback phase mismatch", errors)
    req(rollback.get("document_type") == "START_LS_NEW8_ROLLBACK_BOUNDARY", "rollback document_type mismatch", errors)
    req(rollback.get("status") == "LSNEW8_ROLLBACK_BOUNDARY_READY_NO_EXECUTION", "rollback status mismatch", errors)
    req(rollback.get("rollback_required_before_later_execution") is True, "rollback_required_before_later_execution mismatch", errors)
    req(rollback.get("target_post_id") is None, "rollback target_post_id must be null", errors)
    req(rollback.get("rollback_executed") is False, "rollback_executed=true", errors)
    req(rollback.get("execution_allowed") is False, "rollback execution_allowed=true", errors)


def _validate_abort(abort: dict[str, Any], errors: list[str]) -> None:
    req(abort.get("phase") == "LS-NEW-8", "abort phase mismatch", errors)
    req(abort.get("document_type") == "START_LS_NEW8_ABORT_CONDITIONS", "abort document_type mismatch", errors)
    req(abort.get("status") == "LSNEW8_ABORT_CONDITIONS_READY_NO_EXECUTION", "abort status mismatch", errors)
    req(abort.get("abort_triggered") is False, "abort_triggered=true", errors)
    req(abort.get("execution_allowed") is False, "abort execution_allowed=true", errors)
    items = list(abort.get("abort_if_any_true", []))
    for item in ["post_id=119 update is attempted", "post_id=183 update is attempted", "external fetch is attempted"]:
        req(item in items, f"abort conditions missing item: {item}", errors)


def _validate_handoff(handoff: dict[str, Any], errors: list[str]) -> None:
    req(handoff.get("phase") == "LS-NEW-8", "handoff phase mismatch", errors)
    req(handoff.get("document_type") == "START_LS_NEW8_NEXT_APPROVAL_GATE_HANDOFF", "handoff document_type mismatch", errors)
    req(handoff.get("status") == "LSNEW8_NEXT_APPROVAL_GATE_HANDOFF_READY_NO_EXECUTION", "handoff status mismatch", errors)
    req(handoff.get("next_phase") == "LS-NEW-9", "handoff next_phase mismatch", errors)
    req(handoff.get("required_future_approval_label") == "APPROVED_FOR_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_ONLY", "handoff approval label mismatch", errors)
    req(handoff.get("handoff_ready") is True, "handoff_ready=false", errors)
    req(handoff.get("execution_allowed") is False, "handoff execution_allowed=true", errors)
    req(handoff.get("runner_execution_allowed") is False, "handoff runner_execution_allowed=true", errors)
    req(handoff.get("wordpress_api_call_allowed") is False, "handoff wordpress_api_call_allowed=true", errors)
    req(handoff.get("wordpress_draft_create_allowed") is False, "handoff wordpress_draft_create_allowed=true", errors)
    req(handoff.get("credential_env_read_allowed") is False, "handoff credential_env_read_allowed=true", errors)


def _validate_summary(text: str, errors: list[str]) -> None:
    req(text.startswith("# LS-NEW-8 WordPress Draft Runner Final Preflight Summary"), "summary header mismatch", errors)
    for line in [
        "- Phase: LS-NEW-8",
        "- Status: READY_NO_EXECUTION",
        "- Runner execution allowed: false",
        "- Final execution command created: false",
        "- WordPress API executed: false",
        "- WordPress write executed: false",
        "- WordPress draft created: false",
        "- Credential read executed: false",
        "- Credential existence check executed: false",
        "- Target post ID allocated: false",
        "- Execution allowed: false",
        "- Ready for LS-NEW-9: true",
    ]:
        req(line in text, f"summary missing line: {line}", errors)


def _validate_result(result: dict[str, Any], run_result: dict[str, Any], errors: list[str]) -> None:
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("phase") == "LS-NEW-8", "result phase mismatch", errors)
    req(result.get("document_type") == "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_RESULT", "result document_type mismatch", errors)
    req(result.get("status") == RUN_READY, "result status mismatch", errors)
    req(result.get("execution_mode") == RUN_MODE, "result execution_mode mismatch", errors)
    req(result.get("production_status") == RUN_PROD, "result production_status mismatch", errors)
    req(result.get("ls_new7_validated") is True, "result ls_new7_validated mismatch", errors)
    req(result.get("final_preflight_manifest_created") is True, "result final_preflight_manifest_created mismatch", errors)
    req(result.get("freeze_boundary_created") is True, "result freeze_boundary_created mismatch", errors)
    req(result.get("rollback_boundary_created") is True, "result rollback_boundary_created mismatch", errors)
    req(result.get("abort_conditions_created") is True, "result abort_conditions_created mismatch", errors)
    req(result.get("next_approval_gate_handoff_created") is True, "result next_approval_gate_handoff_created mismatch", errors)
    req(result.get("final_preflight_summary_created") is True, "result final_preflight_summary_created mismatch", errors)
    req(result.get("target_post_id") is None, "result target_post_id must be null", errors)
    req(result.get("abort_triggered") is False, "result abort_triggered=true", errors)
    req(result.get("handoff_ready") is True, "result handoff_ready=false", errors)
    req(result.get("ready_for_ls_new_9") is True, "result ready_for_ls_new_9=false", errors)
    req(result.get("recommended_next_action") == "BEGIN_LS_NEW_9_SEPARATE_EXECUTION_APPROVAL_GATE_NO_EXECUTION", "result recommended_next_action mismatch", errors)
    req(list(result.get("recommended_next_phase_options", [])) == ["LS-NEW-9", "LS-MON-2"], "result recommended_next_phase_options mismatch", errors)
    for key in _false_keys():
        req(result.get(key) is False, f"result {key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-8", "lock phase mismatch", errors)
    req(lock.get("document_type") == "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCK", "lock document_type mismatch", errors)
    req(lock.get("status") == "LSNEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(lock.get("locked") is True, "lock mismatch", errors)
    for key in [
        "runner_execution_allowed",
        "final_execution_command_created",
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
        "# LS-NEW-8 WP Draft Runner Final Preflight Validation Report",
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
    freeze = try_load_json(Path(args.freeze_boundary), errors, "freeze-boundary")
    rollback = try_load_json(Path(args.rollback_boundary), errors, "rollback-boundary")
    abort = try_load_json(Path(args.abort_conditions), errors, "abort-conditions")
    handoff = try_load_json(Path(args.handoff), errors, "handoff")
    summary = read_text(Path(args.summary), errors, "summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls7_valid = try_load_json(Path(args.ls_new7_validation_result), errors, "ls-new7-validation-result")

    req(policy.get("phase") == "LS-NEW-8", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-8", "schema phase mismatch", errors)
    req(ls7_valid.get("validation_status") == REQ_LS7_VALID, "ls-new7 validation status mismatch", errors)

    _validate_manifest(manifest, errors)
    _validate_freeze(freeze, errors)
    _validate_rollback(rollback, errors)
    _validate_abort(abort, errors)
    _validate_handoff(handoff, errors)
    _validate_summary(summary, errors)
    _validate_result(result, run_result, errors)
    _validate_lock(lock, errors)

    status = VALID if len(errors) == 0 else NOT_VALID
    out = {
        "phase": "LS-NEW-8",
        "document_type": "START_LS_NEW8_WP_DRAFT_RUNNER_FINAL_PREFLIGHT_VALIDATION_RESULT",
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
