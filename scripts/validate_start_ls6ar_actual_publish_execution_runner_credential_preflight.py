#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6ar_actual_publish_execution_runner_credential_preflight_policy.json",
    )
    parser.add_argument(
        "--credential-preflight-result",
        default="exchange/runtime/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--credential-preflight-lock",
        default="exchange/locks/start_ls6ar_actual_publish_execution_runner_credential_preflight.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--ls6aq-boundary-result",
        default="exchange/runtime/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--ls6aq-boundary-lock",
        default="exchange/locks/start_ls6aq_actual_publish_execution_runner_final_boundary.lock.json",
    )
    parser.add_argument(
        "--ls6aq-validation-result",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6ar_actual_publish_execution_runner_credential_preflight_validation_report.md",
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
        "# LS-6AR Actual Publish Execution Runner Credential Preflight Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- post_id: {payload.get('post_id', 0)}",
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


def bool_from(source: dict[str, Any], key: str) -> bool:
    return bool(source.get(key, False))


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    preflight_result = try_load_json(Path(args.credential_preflight_result), errors)
    preflight_lock = try_load_json(Path(args.credential_preflight_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6aq_boundary = try_load_json(Path(args.ls6aq_boundary_result), errors)
    ls6aq_lock = try_load_json(Path(args.ls6aq_boundary_lock), errors)
    ls6aq_validation = try_load_json(Path(args.ls6aq_validation_result), errors)

    req(policy.get("phase") == "LS-6AR", "policy.phase mismatch", errors)

    req(
        ls6aq_validation.get("status") == "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH",
        "LS-6AQ validation status mismatch",
        errors,
    )
    req(
        ls6aq_boundary.get("status") == "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH",
        "LS-6AQ run status mismatch",
        errors,
    )
    req(ls6aq_lock.get("locked") is True, "LS-6AQ lock mismatch", errors)

    req(
        preflight_result.get("status")
        == "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_PASSED_NO_PUBLISH",
        "run status mismatch",
        errors,
    )
    req(preflight_result == run_result, "run result mismatch", errors)

    req(bool_from(preflight_result, "actual_publish_execution_runner_credential_preflight_consumed") is False, "credential_preflight_consumed must be false", errors)
    req(bool_from(preflight_result, "actual_publish_execution_runner_final_boundary_consumed") is False, "final_boundary_consumed must be false", errors)
    req(bool_from(preflight_result, "credential_env_read_allowed_by_this_phase") is True, "credential_env_read_allowed_by_this_phase must be true", errors)
    req(bool_from(preflight_result, "credential_env_read_executed") is True, "credential_env_read_executed must be true", errors)
    req(bool_from(preflight_result, "credential_env_exists") is True, "credential_env_exists must be true", errors)
    req(bool_from(preflight_result, "credential_env_readable") is True, "credential_env_readable must be true", errors)
    req(bool_from(preflight_result, "credential_required_keys_present") is True, "credential_required_keys_present must be true", errors)
    req(bool_from(preflight_result, "credential_required_keys_non_empty") is True, "credential_required_keys_non_empty must be true", errors)

    req(bool_from(preflight_result, "credential_values_persisted") is False, "credential_values_persisted must be false", errors)
    req(bool_from(preflight_result, "credential_values_logged") is False, "credential_values_logged must be false", errors)
    req(bool_from(preflight_result, "credential_value_output") is False, "credential_value_output must be false", errors)
    req(bool_from(preflight_result, "credential_secret_output") is False, "credential_secret_output must be false", errors)
    req(bool_from(preflight_result, "secret_length_output") is False, "secret_length_output must be false", errors)
    req(bool_from(preflight_result, "secret_hash_output") is False, "secret_hash_output must be false", errors)
    req(bool_from(preflight_result, "authorization_header_generated") is False, "authorization_header_generated must be false", errors)
    req(bool_from(preflight_result, "authorization_header_output") is False, "authorization_header_output must be false", errors)
    req(bool_from(preflight_result, "basic_auth_string_generated") is False, "basic_auth_string_generated must be false", errors)
    req(bool_from(preflight_result, "basic_auth_string_output") is False, "basic_auth_string_output must be false", errors)

    req(bool_from(preflight_result, "wordpress_api_call_executed") is False, "wordpress_api_call_executed must be false", errors)
    req(bool_from(preflight_result, "wordpress_get_executed") is False, "wordpress_get_executed must be false", errors)
    req(bool_from(preflight_result, "wordpress_post_executed") is False, "wordpress_post_executed must be false", errors)
    req(bool_from(preflight_result, "wordpress_write_executed_by_this_phase") is False, "wordpress_write_executed_by_this_phase must be false", errors)
    req(bool_from(preflight_result, "wordpress_publish_executed") is False, "wordpress_publish_executed must be false", errors)
    req(bool_from(preflight_result, "publish_executed") is False, "publish_executed must be false", errors)

    req(bool_from(preflight_result, "actual_publish_execution_runner_executed") is False, "runner executed must be false", errors)
    req(bool_from(preflight_result, "manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    req(bool_from(preflight_result, "actual_publish_execution_allowed_by_this_phase") is False, "actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(bool_from(preflight_result, "actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(bool_from(preflight_result, "rerun_allowed") is False, "rerun_allowed must be false", errors)

    req(preflight_result.get("next_phase", {}).get("phase") == "LS-6AS", "next_phase mismatch", errors)
    req(bool_from(preflight_result, "publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    must_false = policy.get("must_remain_false_flags", {})
    for key, expected in must_false.items():
        if key in preflight_result:
            req(bool(preflight_result.get(key, False)) is bool(expected), f"{key} mismatch", errors)

    req(preflight_lock.get("document_type") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_LOCK", "lock document_type mismatch", errors)
    req(bool(preflight_lock.get("locked", False)) is True, "lock must be true", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY

    payload = {
        "phase": "LS-6AR",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATION_RESULT",
        "status": status,
        "run_status": str(preflight_result.get("status", "")),
        "execution_mode": str(preflight_result.get("execution_mode", "")),
        "production_status": str(preflight_result.get("production_status", "")),
        "post_id": int(preflight_result.get("post_id", 0)),
        "post_link": str(preflight_result.get("post_link", "")),
        "payload_title": str(preflight_result.get("payload_title", "")),
        "payload_asin": str(preflight_result.get("payload_asin", "")),
        "returned_post_status": str(preflight_result.get("returned_post_status", "")),
        "ls6aq_final_boundary_validated": bool(preflight_result.get("ls6aq_final_boundary_validated", False)),
        "actual_publish_execution_runner_credential_preflight_ready": bool(preflight_result.get("actual_publish_execution_runner_credential_preflight_ready", False)),
        "actual_publish_execution_runner_credential_preflight_consumed": bool(preflight_result.get("actual_publish_execution_runner_credential_preflight_consumed", False)),
        "credential_env_read_allowed_by_this_phase": bool(preflight_result.get("credential_env_read_allowed_by_this_phase", False)),
        "credential_env_read_executed": bool(preflight_result.get("credential_env_read_executed", False)),
        "credential_env_exists": bool(preflight_result.get("credential_env_exists", False)),
        "credential_env_readable": bool(preflight_result.get("credential_env_readable", False)),
        "credential_required_keys_present": bool(preflight_result.get("credential_required_keys_present", False)),
        "credential_required_keys_non_empty": bool(preflight_result.get("credential_required_keys_non_empty", False)),
        "credential_values_persisted": bool(preflight_result.get("credential_values_persisted", False)),
        "credential_values_logged": bool(preflight_result.get("credential_values_logged", False)),
        "credential_value_output": bool(preflight_result.get("credential_value_output", False)),
        "credential_secret_output": bool(preflight_result.get("credential_secret_output", False)),
        "secret_length_output": bool(preflight_result.get("secret_length_output", False)),
        "secret_hash_output": bool(preflight_result.get("secret_hash_output", False)),
        "authorization_header_generated": bool(preflight_result.get("authorization_header_generated", False)),
        "authorization_header_output": bool(preflight_result.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(preflight_result.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(preflight_result.get("basic_auth_string_output", False)),
        "wordpress_api_call_executed": bool(preflight_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(preflight_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(preflight_result.get("wordpress_post_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(preflight_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_publish_executed": bool(preflight_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(preflight_result.get("publish_executed", False)),
        "actual_publish_execution_runner_executed": bool(preflight_result.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(preflight_result.get("manual_publish_executed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(preflight_result.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(preflight_result.get("actual_runner_execution_allowed_by_this_phase", False)),
        "rerun_allowed": bool(preflight_result.get("rerun_allowed", False)),
        "next_phase": preflight_result.get("next_phase", {}),
        "publish_execution_still_blocked": bool(preflight_result.get("publish_execution_still_blocked", False)),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
