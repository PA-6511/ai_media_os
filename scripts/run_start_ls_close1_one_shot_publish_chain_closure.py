#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_FAILED_NO_EXECUTION"
STATUS_MISSING_REGISTER_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_REGISTER_FLAG"
STATUS_BAD_POST_CONFIRMATION = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_BAD_POST_CONFIRMATION"
STATUS_BAD_COMPLETION_CONFIRMATION = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_BAD_COMPLETION_CONFIRMATION"
STATUS_MISSING_NO_WORDPRESS_API_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_NO_WORDPRESS_API_FLAG"
STATUS_MISSING_NO_CREDENTIAL_READ_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_NO_CREDENTIAL_READ_FLAG"
STATUS_MISSING_NO_PUBLISH_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_NO_PUBLISH_FLAG"
STATUS_MISSING_NO_ROLLBACK_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_NO_ROLLBACK_FLAG"
STATUS_MISSING_FORBID_POST119_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_FORBID_POST119_FLAG"
STATUS_MISSING_FORBID_POST183_UPDATE_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_FORBID_POST183_UPDATE_FLAG"
STATUS_MISSING_FORBID_NEW_POST_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_FORBID_NEW_POST_FLAG"
STATUS_MISSING_FORBID_DELETE_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_FORBID_DELETE_FLAG"
STATUS_MISSING_FORBID_SCHEDULE_FLAG = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_NOT_READY_MISSING_FORBID_SCHEDULE_FLAG"
LOCKED_STATUS = "LSCLOSE1_START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_LOCKED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls_close1_one_shot_publish_chain_closure_policy.json",
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
        "--ls6au-run-result",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_result.json",
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
        "--closure-output",
        default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--closure-lock-output",
        default="exchange/locks/start_ls_close1_one_shot_publish_chain_closure.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls_close1_one_shot_publish_chain_closure_report.md",
    )

    parser.add_argument("--register-chain-closure", action="store_true")
    parser.add_argument("--confirm-post-id", type=int, default=0)
    parser.add_argument("--confirm-completion-status", default="")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-rollback", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-post183-update", action="store_true")
    parser.add_argument("--forbid-new-post", action="store_true")
    parser.add_argument("--forbid-delete", action="store_true")
    parser.add_argument("--forbid-schedule", action="store_true")
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
        "# START-LS One-Shot Publish Chain Closure Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- production_status: {payload['production_status']}",
        f"- post_id: {payload['post_id']}",
        f"- completion_status: {payload['completion_status']}",
        f"- recommended_next_action: {payload['recommended_next_action']}",
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


