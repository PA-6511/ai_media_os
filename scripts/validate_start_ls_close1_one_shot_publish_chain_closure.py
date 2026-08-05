#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATED_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_VALIDATED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls_close1_one_shot_publish_chain_closure_policy.json",
    )
    parser.add_argument(
        "--closure-result",
        default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--closure-lock",
        default="exchange/locks/start_ls_close1_one_shot_publish_chain_closure.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--ls6au-result",
        default="exchange/runtime/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--ls6au-lock",
        default="exchange/locks/start_ls6au_post_publish_verification_published_evidence.lock.json",
    )
    parser.add_argument(
        "--ls6au-validation-result",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_validation_result.json",
    )
    parser.add_argument(
        "--ls6at-result",
        default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--ls6at-lock",
        default="exchange/locks/start_ls6at_actual_publish_execution_runner_separated_publish_execution.lock.json",
    )
    parser.add_argument(
        "--ls6at-validation-result",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls_close1_one_shot_publish_chain_closure_validation_report.md",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing file: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json: {path}")
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# START-LS One-Shot Publish Chain Closure Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- completion_status: {payload.get('completion_status', '')}",
        f"- recommended_next_action: {payload.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    closure_result = try_load_json(Path(args.closure_result), errors)
    closure_lock = try_load_json(Path(args.closure_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6au_result = try_load_json(Path(args.ls6au_result), errors)
    ls6au_lock = try_load_json(Path(args.ls6au_lock), errors)
    ls6au_validation = try_load_json(Path(args.ls6au_validation_result), errors)
    ls6at_result = try_load_json(Path(args.ls6at_result), errors)
    ls6at_lock = try_load_json(Path(args.ls6at_lock), errors)
    ls6at_validation = try_load_json(Path(args.ls6at_validation_result), errors)

    target = policy.get("target_post", {})
    closure_state = policy.get("completion_state", {})

    req(policy.get("phase") == "LS-CLOSE-1", "policy.phase mismatch", errors)
    req(closure_result.get("status") == "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION", "closure status mismatch", errors)
    req(closure_result == run_result, "closure result and run_result mismatch", errors)
    req(closure_result.get("production_status") == "PUBLISHED_AND_VERIFIED_CLOSURE", "production_status mismatch", errors)
    req(int(closure_result.get("post_id", 0)) == int(target.get("post_id", 0)), "post_id mismatch", errors)
    req(str(closure_result.get("completion_status", "")) == closure_state.get("status", ""), "completion_status mismatch", errors)
    req(str(closure_result.get("recommended_next_action", "")) == closure_state.get("recommended_next_action", ""), "recommended_next_action mismatch", errors)
    req(bool(closure_result.get("start_ls_one_shot_publish_chain_closed", False)) is True, "chain closed mismatch", errors)
    req(bool(closure_result.get("closure_registration_executed", False)) is True, "closure registration mismatch", errors)
    req(bool(closure_result.get("published_state_preserved", False)) is True, "published_state_preserved mismatch", errors)
    req(bool(closure_result.get("post_publish_verified", False)) is True, "post_publish_verified mismatch", errors)
    req(bool(closure_result.get("published_evidence_recorded", False)) is True, "published_evidence_recorded mismatch", errors)
    req(bool(closure_result.get("rollback_readiness_recorded", False)) is True, "rollback_readiness_recorded mismatch", errors)
    req(bool(closure_result.get("wordpress_api_call_executed", False)) is False, "wordpress_api_call_executed must be false", errors)
    req(bool(closure_result.get("wordpress_get_executed", False)) is False, "wordpress_get_executed must be false", errors)
    req(bool(closure_result.get("wordpress_post_executed", False)) is False, "wordpress_post_executed must be false", errors)
    req(bool(closure_result.get("wordpress_write_executed_by_this_phase", False)) is False, "wordpress_write_executed_by_this_phase must be false", errors)
    req(bool(closure_result.get("publish_executed_by_this_phase", False)) is False, "publish_executed_by_this_phase must be false", errors)
    req(bool(closure_result.get("credential_env_read_executed", False)) is False, "credential_env_read_executed must be false", errors)
    req(bool(closure_result.get("rollback_executed", False)) is False, "rollback_executed must be false", errors)
    req(bool(closure_result.get("unpublish_executed", False)) is False, "unpublish_executed must be false", errors)
    req(bool(closure_result.get("draft_revert_executed", False)) is False, "draft_revert_executed must be false", errors)
    req(bool(closure_result.get("post119_update_executed", False)) is False, "post119_update_executed must be false", errors)
    req(bool(closure_result.get("post183_update_executed_by_this_phase", False)) is False, "post183_update_executed_by_this_phase must be false", errors)
    req(bool(closure_result.get("rerun_allowed", False)) is False, "rerun_allowed must be false", errors)
    req(bool(closure_result.get("ls6at_rerun_allowed", False)) is False, "ls6at_rerun_allowed must be false", errors)
    req(bool(closure_result.get("ls6au_rerun_allowed", False)) is False, "ls6au_rerun_allowed must be false", errors)
    req(bool(closure_result.get("publish_rerun_allowed", False)) is False, "publish_rerun_allowed must be false", errors)
    req(bool(closure_result.get("ls6oc1_rerun_executed", False)) is False, "ls6oc1_rerun_executed must be false", errors)

    req(closure_lock.get("status") == "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(closure_lock.get("locked", False)) is True, "lock mismatch", errors)

    req(ls6au_result.get("status") == "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED", "LS-6AU run status mismatch", errors)
    req(ls6au_validation.get("status") == "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED", "LS-6AU validation status mismatch", errors)
    req(bool(ls6au_lock.get("locked", False)) is True, "LS-6AU lock mismatch", errors)
    req(str(ls6au_result.get("completion_status", "")) == "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED", "LS-6AU completion mismatch", errors)
    req(bool(ls6au_result.get("post_publish_verified", False)) is True, "LS-6AU post_publish_verified mismatch", errors)
    req(bool(ls6au_result.get("published_evidence_recorded", False)) is True, "LS-6AU published_evidence_recorded mismatch", errors)
    req(bool(ls6au_result.get("rollback_readiness_recorded", False)) is True, "LS-6AU rollback_readiness_recorded mismatch", errors)

    req(ls6at_result.get("status") == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED", "LS-6AT run status mismatch", errors)
    req(ls6at_validation.get("status") == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED", "LS-6AT validation status mismatch", errors)
    req(bool(ls6at_lock.get("locked", False)) is True, "LS-6AT lock mismatch", errors)
    req(int(ls6at_result.get("updated_post_id", 0)) == 183, "LS-6AT updated_post_id mismatch", errors)
    req(list(ls6at_result.get("updated_fields", [])) == ["status"], "LS-6AT updated_fields mismatch", errors)
    req(str(ls6at_result.get("updated_status", "")) == "publish", "LS-6AT updated_status mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-CLOSE-1",
        "document_type": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_VALIDATION_RESULT",
        "status": status,
        "run_status": str(closure_result.get("status", "")),
        "execution_mode": str(closure_result.get("execution_mode", "")),
        "production_status": str(closure_result.get("production_status", "")),
        "post_id": int(closure_result.get("post_id", 0)),
        "post_link": str(closure_result.get("post_link", "")),
        "payload_title": str(closure_result.get("payload_title", "")),
        "payload_asin": str(closure_result.get("payload_asin", "")),
        "ls6au_validated": bool(closure_result.get("ls6au_validated", False)),
        "ls6au_production_status": str(closure_result.get("ls6au_production_status", "")),
        "ls6au_completion_status": str(closure_result.get("ls6au_completion_status", "")),
        "ls6au_post_publish_verified": bool(closure_result.get("ls6au_post_publish_verified", False)),
        "ls6au_published_evidence_recorded": bool(closure_result.get("ls6au_published_evidence_recorded", False)),
        "ls6au_rollback_readiness_recorded": bool(closure_result.get("ls6au_rollback_readiness_recorded", False)),
        "ls6at_validated": bool(closure_result.get("ls6at_validated", False)),
        "ls6at_production_status": str(closure_result.get("ls6at_production_status", "")),
        "ls6at_updated_post_id": int(closure_result.get("ls6at_updated_post_id", 0)),
        "ls6at_updated_fields": list(closure_result.get("ls6at_updated_fields", [])),
        "ls6at_updated_status": str(closure_result.get("ls6at_updated_status", "")),
        "start_ls_one_shot_publish_chain_closed": bool(closure_result.get("start_ls_one_shot_publish_chain_closed", False)),
        "closure_registration_executed": bool(closure_result.get("closure_registration_executed", False)),
        "published_state_preserved": bool(closure_result.get("published_state_preserved", False)),
        "post_publish_verified": bool(closure_result.get("post_publish_verified", False)),
        "published_evidence_recorded": bool(closure_result.get("published_evidence_recorded", False)),
        "rollback_readiness_recorded": bool(closure_result.get("rollback_readiness_recorded", False)),
        "wordpress_api_call_executed": bool(closure_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(closure_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(closure_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(closure_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(closure_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(closure_result.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(closure_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_publish_executed_by_this_phase": bool(closure_result.get("wordpress_publish_executed_by_this_phase", False)),
        "publish_executed_by_this_phase": bool(closure_result.get("publish_executed_by_this_phase", False)),
        "post119_update_executed": bool(closure_result.get("post119_update_executed", False)),
        "post183_update_executed_by_this_phase": bool(closure_result.get("post183_update_executed_by_this_phase", False)),
        "wordpress_new_post_executed": bool(closure_result.get("wordpress_new_post_executed", False)),
        "wordpress_content_update_executed": bool(closure_result.get("wordpress_content_update_executed", False)),
        "wordpress_title_update_executed": bool(closure_result.get("wordpress_title_update_executed", False)),
        "wordpress_meta_update_executed": bool(closure_result.get("wordpress_meta_update_executed", False)),
        "wordpress_schedule_executed": bool(closure_result.get("wordpress_schedule_executed", False)),
        "future_schedule_executed": bool(closure_result.get("future_schedule_executed", False)),
        "delete_executed": bool(closure_result.get("delete_executed", False)),
        "rollback_executed": bool(closure_result.get("rollback_executed", False)),
        "unpublish_executed": bool(closure_result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(closure_result.get("draft_revert_executed", False)),
        "credential_env_read_executed": bool(closure_result.get("credential_env_read_executed", False)),
        "credential_values_loaded_for_output": bool(closure_result.get("credential_values_loaded_for_output", False)),
        "credential_values_persisted": bool(closure_result.get("credential_values_persisted", False)),
        "credential_values_logged": bool(closure_result.get("credential_values_logged", False)),
        "credential_value_output": bool(closure_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(closure_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(closure_result.get("credential_secret_output", False)),
        "secret_length_output": bool(closure_result.get("secret_length_output", False)),
        "secret_hash_output": bool(closure_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(closure_result.get("authorization_header_output", False)),
        "basic_auth_string_output": bool(closure_result.get("basic_auth_string_output", False)),
        "actual_publish_execution_runner_executed": bool(closure_result.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(closure_result.get("manual_publish_executed", False)),
        "manual_publish_allowed_by_this_phase": bool(closure_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(closure_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "locked": bool(closure_result.get("locked", False)),
        "rerun_allowed": bool(closure_result.get("rerun_allowed", False)),
        "ls6at_rerun_allowed": bool(closure_result.get("ls6at_rerun_allowed", False)),
        "ls6au_rerun_allowed": bool(closure_result.get("ls6au_rerun_allowed", False)),
        "publish_rerun_allowed": bool(closure_result.get("publish_rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(closure_result.get("ls6oc1_rerun_executed", False)),
        "completion_status": str(closure_result.get("completion_status", "")),
        "recommended_next_action": str(closure_result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(closure_result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
