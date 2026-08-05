#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_VALIDATED_GET_ONLY"
STATUS_NOT_VALIDATED = "LSMON1_POST183_PUBLISHED_STATE_MONITOR_NOT_VALIDATED"
PUBLIC_REST_UNAVAILABLE_WARNING = "PUBLIC_REST_UNAVAILABLE_BUT_PUBLIC_URL_REACHABLE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls_mon1_post183_published_state_monitor_policy.json",
    )
    parser.add_argument(
        "--monitor-result",
        default="exchange/runtime/start_ls_mon1_post183_published_state_monitor_result.json",
    )
    parser.add_argument(
        "--monitor-lock",
        default="exchange/locks/start_ls_mon1_post183_published_state_monitor.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls_mon1_post183_published_state_monitor_result.json",
    )
    parser.add_argument(
        "--ls-close1-result",
        default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json",
    )
    parser.add_argument(
        "--ls-close1-lock",
        default="exchange/locks/start_ls_close1_one_shot_publish_chain_closure.lock.json",
    )
    parser.add_argument(
        "--ls-close1-validation-result",
        default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_validation_result.json",
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
        "--output",
        default="exchange/logs/start_ls_mon1_post183_published_state_monitor_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls_mon1_post183_published_state_monitor_validation_report.md",
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
        "# LS-MON-1 Post-183 Published State Monitor Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- post_id: {payload.get('post_id', '')}",
        f"- recommended_next_action: {payload.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {item}" for item in payload["errors"])
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
    monitor_result = try_load_json(Path(args.monitor_result), errors)
    monitor_lock = try_load_json(Path(args.monitor_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls_close1_result = try_load_json(Path(args.ls_close1_result), errors)
    ls_close1_lock = try_load_json(Path(args.ls_close1_lock), errors)
    ls_close1_validation = try_load_json(Path(args.ls_close1_validation_result), errors)
    ls6au_result = try_load_json(Path(args.ls6au_result), errors)
    ls6au_lock = try_load_json(Path(args.ls6au_lock), errors)
    ls6au_validation = try_load_json(Path(args.ls6au_validation_result), errors)

    target = policy.get("target_post", {})
    req_close1 = policy.get("required_previous_phase", {}).get("ls_close1", {})
    req_ls6au = policy.get("required_previous_phase", {}).get("ls6au", {})
    monitor_policy = policy.get("monitor_policy", {})

    req(policy.get("phase") == "LS-MON-1", "policy.phase mismatch", errors)
    req(
        monitor_result.get("status") == "LSMON1_POST183_PUBLISHED_STATE_MONITOR_PASSED_GET_ONLY",
        "monitor status mismatch",
        errors,
    )
    req(monitor_result == run_result, "monitor result and run_result mismatch", errors)
    req(
        monitor_result.get("production_status") == "PUBLISHED_STATE_MONITORED",
        "production_status mismatch",
        errors,
    )
    req(int(monitor_result.get("post_id", 0)) == int(target.get("post_id", 0)), "post_id mismatch", errors)
    req(str(monitor_result.get("post_link", "")) == str(target.get("post_link", "")), "post_link mismatch", errors)
    req(bool(monitor_result.get("monitor_checkpoint_recorded", False)) is True, "monitor_checkpoint_recorded mismatch", errors)
    req(str(monitor_result.get("monitor_scope", "")) == str(monitor_policy.get("monitor_scope", "")), "monitor_scope mismatch", errors)
    req(str(monitor_result.get("monitor_window", "")) == str(monitor_policy.get("monitor_window", "")), "monitor_window mismatch", errors)
    req(str(monitor_result.get("monitor_checkpoint", "")) == str(monitor_policy.get("monitor_checkpoint", "")), "monitor_checkpoint mismatch", errors)

    req(bool(monitor_result.get("public_url_get_executed", False)) is True, "public_url_get_executed must be true", errors)
    req(bool(monitor_result.get("public_url_reachable", False)) is True, "public_url_reachable must be true", errors)
    req(bool(monitor_result.get("public_url_reachable_status_ok", False)) is True, "public_url_reachable_status_ok must be true", errors)
    req(bool(monitor_result.get("public_rest_get_executed", False)) is True, "public_rest_get_executed must be true", errors)

    public_rest_reachable = bool(monitor_result.get("public_rest_reachable", False))
    public_rest_warning = monitor_result.get("public_rest_warning")
    if public_rest_reachable:
        req(int(monitor_result.get("public_rest_returned_post_id", 0)) == int(target.get("post_id", 0)), "public_rest_returned_post_id mismatch", errors)
        req(str(monitor_result.get("public_rest_returned_post_status", "")) == str(target.get("expected_status", "")), "public_rest_returned_post_status mismatch", errors)
        req(bool(monitor_result.get("public_rest_status_verified", False)) is True, "public_rest_status_verified mismatch", errors)
    else:
        req(bool(monitor_result.get("public_url_reachable", False)) is True, "public URL unreachable when REST unavailable", errors)
        req(public_rest_warning == PUBLIC_REST_UNAVAILABLE_WARNING, "public_rest_warning mismatch", errors)

    req(bool(monitor_result.get("published_state_preserved", False)) is True, "published_state_preserved mismatch", errors)
    req(bool(monitor_result.get("post_publish_state_monitor_ok", False)) is True, "post_publish_state_monitor_ok mismatch", errors)

    req(
        ls_close1_result.get("status") == req_close1.get("required_run_status"),
        "LS-CLOSE-1 run status mismatch",
        errors,
    )
    req(
        ls_close1_validation.get("status") == req_close1.get("required_validation_status"),
        "LS-CLOSE-1 validation status mismatch",
        errors,
    )
    req(bool(ls_close1_lock.get("locked", False)) is True, "LS-CLOSE-1 lock mismatch", errors)
    req(
        str(ls_close1_result.get("completion_status", "")) == str(req_close1.get("required_completion_status", "")),
        "LS-CLOSE-1 completion status mismatch",
        errors,
    )

    req(ls6au_result.get("status") == req_ls6au.get("required_run_status"), "LS-6AU run status mismatch", errors)
    req(ls6au_validation.get("status") == req_ls6au.get("required_validation_status"), "LS-6AU validation status mismatch", errors)
    req(bool(ls6au_lock.get("locked", False)) is True, "LS-6AU lock mismatch", errors)
    req(str(ls6au_result.get("production_status", "")) == str(req_ls6au.get("required_production_status", "")), "LS-6AU production status mismatch", errors)
    req(str(ls6au_result.get("rest_returned_post_status", "")) == str(req_ls6au.get("required_rest_returned_post_status", "")), "LS-6AU rest status mismatch", errors)

    req(monitor_lock.get("status") == "LSMON1_POST183_PUBLISHED_STATE_MONITOR_LOCKED_GET_ONLY", "lock status mismatch", errors)
    req(bool(monitor_lock.get("locked", False)) is True, "lock locked mismatch", errors)

    req(
        str(monitor_result.get("recommended_next_action", ""))
        == str(monitor_policy.get("recommended_next_action", "")),
        "recommended_next_action mismatch",
        errors,
    )

    must_be_false = [
        "credential_env_read_executed",
        "credential_values_loaded_for_output",
        "credential_values_persisted",
        "credential_values_logged",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_generated",
        "authorization_header_output",
        "basic_auth_string_generated",
        "basic_auth_string_output",
        "wordpress_authenticated_api_call_executed",
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_publish_executed_by_this_phase",
        "publish_executed_by_this_phase",
        "post119_update_executed",
        "post183_update_executed_by_this_phase",
        "wordpress_new_post_executed",
        "wordpress_content_update_executed",
        "wordpress_title_update_executed",
        "wordpress_meta_update_executed",
        "wordpress_schedule_executed",
        "future_schedule_executed",
        "delete_executed",
        "rollback_executed",
        "unpublish_executed",
        "draft_revert_executed",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "rerun_allowed",
        "publish_rerun_allowed",
        "ls6oc1_rerun_executed",
    ]
    for key in must_be_false:
        req(bool(monitor_result.get(key, False)) is False, f"{key} must be false", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-MON-1",
        "document_type": "POST_183_PUBLISHED_STATE_MONITOR_VALIDATION_RESULT",
        "status": status,
        "run_status": str(monitor_result.get("status", "")),
        "execution_mode": str(monitor_result.get("execution_mode", "")),
        "production_status": str(monitor_result.get("production_status", "")),
        "post_id": int(monitor_result.get("post_id", 0)),
        "post_link": str(monitor_result.get("post_link", "")),
        "public_rest_url": str(monitor_result.get("public_rest_url", "")),
        "payload_title": str(monitor_result.get("payload_title", "")),
        "payload_asin": str(monitor_result.get("payload_asin", "")),
        "ls_close1_validated": bool(monitor_result.get("ls_close1_validated", False)),
        "ls_close1_completion_status": str(monitor_result.get("ls_close1_completion_status", "")),
        "ls6au_validated": bool(monitor_result.get("ls6au_validated", False)),
        "ls6au_production_status": str(monitor_result.get("ls6au_production_status", "")),
        "ls6au_rest_returned_post_status": str(monitor_result.get("ls6au_rest_returned_post_status", "")),
        "ls6au_public_url_reachable": bool(monitor_result.get("ls6au_public_url_reachable", False)),
        "monitor_checkpoint_recorded": bool(monitor_result.get("monitor_checkpoint_recorded", False)),
        "monitor_scope": str(monitor_result.get("monitor_scope", "")),
        "monitor_window": str(monitor_result.get("monitor_window", "")),
        "monitor_checkpoint": str(monitor_result.get("monitor_checkpoint", "")),
        "public_url_get_executed": bool(monitor_result.get("public_url_get_executed", False)),
        "public_url_http_status": monitor_result.get("public_url_http_status"),
        "public_url_reachable": bool(monitor_result.get("public_url_reachable", False)),
        "public_url_reachable_status_ok": bool(monitor_result.get("public_url_reachable_status_ok", False)),
        "public_rest_get_executed": bool(monitor_result.get("public_rest_get_executed", False)),
        "public_rest_http_status": monitor_result.get("public_rest_http_status"),
        "public_rest_reachable": bool(monitor_result.get("public_rest_reachable", False)),
        "public_rest_returned_post_id": monitor_result.get("public_rest_returned_post_id"),
        "public_rest_returned_post_status": monitor_result.get("public_rest_returned_post_status"),
        "public_rest_status_verified": bool(monitor_result.get("public_rest_status_verified", False)),
        "public_rest_warning": monitor_result.get("public_rest_warning"),
        "published_state_preserved": bool(monitor_result.get("published_state_preserved", False)),
        "post_publish_state_monitor_ok": bool(monitor_result.get("post_publish_state_monitor_ok", False)),
        "wordpress_authenticated_api_call_executed": bool(monitor_result.get("wordpress_authenticated_api_call_executed", False)),
        "credential_env_read_executed": bool(monitor_result.get("credential_env_read_executed", False)),
        "credential_values_loaded_for_output": bool(monitor_result.get("credential_values_loaded_for_output", False)),
        "credential_values_persisted": bool(monitor_result.get("credential_values_persisted", False)),
        "credential_values_logged": bool(monitor_result.get("credential_values_logged", False)),
        "credential_value_output": bool(monitor_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(monitor_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(monitor_result.get("credential_secret_output", False)),
        "secret_length_output": bool(monitor_result.get("secret_length_output", False)),
        "secret_hash_output": bool(monitor_result.get("secret_hash_output", False)),
        "authorization_header_generated": bool(monitor_result.get("authorization_header_generated", False)),
        "authorization_header_output": bool(monitor_result.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(monitor_result.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(monitor_result.get("basic_auth_string_output", False)),
        "wordpress_post_executed": bool(monitor_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(monitor_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(monitor_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(monitor_result.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(monitor_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_publish_executed_by_this_phase": bool(monitor_result.get("wordpress_publish_executed_by_this_phase", False)),
        "publish_executed_by_this_phase": bool(monitor_result.get("publish_executed_by_this_phase", False)),
        "post119_update_executed": bool(monitor_result.get("post119_update_executed", False)),
        "post183_update_executed_by_this_phase": bool(monitor_result.get("post183_update_executed_by_this_phase", False)),
        "wordpress_new_post_executed": bool(monitor_result.get("wordpress_new_post_executed", False)),
        "wordpress_content_update_executed": bool(monitor_result.get("wordpress_content_update_executed", False)),
        "wordpress_title_update_executed": bool(monitor_result.get("wordpress_title_update_executed", False)),
        "wordpress_meta_update_executed": bool(monitor_result.get("wordpress_meta_update_executed", False)),
        "wordpress_schedule_executed": bool(monitor_result.get("wordpress_schedule_executed", False)),
        "future_schedule_executed": bool(monitor_result.get("future_schedule_executed", False)),
        "delete_executed": bool(monitor_result.get("delete_executed", False)),
        "rollback_executed": bool(monitor_result.get("rollback_executed", False)),
        "unpublish_executed": bool(monitor_result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(monitor_result.get("draft_revert_executed", False)),
        "actual_publish_execution_runner_executed": bool(monitor_result.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(monitor_result.get("manual_publish_executed", False)),
        "manual_publish_allowed_by_this_phase": bool(monitor_result.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(monitor_result.get("manual_publish_execution_allowed_by_this_phase", False)),
        "locked": bool(monitor_result.get("locked", False)),
        "rerun_allowed": bool(monitor_result.get("rerun_allowed", False)),
        "publish_rerun_allowed": bool(monitor_result.get("publish_rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(monitor_result.get("ls6oc1_rerun_executed", False)),
        "recommended_next_action": str(monitor_result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(monitor_result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
