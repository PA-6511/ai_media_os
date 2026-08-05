#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED"
STATUS_NOT_VALIDATED = "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_NOT_VALIDATED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6at_actual_publish_execution_runner_separated_publish_execution_policy.json",
    )
    parser.add_argument(
        "--publish-execution-result",
        default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--publish-execution-lock",
        default="exchange/locks/start_ls6at_actual_publish_execution_runner_separated_publish_execution.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--ls6as-ready-result",
        default="exchange/logs/start_ls6as_actual_publish_execution_runner_final_command_ready_result.json",
    )
    parser.add_argument(
        "--ls6as-final-command-result",
        default="exchange/human_review/start_ls6as_actual_publish_execution_runner_final_command.json",
    )
    parser.add_argument(
        "--ls6ar-credential-preflight-result",
        default="exchange/runtime/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--ls6ar-validation-result",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_report.md",
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
        "# LS-6AT Separated Publish Execution Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
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


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    execution_result = try_load_json(Path(args.publish_execution_result), errors)
    execution_lock = try_load_json(Path(args.publish_execution_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6as_ready = try_load_json(Path(args.ls6as_ready_result), errors)
    ls6as_final = try_load_json(Path(args.ls6as_final_command_result), errors)
    ls6ar_preflight = try_load_json(Path(args.ls6ar_credential_preflight_result), errors)
    ls6ar_validation = try_load_json(Path(args.ls6ar_validation_result), errors)

    target = policy.get("target_post", {})
    post_id = int(target.get("post_id", 0))

    req(policy.get("phase") == "LS-6AT", "policy.phase mismatch", errors)

    req(
        execution_result.get("status")
        == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED",
        "status mismatch",
        errors,
    )
    req(execution_result == run_result, "execution_result and run_result mismatch", errors)
    req(execution_result.get("production_status") == "PUBLISHED", "production_status mismatch", errors)
    req(int(execution_result.get("post_id", 0)) == post_id, "post_id mismatch", errors)
    req(str(execution_result.get("pre_publish_returned_post_status", "")) == "draft", "pre status mismatch", errors)
    req(str(execution_result.get("post_publish_returned_post_status", "")) == "publish", "post status mismatch", errors)

    req(bool(execution_result.get("publish_executed", False)) is True, "publish_executed mismatch", errors)
    req(bool(execution_result.get("wordpress_api_call_executed", False)) is True, "wordpress_api_call_executed mismatch", errors)
    req(bool(execution_result.get("wordpress_get_executed", False)) is True, "wordpress_get_executed mismatch", errors)
    req(bool(execution_result.get("wordpress_post_executed", False)) is True, "wordpress_post_executed mismatch", errors)

    req(bool(execution_result.get("wordpress_put_executed", False)) is False, "wordpress_put_executed mismatch", errors)
    req(bool(execution_result.get("wordpress_patch_executed", False)) is False, "wordpress_patch_executed mismatch", errors)
    req(bool(execution_result.get("wordpress_delete_executed", False)) is False, "wordpress_delete_executed mismatch", errors)

    req(bool(execution_result.get("post119_update_executed", False)) is False, "post119_update_executed mismatch", errors)
    req(bool(execution_result.get("delete_executed", False)) is False, "delete_executed mismatch", errors)
    req(bool(execution_result.get("future_schedule_executed", False)) is False, "future_schedule_executed mismatch", errors)

    req(bool(execution_result.get("content_update_executed", False)) is False, "content_update_executed mismatch", errors)
    req(bool(execution_result.get("title_update_executed", False)) is False, "title_update_executed mismatch", errors)
    req(bool(execution_result.get("meta_update_executed", False)) is False, "meta_update_executed mismatch", errors)
    req(bool(execution_result.get("new_post_created", False)) is False, "new_post_created mismatch", errors)

    req(bool(execution_result.get("credential_value_output", False)) is False, "credential_value_output mismatch", errors)
    req(bool(execution_result.get("credential_value_persisted", False)) is False, "credential_value_persisted mismatch", errors)
    req(bool(execution_result.get("secret_length_output", False)) is False, "secret_length_output mismatch", errors)
    req(bool(execution_result.get("secret_hash_output", False)) is False, "secret_hash_output mismatch", errors)
    req(bool(execution_result.get("manual_publish_executed", False)) is False, "manual_publish_executed mismatch", errors)
    req(bool(execution_result.get("rerun_allowed", False)) is False, "rerun_allowed mismatch", errors)

    next_phase = execution_result.get("next_phase", {})
    req(str(next_phase.get("phase", "")) == "LS-6AU", "next_phase mismatch", errors)
    req(bool(execution_result.get("requires_post_publish_verification", False)) is True, "requires_post_publish_verification mismatch", errors)

    req(bool(execution_lock.get("locked", False)) is True, "lock mismatch", errors)
    req(execution_lock.get("status") == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_LOCKED_PUBLISHED", "lock status mismatch", errors)

    req(ls6as_ready.get("status") == "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_READY_NO_PUBLISH", "LS-6AS ready status mismatch", errors)
    req(ls6as_final.get("command_status") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AS final command status mismatch", errors)
    req(ls6ar_validation.get("status") == "LS6AR_ACTUAL_PUBLISH_EXECUTION_RUNNER_CREDENTIAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AR validation status mismatch", errors)
    req(bool(ls6ar_preflight.get("actual_publish_execution_runner_credential_preflight_ready", False)) is True, "LS-6AR preflight ready mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-6AT",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATION_RESULT",
        "status": status,
        "run_status": str(execution_result.get("status", "")),
        "execution_mode": str(execution_result.get("execution_mode", "")),
        "production_status": str(execution_result.get("production_status", "")),
        "post_id": int(execution_result.get("post_id", 0)),
        "post_link": str(execution_result.get("post_link", "")),
        "payload_title": str(execution_result.get("payload_title", "")),
        "payload_asin": str(execution_result.get("payload_asin", "")),
        "pre_publish_returned_post_status": str(execution_result.get("pre_publish_returned_post_status", "")),
        "post_publish_returned_post_status": str(execution_result.get("post_publish_returned_post_status", "")),
        "returned_post_status": str(execution_result.get("returned_post_status", "")),
        "ls6as_final_command_validated": bool(execution_result.get("ls6as_final_command_validated", False)),
        "ls6ar_credential_preflight_validated": bool(execution_result.get("ls6ar_credential_preflight_validated", False)),
        "publish_executed": bool(execution_result.get("publish_executed", False)),
        "wordpress_api_call_executed": bool(execution_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(execution_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(execution_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(execution_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(execution_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(execution_result.get("wordpress_delete_executed", False)),
        "post119_update_executed": bool(execution_result.get("post119_update_executed", False)),
        "delete_executed": bool(execution_result.get("delete_executed", False)),
        "future_schedule_executed": bool(execution_result.get("future_schedule_executed", False)),
        "content_update_executed": bool(execution_result.get("content_update_executed", False)),
        "title_update_executed": bool(execution_result.get("title_update_executed", False)),
        "meta_update_executed": bool(execution_result.get("meta_update_executed", False)),
        "new_post_created": bool(execution_result.get("new_post_created", False)),
        "credential_value_output": bool(execution_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(execution_result.get("credential_value_persisted", False)),
        "secret_length_output": bool(execution_result.get("secret_length_output", False)),
        "secret_hash_output": bool(execution_result.get("secret_hash_output", False)),
        "manual_publish_executed": bool(execution_result.get("manual_publish_executed", False)),
        "rerun_allowed": bool(execution_result.get("rerun_allowed", False)),
        "requires_post_publish_verification": bool(execution_result.get("requires_post_publish_verification", False)),
        "next_phase": execution_result.get("next_phase", {}),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
