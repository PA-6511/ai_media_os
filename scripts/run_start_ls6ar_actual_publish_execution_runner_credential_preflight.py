#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_FAILED_NO_PUBLISH"
STATUS_MISSING_RECORD_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_RECORD_FLAG"
STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_CREDENTIAL_READ_ALLOW_FLAG"
STATUS_MISSING_NO_WORDPRESS_API_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_NO_WORDPRESS_API_FLAG"
STATUS_MISSING_NO_PUBLISH_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_NO_PUBLISH_FLAG"
STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_NO_RUNNER_EXECUTION_FLAG"
STATUS_MISSING_NO_SECRET_OUTPUT_FLAG = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_NOT_READY_MISSING_NO_SECRET_OUTPUT_FLAG"
LOCKED_STATUS = "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_LOCKED_NO_PUBLISH"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6ar_actual_publish_execution_runner_credential_preflight_policy.json",
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
        "--ls6aq-run-result",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--ls6aq-validation-result",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_validation_result.json",
    )
    parser.add_argument("--credential-env-path", default="/etc/ai-media-os/credential.env")
    parser.add_argument(
        "--credential-preflight-output",
        default="exchange/runtime/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--credential-preflight-lock-output",
        default="exchange/locks/start_ls6ar_actual_publish_execution_runner_credential_preflight.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6ar_actual_publish_execution_runner_credential_preflight_report.md",
    )
    parser.add_argument("--record-credential-preflight", action="store_true")
    parser.add_argument("--allow-credential-env-read", action="store_true")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-runner-execution", action="store_true")
    parser.add_argument("--require-no-secret-output", action="store_true")
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


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6AR Actual Publish Execution Runner Credential Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- phase: {result['phase']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- credential_env_exists: {result['credential_env_exists']}",
        f"- credential_env_readable: {result['credential_env_readable']}",
        f"- credential_required_keys_present: {result['credential_required_keys_present']}",
        f"- credential_required_keys_non_empty: {result['credential_required_keys_non_empty']}",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def choose_missing_flag_status(args: argparse.Namespace) -> str | None:
    if not args.record_credential_preflight:
        return STATUS_MISSING_RECORD_FLAG
    if not args.allow_credential_env_read:
        return STATUS_MISSING_CREDENTIAL_READ_ALLOW_FLAG
    if not args.require_no_wordpress_api:
        return STATUS_MISSING_NO_WORDPRESS_API_FLAG
    if not args.require_no_publish:
        return STATUS_MISSING_NO_PUBLISH_FLAG
    if not args.require_no_runner_execution:
        return STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG
    if not args.require_no_secret_output:
        return STATUS_MISSING_NO_SECRET_OUTPUT_FLAG
    return None


def build_next_phase(policy: dict[str, Any]) -> dict[str, Any]:
    next_phase = policy.get("next_phase", {})
    return {
        "phase": str(next_phase.get("phase", "")),
        "execution_allowed": bool(next_phase.get("execution_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(
            next_phase.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_publish_execution_allowed_by_this_phase": bool(
            next_phase.get("actual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_runner_execution_allowed_by_this_phase": bool(
            next_phase.get("actual_runner_execution_allowed_by_this_phase", False)
        ),
        "requires_actual_publish_execution_runner_final_command": bool(
            next_phase.get("requires_actual_publish_execution_runner_final_command", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            next_phase.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(next_phase.get("publish_execution_still_blocked", False)),
    }


def scan_credential_env(
    path: Path,
    required_keys: list[str],
    required_key_aliases: dict[str, list[str]],
) -> tuple[bool, bool, bool, bool, bool, bool]:
    credential_env_exists = path.exists()
    credential_env_readable = credential_env_exists and os.access(path, os.R_OK)
    credential_env_permission_checked = False
    credential_env_read_executed = False
    credential_required_keys_present = False
    credential_required_keys_non_empty = False

    if credential_env_exists:
        try:
            path.stat()
            credential_env_permission_checked = True
        except OSError:
            credential_env_permission_checked = False

    if credential_env_readable:
        present_keys: set[str] = set()
        non_empty_keys: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if not key:
                    continue
                present_keys.add(key)
                if value.strip() != "":
                    non_empty_keys.add(key)
        credential_env_read_executed = True
        def candidates(key: str) -> list[str]:
            return [key, *required_key_aliases.get(key, [])]

        credential_required_keys_present = all(
            any(c in present_keys for c in candidates(key)) for key in required_keys
        )
        credential_required_keys_non_empty = all(
            any(c in non_empty_keys for c in candidates(key)) for key in required_keys
        )

    return (
        credential_env_exists,
        credential_env_readable,
        credential_env_permission_checked,
        credential_env_read_executed,
        credential_required_keys_present,
        credential_required_keys_non_empty,
    )


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    missing_flag_status = choose_missing_flag_status(args)

    policy = try_load_json(Path(args.policy), errors)
    ls6aq_boundary = try_load_json(Path(args.ls6aq_boundary_result), errors)
    ls6aq_lock = try_load_json(Path(args.ls6aq_boundary_lock), errors)
    ls6aq_run = try_load_json(Path(args.ls6aq_run_result), errors)
    ls6aq_validation = try_load_json(Path(args.ls6aq_validation_result), errors)

    req(policy.get("phase") == "LS-6AR", "policy.phase mismatch", errors)
    req(
        policy.get("execution_mode") == "CREDENTIAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "policy.execution_mode mismatch",
        errors,
    )

    target = policy.get("target_post", {})
    req_prev = policy.get("required_previous_phase", {}).get("ls6aq", {})
    cred_conf = policy.get("credential_preflight", {})
    policy_flags = policy.get("credential_preflight_policy", {})

    req(ls6aq_boundary.get("status") == req_prev.get("required_run_status"), "LS-6AQ boundary status mismatch", errors)
    req(ls6aq_run.get("status") == req_prev.get("required_run_status"), "LS-6AQ run status mismatch", errors)
    req(
        ls6aq_validation.get("status") == req_prev.get("required_validation_status"),
        "LS-6AQ validation status mismatch",
        errors,
    )
    req(ls6aq_boundary.get("post_id") == req_prev.get("required_post_id"), "LS-6AQ post_id mismatch", errors)
    req(
        ls6aq_boundary.get("returned_post_status") == req_prev.get("required_returned_post_status"),
        "LS-6AQ returned_post_status mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_final_boundary_ready", False))
        is bool(req_prev.get("required_final_boundary_ready", True)),
        "LS-6AQ final boundary ready mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_final_boundary_consumed", False))
        is bool(req_prev.get("required_final_boundary_consumed", False)),
        "LS-6AQ final boundary consumed mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase", False))
        is bool(req_prev.get("required_final_boundary_allows_execution_by_this_phase", False)),
        "LS-6AQ boundary execution allowance mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_credential_preflight_required", False))
        is bool(req_prev.get("required_credential_preflight_required", True)),
        "LS-6AQ credential preflight required mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_final_command_required", False))
        is bool(req_prev.get("required_final_command_required", True)),
        "LS-6AQ final command required mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("actual_publish_execution_runner_separate_publish_execution_phase_required", False))
        is bool(req_prev.get("required_separate_publish_execution_phase_required", True)),
        "LS-6AQ separate publish phase required mismatch",
        errors,
    )
    req(
        bool(ls6aq_boundary.get("publish_execution_still_blocked", False))
        is bool(req_prev.get("required_publish_execution_still_blocked", True)),
        "LS-6AQ publish_execution_still_blocked mismatch",
        errors,
    )
    req(ls6aq_lock.get("post_id") == req_prev.get("required_post_id"), "LS-6AQ lock post_id mismatch", errors)

    required_keys = list(cred_conf.get("required_key_names", []))
    credential_env_path = Path(args.credential_env_path)

    required_key_aliases = {
        "WORDPRESS_SITE_URL": ["WORDPRESS_BASE_URL"],
    }

    (
        credential_env_exists,
        credential_env_readable,
        credential_env_permission_checked,
        credential_env_read_executed,
        credential_required_keys_present,
        credential_required_keys_non_empty,
    ) = scan_credential_env(credential_env_path, required_keys, required_key_aliases)

    req(credential_env_exists, "credential env missing", errors)
    req(credential_env_readable, "credential env unreadable", errors)
    req(credential_required_keys_present, "credential required key missing", errors)
    req(credential_required_keys_non_empty, "credential required key empty", errors)

    status = STATUS_PASSED if (not errors and missing_flag_status is None) else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status

    locked = status == STATUS_PASSED

    next_phase = build_next_phase(policy)

    payload = {
        "phase": "LS-6AR",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_RESULT",
        "status": status,
        "execution_mode": "CREDENTIAL_PREFLIGHT_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": int(target.get("post_id", 0)),
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "returned_post_status": str(ls6aq_boundary.get("returned_post_status", "")),
        "ls6aq_final_boundary_validated": ls6aq_validation.get("status") == req_prev.get("required_validation_status"),
        "actual_publish_execution_runner_credential_preflight_ready": bool(
            policy_flags.get("actual_publish_execution_runner_credential_preflight_ready", True)
        ),
        "actual_publish_execution_runner_credential_preflight_consumed": bool(
            policy_flags.get("actual_publish_execution_runner_credential_preflight_consumed", False)
        ),
        "actual_publish_execution_runner_final_boundary_ready": bool(
            policy_flags.get("actual_publish_execution_runner_final_boundary_ready", True)
        ),
        "actual_publish_execution_runner_final_boundary_consumed": bool(
            policy_flags.get("actual_publish_execution_runner_final_boundary_consumed", False)
        ),
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": bool(
            policy_flags.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase", False)
        ),
        "credential_env_path": str(credential_env_path),
        "credential_env_read_allowed_by_this_phase": bool(
            policy_flags.get("credential_env_read_allowed_by_this_phase", True)
        ),
        "credential_env_read_executed": credential_env_read_executed,
        "credential_env_exists": credential_env_exists,
        "credential_env_readable": credential_env_readable,
        "credential_env_permission_checked": credential_env_permission_checked,
        "credential_required_keys_present": credential_required_keys_present,
        "credential_required_keys_non_empty": credential_required_keys_non_empty,
        "credential_values_loaded_for_output": False,
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "locked": locked,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_final_command": bool(
            policy_flags.get("requires_actual_publish_execution_runner_final_command", True)
        ),
        "requires_separate_publish_execution_phase": bool(
            policy_flags.get("requires_separate_publish_execution_phase", True)
        ),
        "publish_execution_still_blocked": bool(policy_flags.get("publish_execution_still_blocked", True)),
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock_payload = {
        "phase": "LS-6AR",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_LOCK",
        "status": LOCKED_STATUS if locked else status,
        "locked": locked,
        "post_id": int(target.get("post_id", 0)),
        "target_post_status": str(ls6aq_boundary.get("returned_post_status", "")),
        "actual_publish_execution_runner_credential_preflight_ready": payload[
            "actual_publish_execution_runner_credential_preflight_ready"
        ],
        "actual_publish_execution_runner_credential_preflight_consumed": payload[
            "actual_publish_execution_runner_credential_preflight_consumed"
        ],
        "actual_publish_execution_runner_final_boundary_consumed": payload[
            "actual_publish_execution_runner_final_boundary_consumed"
        ],
        "credential_env_read_allowed_by_this_phase": payload["credential_env_read_allowed_by_this_phase"],
        "credential_env_read_executed": payload["credential_env_read_executed"],
        "credential_env_exists": payload["credential_env_exists"],
        "credential_env_readable": payload["credential_env_readable"],
        "credential_env_permission_checked": payload["credential_env_permission_checked"],
        "credential_required_keys_present": payload["credential_required_keys_present"],
        "credential_required_keys_non_empty": payload["credential_required_keys_non_empty"],
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_only_presence_check": True,
        "publish_executed": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6AS",
        "requires_actual_publish_execution_runner_final_command": payload[
            "requires_actual_publish_execution_runner_final_command"
        ],
        "requires_separate_publish_execution_phase": payload["requires_separate_publish_execution_phase"],
        "publish_execution_still_blocked": payload["publish_execution_still_blocked"],
    }

    write_json(Path(args.credential_preflight_output), payload)
    write_json(Path(args.credential_preflight_lock_output), lock_payload)
    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