def choose_missing_flag_status(args: argparse.Namespace) -> str | None:
    if not args.register_chain_closure:
        return STATUS_MISSING_REGISTER_FLAG
    if not args.require_no_wordpress_api:
        return STATUS_MISSING_NO_WORDPRESS_API_FLAG
    if not args.require_no_credential_read:
        return STATUS_MISSING_NO_CREDENTIAL_READ_FLAG
    if not args.require_no_publish:
        return STATUS_MISSING_NO_PUBLISH_FLAG
    if not args.require_no_rollback:
        return STATUS_MISSING_NO_ROLLBACK_FLAG
    if not args.forbid_post119_update:
        return STATUS_MISSING_FORBID_POST119_FLAG
    if not args.forbid_post183_update:
        return STATUS_MISSING_FORBID_POST183_UPDATE_FLAG
    if not args.forbid_new_post:
        return STATUS_MISSING_FORBID_NEW_POST_FLAG
    if not args.forbid_delete:
        return STATUS_MISSING_FORBID_DELETE_FLAG
    if not args.forbid_schedule:
        return STATUS_MISSING_FORBID_SCHEDULE_FLAG
    return None


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls6au_result = try_load_json(Path(args.ls6au_result), errors)
    ls6au_lock = try_load_json(Path(args.ls6au_lock), errors)
    ls6au_run = try_load_json(Path(args.ls6au_run_result), errors)
    ls6au_validation = try_load_json(Path(args.ls6au_validation_result), errors)
    ls6at_result = try_load_json(Path(args.ls6at_result), errors)
    ls6at_lock = try_load_json(Path(args.ls6at_lock), errors)
    ls6at_validation = try_load_json(Path(args.ls6at_validation_result), errors)

    target = policy.get("target_post", {})
    closure_state = policy.get("completion_state", {})
    closure_policy = policy.get("closure_policy", {})
    req_ls6au = policy.get("required_previous_phase", {}).get("ls6au", {})
    req_ls6at = policy.get("required_previous_phase", {}).get("ls6at", {})

    missing_flag_status = choose_missing_flag_status(args)
    if args.confirm_post_id != int(target.get("post_id", 0)):
        missing_flag_status = STATUS_BAD_POST_CONFIRMATION
    if args.confirm_completion_status != str(closure_state.get("status", "")):
        missing_flag_status = STATUS_BAD_COMPLETION_CONFIRMATION

    req(policy.get("phase") == "LS-CLOSE-1", "policy.phase mismatch", errors)
    req(
        ls6au_result.get("status") == req_ls6au.get("required_run_status"),
        "LS-6AU run status mismatch",
        errors,
    )
    req(
        ls6au_validation.get("status") == req_ls6au.get("required_validation_status"),
        "LS-6AU validation status mismatch",
        errors,
    )
    req(ls6au_result == ls6au_run, "LS-6AU result mismatch", errors)
    req(ls6au_result.get("production_status") == req_ls6au.get("required_production_status"), "LS-6AU production_status mismatch", errors)
    req(int(ls6au_result.get("post_id", 0)) == req_ls6au.get("required_post_id"), "LS-6AU post_id mismatch", errors)
    req(str(ls6au_result.get("rest_returned_post_status", "")) == req_ls6au.get("required_rest_returned_post_status"), "LS-6AU rest status mismatch", errors)
    req(bool(ls6au_result.get("public_url_reachable", False)) is bool(req_ls6au.get("required_public_url_reachable", True)), "LS-6AU public_url_reachable mismatch", errors)
    req(bool(ls6au_result.get("post_publish_verified", False)) is bool(req_ls6au.get("required_post_publish_verified", True)), "LS-6AU post_publish_verified mismatch", errors)
    req(bool(ls6au_result.get("published_evidence_recorded", False)) is bool(req_ls6au.get("required_published_evidence_recorded", True)), "LS-6AU published_evidence_recorded mismatch", errors)
    req(bool(ls6au_result.get("rollback_readiness_recorded", False)) is bool(req_ls6au.get("required_rollback_readiness_recorded", True)), "LS-6AU rollback_readiness_recorded mismatch", errors)
    req(str(ls6au_result.get("completion_status", "")) == req_ls6au.get("required_completion_status"), "LS-6AU completion_status mismatch", errors)
    req(bool(ls6au_lock.get("locked", False)) is True, "LS-6AU lock mismatch", errors)
    req(bool(ls6au_result.get("rollback_executed", False)) is False, "LS-6AU rollback_executed must be false", errors)
    req(bool(ls6au_result.get("unpublish_executed", False)) is False, "LS-6AU unpublish_executed must be false", errors)
    req(bool(ls6au_result.get("draft_revert_executed", False)) is False, "LS-6AU draft_revert_executed must be false", errors)
    req(bool(ls6au_result.get("wordpress_post_executed", False)) is False, "LS-6AU wordpress_post_executed must be false", errors)
    req(bool(ls6au_result.get("wordpress_write_executed_by_this_phase", False)) is False, "LS-6AU wordpress_write_executed_by_this_phase must be false", errors)
    req(bool(ls6au_result.get("publish_executed_by_this_phase", False)) is False, "LS-6AU publish_executed_by_this_phase must be false", errors)

    req(ls6at_result.get("status") == req_ls6at.get("required_run_status"), "LS-6AT run status mismatch", errors)
    req(ls6at_validation.get("status") == req_ls6at.get("required_validation_status"), "LS-6AT validation status mismatch", errors)
    req(ls6at_result.get("production_status") == req_ls6at.get("required_production_status"), "LS-6AT production_status mismatch", errors)
    req(int(ls6at_result.get("post_id", 0)) == req_ls6at.get("required_post_id"), "LS-6AT post_id mismatch", errors)
    req(str(ls6at_result.get("post_publish_returned_post_status", "")) == req_ls6at.get("required_post_publish_status"), "LS-6AT post_publish status mismatch", errors)
    req(int(ls6at_result.get("updated_post_id", 0)) == req_ls6at.get("required_updated_post_id"), "LS-6AT updated_post_id mismatch", errors)
    req(list(ls6at_result.get("updated_fields", [])) == list(req_ls6at.get("required_updated_fields", [])), "LS-6AT updated_fields mismatch", errors)
    req(str(ls6at_result.get("updated_status", "")) == req_ls6at.get("required_updated_status"), "LS-6AT updated_status mismatch", errors)
    req(
        bool(ls6at_result.get("post119_update_executed", False)) is (not bool(req_ls6at.get("required_no_post119_update", True))),
        "LS-6AT post119_update_executed mismatch",
        errors,
    )
    req(bool(ls6at_result.get("new_post_created", False)) is False, "LS-6AT new_post_created must be false", errors)
    req(bool(ls6at_result.get("content_update_executed", False)) is False, "LS-6AT content_update_executed must be false", errors)
    req(bool(ls6at_result.get("title_update_executed", False)) is False, "LS-6AT title_update_executed must be false", errors)
    req(bool(ls6at_result.get("meta_update_executed", False)) is False, "LS-6AT meta_update_executed must be false", errors)
    req(bool(ls6at_result.get("delete_executed", False)) is False, "LS-6AT delete_executed must be false", errors)
    req(bool(ls6at_lock.get("locked", False)) is True, "LS-6AT lock mismatch", errors)

    req(closure_state.get("status") == "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSED_PUBLISHED_AND_VERIFIED", "completion state mismatch", errors)
    req(int(closure_state.get("post_id", 0)) == int(target.get("post_id", 0)), "completion state post_id mismatch", errors)
    req(bool(closure_state.get("published", False)) is True, "completion state published mismatch", errors)
    req(bool(closure_state.get("post_publish_verified", False)) is True, "completion state verified mismatch", errors)
    req(bool(closure_state.get("published_evidence_recorded", False)) is True, "completion state evidence mismatch", errors)
    req(bool(closure_state.get("rollback_readiness_recorded", False)) is True, "completion state rollback readiness mismatch", errors)
    req(bool(closure_state.get("closure_registered", False)) is True, "completion state closure registration mismatch", errors)
    req(bool(closure_state.get("publish_chain_closed", False)) is True, "completion state chain closed mismatch", errors)

    status = STATUS_PASSED if not errors and missing_flag_status is None else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status

    payload = {
        "phase": "LS-CLOSE-1",
        "document_type": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_RESULT",
        "status": status,
        "execution_mode": "CLOSURE_REGISTRATION_ONLY_NO_EXECUTION",
        "production_status": "PUBLISHED_AND_VERIFIED_CLOSURE",
        "post_id": int(target.get("post_id", 0)),
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "ls6au_validated": ls6au_validation.get("status") == req_ls6au.get("required_validation_status"),
        "ls6au_production_status": str(ls6au_result.get("production_status", "")),
        "ls6au_completion_status": str(ls6au_result.get("completion_status", "")),
        "ls6au_post_publish_verified": bool(ls6au_result.get("post_publish_verified", False)),
        "ls6au_published_evidence_recorded": bool(ls6au_result.get("published_evidence_recorded", False)),
        "ls6au_rollback_readiness_recorded": bool(ls6au_result.get("rollback_readiness_recorded", False)),
        "ls6at_validated": ls6at_validation.get("status") == req_ls6at.get("required_validation_status"),
        "ls6at_production_status": str(ls6at_result.get("production_status", "")),
        "ls6at_updated_post_id": int(ls6at_result.get("updated_post_id", 0)),
        "ls6at_updated_fields": list(ls6at_result.get("updated_fields", [])),
        "ls6at_updated_status": str(ls6at_result.get("updated_status", "")),
        "start_ls_one_shot_publish_chain_closed": bool(closure_state.get("publish_chain_closed", False)),
        "closure_registration_executed": bool(closure_policy.get("closure_registration_executed", True)),
        "published_state_preserved": bool(closure_policy.get("published_state_preserved", True)),
        "post_publish_verified": bool(closure_policy.get("post_publish_verified", True)),
        "published_evidence_recorded": bool(closure_policy.get("published_evidence_recorded", True)),
        "rollback_readiness_recorded": bool(closure_policy.get("rollback_readiness_recorded", True)),
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_publish_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "wordpress_new_post_executed": False,
        "wordpress_content_update_executed": False,
        "wordpress_title_update_executed": False,
        "wordpress_meta_update_executed": False,
        "wordpress_schedule_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "credential_env_read_executed": False,
        "credential_values_loaded_for_output": False,
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "basic_auth_string_output": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "locked": status == STATUS_PASSED,
        "rerun_allowed": False,
        "ls6at_rerun_allowed": False,
        "ls6au_rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "completion_status": str(closure_state.get("status", "")),
        "recommended_next_action": str(closure_state.get("recommended_next_action", "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM")),
        "recommended_next_phase_options": list(closure_policy.get("recommended_next_phase_options", ["LS-MON-1", "LS-NEXT-1", "LS-REUSE-1"])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    for key, expected in policy.get("must_remain_false_flags", {}).items():
        observed = bool(payload.get(key, False)) if key in payload else False
        req(observed is bool(expected), f"{key} mismatch", errors)

    status = STATUS_PASSED if not errors and missing_flag_status is None else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status
    payload["status"] = status
    payload["locked"] = status == STATUS_PASSED

    lock_payload = {
        "phase": "LS-CLOSE-1",
        "document_type": "START_LS_ONE_SHOT_PUBLISH_CHAIN_CLOSURE_LOCK",
        "status": LOCKED_STATUS if status == STATUS_PASSED else status,
        "locked": status == STATUS_PASSED,
        "post_id": int(target.get("post_id", 0)),
        "target_post_status": str(target.get("final_status", "publish")),
        "start_ls_one_shot_publish_chain_closed": bool(closure_state.get("publish_chain_closed", False)),
        "closure_registration_executed": bool(closure_policy.get("closure_registration_executed", True)),
        "completion_status": str(closure_state.get("status", "")),
        "published_state_preserved": bool(closure_policy.get("published_state_preserved", True)),
        "post_publish_verified": bool(closure_policy.get("post_publish_verified", True)),
        "published_evidence_recorded": bool(closure_policy.get("published_evidence_recorded", True)),
        "rollback_readiness_recorded": bool(closure_policy.get("rollback_readiness_recorded", True)),
        "wordpress_api_call_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "delete_executed": False,
        "future_schedule_executed": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "rerun_allowed": False,
        "ls6at_rerun_allowed": False,
        "ls6au_rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "recommended_next_action": str(closure_state.get("recommended_next_action", "MONITOR_OR_BEGIN_NEXT_CONTENT_ITEM")),
        "recommended_next_phase_options": list(closure_policy.get("recommended_next_phase_options", ["LS-MON-1", "LS-NEXT-1", "LS-REUSE-1"])),
    }

    write_json(Path(args.closure_output), payload)
    write_json(Path(args.closure_lock_output), lock_payload)
    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
