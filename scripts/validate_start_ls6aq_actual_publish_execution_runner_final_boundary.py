#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH"
STATUS_NOT_READY = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6aq_actual_publish_execution_runner_final_boundary_policy.json",
    )
    parser.add_argument(
        "--boundary-result",
        default="exchange/runtime/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--boundary-lock",
        default="exchange/locks/start_ls6aq_actual_publish_execution_runner_final_boundary.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--ls6ap-ready-result",
        default="exchange/logs/start_ls6ap_actual_publish_execution_runner_execution_approval_gate_ready_result.json",
    )
    parser.add_argument(
        "--ls6ap-approval-gate-result",
        default="exchange/human_review/start_ls6ap_actual_publish_execution_runner_execution_approval_gate.json",
    )
    parser.add_argument(
        "--ls6ao-validation-result",
        default="exchange/runtime/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--ls6ao-validation-lock",
        default="exchange/locks/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation.lock.json",
    )
    parser.add_argument(
        "--ls6ao-validation-log",
        default="exchange/logs/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6aq_actual_publish_execution_runner_final_boundary_validation_report.md",
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
        "# LS-6AQ Actual Publish Execution Runner Final Boundary Validation Report",
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
    boundary_result = try_load_json(Path(args.boundary_result), errors)
    boundary_lock = try_load_json(Path(args.boundary_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6ap_ready = try_load_json(Path(args.ls6ap_ready_result), errors)
    ls6ap_approval = try_load_json(Path(args.ls6ap_approval_gate_result), errors)
    ls6ao_result = try_load_json(Path(args.ls6ao_validation_result), errors)
    ls6ao_lock = try_load_json(Path(args.ls6ao_validation_lock), errors)
    ls6ao_log = try_load_json(Path(args.ls6ao_validation_log), errors)

    req(policy.get("phase") == "LS-6AQ", "policy.phase mismatch", errors)

    target = policy.get("target_post", {})
    final_policy = policy.get("final_boundary_policy", {})
    post_id = int(target.get("post_id", 0))

    req(boundary_result.get("status") == "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH", "run status mismatch", errors)
    req(boundary_result == run_result, "boundary_result and run_result mismatch", errors)

    req(boundary_result.get("post_id") == post_id, "post_id mismatch", errors)
    req(boundary_result.get("returned_post_status") == "draft", "returned_post_status mismatch", errors)

    req(ls6ap_ready.get("status") == "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_READY_NO_PUBLISH", "LS-6AP ready status mismatch", errors)
    req(ls6ap_approval.get("gate_status") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AP approval gate status mismatch", errors)

    req(ls6ao_result.get("status") == "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH", "LS-6AO status mismatch", errors)
    req(ls6ao_log.get("status") == "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH", "LS-6AO log status mismatch", errors)
    req(ls6ao_lock.get("post_id") == post_id, "LS-6AO lock post_id mismatch", errors)

    req(bool_from(boundary_result, "actual_publish_execution_runner_final_boundary_consumed") is False, "final_boundary_consumed must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_execution_approval_gate_consumed") is False, "approval_gate_consumed must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase") is False, "final_boundary_allows_execution must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_credential_preflight_required") is True, "credential_preflight_required must be true", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_final_command_required") is True, "final_command_required must be true", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_separate_publish_execution_phase_required") is True, "separate_publish_phase_required must be true", errors)

    req(bool_from(boundary_result, "actual_publish_execution_runner_network_call_enabled") is False, "network_call_enabled must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_credential_read_enabled") is False, "credential_read_enabled must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_publish_enabled") is False, "publish_enabled must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_execution_enabled") is False, "execution_enabled must be false", errors)
    req(bool_from(boundary_result, "actual_publish_execution_runner_executed") is False, "runner executed must be false", errors)
    req(bool_from(boundary_result, "manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    req(bool_from(boundary_result, "wordpress_api_call_executed") is False, "wordpress_api_call_executed must be false", errors)
    req(bool_from(boundary_result, "credential_env_read_executed") is False, "credential_env_read_executed must be false", errors)
    req(bool_from(boundary_result, "publish_executed") is False, "publish_executed must be false", errors)
    req(bool_from(boundary_result, "rerun_allowed") is False, "rerun_allowed must be false", errors)

    req(str(boundary_result.get("next_phase", {}).get("phase", "")) == "LS-6AR", "next_phase mismatch", errors)
    req(bool_from(boundary_result, "publish_execution_still_blocked") is True, "publish_execution_still_blocked must be true", errors)

    must_false = policy.get("must_remain_false_flags", {})
    for key, expected in must_false.items():
        if key in boundary_result:
            observed = bool(boundary_result.get(key, False))
            req(observed is bool(expected), f"{key} mismatch", errors)

    req(
        bool_from(boundary_result, "actual_publish_execution_runner_final_boundary_ready")
        is bool(final_policy.get("actual_publish_execution_runner_final_boundary_ready", True)),
        "final_boundary_ready mismatch",
        errors,
    )

    req(boundary_lock.get("document_type") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_LOCK", "lock document_type mismatch", errors)
    req(bool(boundary_lock.get("locked", False)) is True, "lock must be true", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY

    payload = {
        "phase": "LS-6AQ",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATION_RESULT",
        "status": status,
        "run_status": str(boundary_result.get("status", "")),
        "execution_mode": str(boundary_result.get("execution_mode", "")),
        "production_status": str(boundary_result.get("production_status", "")),
        "post_id": int(boundary_result.get("post_id", 0)),
        "post_link": str(boundary_result.get("post_link", "")),
        "payload_title": str(boundary_result.get("payload_title", "")),
        "payload_asin": str(boundary_result.get("payload_asin", "")),
        "returned_post_status": str(boundary_result.get("returned_post_status", "")),
        "ls6ap_execution_approval_gate_validated": bool(boundary_result.get("ls6ap_execution_approval_gate_validated", False)),
        "ls6ao_validation_validated": bool(boundary_result.get("ls6ao_validation_validated", False)),
        "actual_publish_execution_runner_final_boundary_ready": bool(boundary_result.get("actual_publish_execution_runner_final_boundary_ready", False)),
        "actual_publish_execution_runner_final_boundary_consumed": bool(boundary_result.get("actual_publish_execution_runner_final_boundary_consumed", False)),
        "actual_publish_execution_runner_execution_approval_gate_consumed": bool(boundary_result.get("actual_publish_execution_runner_execution_approval_gate_consumed", False)),
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": bool(boundary_result.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase", False)),
        "actual_publish_execution_runner_credential_preflight_required": bool(boundary_result.get("actual_publish_execution_runner_credential_preflight_required", False)),
        "actual_publish_execution_runner_final_command_required": bool(boundary_result.get("actual_publish_execution_runner_final_command_required", False)),
        "actual_publish_execution_runner_separate_publish_execution_phase_required": bool(boundary_result.get("actual_publish_execution_runner_separate_publish_execution_phase_required", False)),
        "actual_publish_execution_runner_network_call_enabled": bool(boundary_result.get("actual_publish_execution_runner_network_call_enabled", False)),
        "actual_publish_execution_runner_credential_read_enabled": bool(boundary_result.get("actual_publish_execution_runner_credential_read_enabled", False)),
        "actual_publish_execution_runner_publish_enabled": bool(boundary_result.get("actual_publish_execution_runner_publish_enabled", False)),
        "actual_publish_execution_runner_execution_enabled": bool(boundary_result.get("actual_publish_execution_runner_execution_enabled", False)),
        "actual_publish_execution_runner_executed": bool(boundary_result.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(boundary_result.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(boundary_result.get("wordpress_api_call_executed", False)),
        "credential_env_read_executed": bool(boundary_result.get("credential_env_read_executed", False)),
        "publish_executed": bool(boundary_result.get("publish_executed", False)),
        "rerun_allowed": bool(boundary_result.get("rerun_allowed", False)),
        "next_phase": boundary_result.get("next_phase", {}),
        "publish_execution_still_blocked": bool(boundary_result.get("publish_execution_still_blocked", False)),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
