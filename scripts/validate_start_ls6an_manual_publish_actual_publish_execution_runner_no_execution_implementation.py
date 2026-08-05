#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY"

RUNTIME_STATUS_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RECORDED_NO_PUBLISH"
LOCK_STATUS_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCKED_NO_PUBLISH"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_policy.json",
    )
    parser.add_argument(
        "--runner-skeleton",
        default="scripts/run_start_ls6an_actual_publish_execution_runner_no_execution_skeleton.py",
    )
    parser.add_argument(
        "--runtime-result",
        default="exchange/runtime/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--lock-result",
        default="exchange/locks/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_validation_report.md",
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


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6AN Manual Publish Actual Publish Execution Runner No-Execution Implementation Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- runtime_status: {result['runtime_status']}",
        f"- lock_status: {result['lock_status']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
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


def check_false_flags(doc: dict[str, Any], errors: list[str], prefix: str, keys: list[str]) -> None:
    for key in keys:
        req(doc.get(key) is False, f"{prefix}.{key} must be false", errors)


def build_result(run_result: dict[str, Any], runtime_result: dict[str, Any], lock_result: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    return {
        "phase": "LS-6AN",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": run_result.get("post_id", 0),
        "post_link": run_result.get("post_link", ""),
        "payload_title": run_result.get("payload_title", ""),
        "payload_asin": run_result.get("payload_asin", ""),
        "returned_post_status": run_result.get("returned_post_status", ""),
        "runtime_status": runtime_result.get("status", ""),
        "lock_status": lock_result.get("status", ""),
        "actual_publish_execution_runner_no_execution_implementation_ready": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_ready", False)
        ),
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_gate_recorded": bool(
            run_result.get("actual_publish_execution_runner_implementation_gate_recorded", False)
        ),
        "actual_publish_execution_runner_implementation_gate_consumed": bool(
            run_result.get("actual_publish_execution_runner_implementation_gate_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": bool(
            run_result.get("actual_publish_execution_runner_implementation_allowed_by_this_phase", False)
        ),
        "actual_publish_execution_runner_implemented_by_this_phase": bool(
            run_result.get("actual_publish_execution_runner_implemented_by_this_phase", False)
        ),
        "actual_publish_execution_runner_file_created_by_this_phase": bool(
            run_result.get("actual_publish_execution_runner_file_created_by_this_phase", False)
        ),
        "actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase": bool(
            run_result.get("actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase", False)
        ),
        "actual_publish_execution_runner_live_publish_path_implemented_by_this_phase": bool(
            run_result.get("actual_publish_execution_runner_live_publish_path_implemented_by_this_phase", False)
        ),
        "actual_publish_execution_runner_network_call_enabled": bool(
            run_result.get("actual_publish_execution_runner_network_call_enabled", False)
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool(
            run_result.get("actual_publish_execution_runner_credential_read_enabled", False)
        ),
        "actual_publish_execution_runner_publish_enabled": bool(
            run_result.get("actual_publish_execution_runner_publish_enabled", False)
        ),
        "actual_publish_execution_runner_execution_enabled": bool(
            run_result.get("actual_publish_execution_runner_execution_enabled", False)
        ),
        "actual_publish_execution_runner_executed": bool(run_result.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(run_result.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(run_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(run_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(run_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(run_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(run_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(run_result.get("wordpress_delete_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "rerun_allowed": bool(run_result.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(run_result.get("ls6oc1_rerun_executed", False)),
        "requires_actual_publish_execution_runner_no_execution_validation": bool(
            run_result.get("requires_actual_publish_execution_runner_no_execution_validation", False)
        ),
        "requires_actual_publish_execution_runner_execution_approval_gate": bool(
            run_result.get("requires_actual_publish_execution_runner_execution_approval_gate", False)
        ),
        "requires_separate_publish_execution_phase": bool(run_result.get("requires_separate_publish_execution_phase", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "next_phase": run_result.get("next_phase", {}),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    runtime_result = try_load_json(Path(args.runtime_result), errors)
    lock_result = try_load_json(Path(args.lock_result), errors)
    run_result = try_load_json(Path(args.run_result), errors)

    req(policy.get("phase") == "LS-6AN", "policy.phase mismatch", errors)
    req(
        policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        "policy.execution_mode mismatch",
        errors,
    )

    req(run_result.get("status") == "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH", "run_result.status mismatch", errors)
    req(runtime_result.get("status") == RUNTIME_STATUS_READY, "runtime_result.status mismatch", errors)
    req(lock_result.get("status") == LOCK_STATUS_READY, "lock_result.status mismatch", errors)

    req(run_result.get("post_id") == 183, "run_result.post_id mismatch", errors)
    req(run_result.get("returned_post_status") == "draft", "run_result.returned_post_status mismatch", errors)
    req(run_result.get("actual_publish_execution_runner_no_execution_implementation_ready") is True, "no_execution_implementation_ready must be true", errors)
    req(run_result.get("actual_publish_execution_runner_implementation_gate_recorded") is True, "implementation gate recorded must be true", errors)
    req(run_result.get("actual_publish_execution_runner_implementation_allowed_by_this_phase") is True, "implementation allowed by this phase must be true", errors)
    req(run_result.get("actual_publish_execution_runner_implemented_by_this_phase") is True, "implemented_by_this_phase must be true", errors)
    req(run_result.get("actual_publish_execution_runner_file_created_by_this_phase") is True, "file_created_by_this_phase must be true", errors)

    false_flags = [
        "actual_publish_execution_runner_no_execution_implementation_consumed",
        "actual_publish_execution_runner_implementation_gate_consumed",
        "actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase",
        "actual_publish_execution_runner_live_publish_path_implemented_by_this_phase",
        "actual_publish_execution_runner_network_call_enabled",
        "actual_publish_execution_runner_credential_read_enabled",
        "actual_publish_execution_runner_publish_enabled",
        "actual_publish_execution_runner_execution_enabled",
        "actual_publish_execution_runner_executed",
        "manual_publish_executed",
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_put_executed",
        "wordpress_patch_executed",
        "wordpress_delete_executed",
        "wordpress_write_executed_by_this_phase",
        "wordpress_draft_creation_executed_by_this_phase",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "final_explicit_publish_execution_command_consumed",
        "actual_publish_execution_final_preflight_consumed",
        "actual_publish_runner_boundary_consumed",
        "actual_publish_execution_gate_consumed",
        "final_execution_command_consumed",
        "approval_label_consumed",
        "execute_now_confirmation_consumed",
        "actual_publish_execution_allowed_by_this_phase",
        "actual_runner_execution_allowed_by_this_phase",
        "manual_publish_allowed_by_this_phase",
        "manual_publish_execution_allowed_by_this_phase",
        "rerun_allowed",
        "ls6oc1_rerun_executed",
    ]
    check_false_flags(run_result, errors, "run_result", false_flags)

    req(run_result.get("requires_actual_publish_execution_runner_no_execution_validation") is True, "requires_actual_publish_execution_runner_no_execution_validation must be true", errors)
    req(run_result.get("requires_actual_publish_execution_runner_execution_approval_gate") is True, "requires_actual_publish_execution_runner_execution_approval_gate must be true", errors)
    req(run_result.get("requires_separate_publish_execution_phase") is True, "requires_separate_publish_execution_phase must be true", errors)
    req(run_result.get("publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    req(runtime_result.get("locked") is True, "runtime_result.locked must be true", errors)
    req(lock_result.get("locked") is True, "lock_result.locked must be true", errors)
    req(lock_result.get("requires_next_phase") == "LS-6AO", "lock_result.requires_next_phase mismatch", errors)

    next_phase = run_result.get("next_phase", {})
    req(next_phase.get("phase") == "LS-6AO", "next_phase.phase mismatch", errors)
    req(next_phase.get("execution_allowed") is False, "next_phase.execution_allowed must be false", errors)
    req(next_phase.get("requires_actual_publish_execution_runner_no_execution_validation") is True, "next_phase.requires_actual_publish_execution_runner_no_execution_validation must be true", errors)
    req(next_phase.get("requires_actual_publish_execution_runner_execution_approval_gate") is True, "next_phase.requires_actual_publish_execution_runner_execution_approval_gate must be true", errors)
    req(next_phase.get("requires_separate_publish_execution_phase") is True, "next_phase.requires_separate_publish_execution_phase must be true", errors)
    req(next_phase.get("publish_execution_still_blocked") is True, "next_phase.publish_execution_still_blocked must be true", errors)

    skeleton_path = Path(args.runner_skeleton)
    req(skeleton_path.exists(), f"runner skeleton missing: {skeleton_path}", errors)
    if skeleton_path.exists():
        source = skeleton_path.read_text(encoding="utf-8")
        for banned in [
            "requests.",
            "import requests",
            "urllib",
            "http.client",
            "load_dotenv",
            "credential.env",
            "Authorization",
            "wp-json",
            "wordpress_post_executed = True",
            "publish_enabled = True",
            "execution_enabled = True",
        ]:
            req(banned not in source, f"runner skeleton contains banned token: {banned}", errors)

    result = build_result(run_result, runtime_result, lock_result, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
