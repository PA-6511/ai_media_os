#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_READY = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY"
STATUS_NOT_READY_MISSING_RECORD_FLAG = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY_MISSING_RECORD_FLAG"
STATUS_NOT_READY_MISSING_SKELETON_FLAG = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY_MISSING_SKELETON_FLAG"
STATUS_NOT_READY_MISSING_ENFORCE_FLAG = "LS6AN_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY_MISSING_ENFORCE_FLAG"

RUNTIME_STATUS_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RECORDED_NO_PUBLISH"
RUNTIME_STATUS_NOT_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_NOT_READY"
LOCK_STATUS_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCKED_NO_PUBLISH"
LOCK_STATUS_NOT_READY = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_UNLOCKED_NO_PUBLISH"


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
        "--runtime-output",
        default="exchange/runtime/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--lock-output",
        default="exchange/locks/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_report.md",
    )
    parser.add_argument("--record-no-execution-implementation", action="store_true")
    parser.add_argument("--create-runner-skeleton-file", action="store_true")
    parser.add_argument("--enforce-no-network-no-credential-no-publish", action="store_true")
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
        "# LS-6AN Manual Publish Actual Publish Execution Runner No-Execution Implementation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- no_execution_implementation_ready: {result['actual_publish_execution_runner_no_execution_implementation_ready']}",
        f"- implementation_allowed_by_this_phase: {result['actual_publish_execution_runner_implementation_allowed_by_this_phase']}",
        f"- implementation_file_created_by_this_phase: {result['actual_publish_execution_runner_file_created_by_this_phase']}",
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


def flatten_values(data: Any, index: dict[str, list[Any]]) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            index.setdefault(k, []).append(v)
            flatten_values(v, index)
    elif isinstance(data, list):
        for item in data:
            flatten_values(item, index)


def map_required_key(required_key: str) -> str:
    if required_key in {
        "required_ready_status",
        "required_validation_status",
    }:
        return "status"
    if required_key == "required_gate_status":
        return "gate_status"
    if required_key == "required_command_status":
        return "command_status"
    if required_key == "required_execute_now_status":
        return "execute_now_status"
    if required_key.startswith("required_"):
        return required_key[len("required_") :]
    return required_key


def load_required_previous_phase_docs(
    policy_path: Path,
    policy: dict[str, Any],
    errors: list[str],
) -> dict[str, list[dict[str, Any]]]:
    docs_by_phase: dict[str, list[dict[str, Any]]] = {}
    prev = policy.get("required_previous_phase", {})
    if not isinstance(prev, dict):
        errors.append("policy.required_previous_phase must be object")
        return docs_by_phase

    for phase_name, phase_cfg in prev.items():
        if not isinstance(phase_cfg, dict):
            errors.append(f"policy.required_previous_phase.{phase_name} must be object")
            continue
        phase_docs: list[dict[str, Any]] = []
        for key, value in phase_cfg.items():
            if isinstance(value, str) and value.endswith(".json"):
                doc_path = policy_path.parent.parent / value
                phase_docs.append(try_load_json(doc_path, errors))
        docs_by_phase[phase_name] = phase_docs
    return docs_by_phase


def check_required_previous_phase(
    policy: dict[str, Any],
    docs_by_phase: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    prev = policy.get("required_previous_phase", {})

    for phase_name, phase_cfg in prev.items():
        if not isinstance(phase_cfg, dict):
            continue
        phase_index: dict[str, list[Any]] = {}
        for doc in docs_by_phase.get(phase_name, []):
            flatten_values(doc, phase_index)
        for key, expected in phase_cfg.items():
            if not key.startswith("required_"):
                continue
            target_key = map_required_key(key)
            values = phase_index.get(target_key, [])
            if expected not in values:
                errors.append(
                    f"required_previous_phase.{phase_name}.{key} mismatch: expected {expected!r} not found in key {target_key!r}"
                )


def build_common_result(status: str, runtime_status: str, lock_status: str, post_id: int, post_link: str, payload_title: str, payload_asin: str, returned_post_status: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6AN",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION",
        "runtime_status": runtime_status,
        "lock_status": lock_status,
        "post_id": post_id,
        "post_link": post_link,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "returned_post_status": returned_post_status,
        "actual_publish_execution_runner_no_execution_implementation_ready": status == STATUS_READY,
        "actual_publish_execution_runner_no_execution_implementation_consumed": False,
        "actual_publish_execution_runner_implementation_gate_recorded": True,
        "actual_publish_execution_runner_implementation_gate_consumed": False,
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": status == STATUS_READY,
        "actual_publish_execution_runner_implemented_by_this_phase": status == STATUS_READY,
        "actual_publish_execution_runner_file_created_by_this_phase": status == STATUS_READY,
        "actual_publish_execution_runner_live_wordpress_call_implemented_by_this_phase": False,
        "actual_publish_execution_runner_live_publish_path_implemented_by_this_phase": False,
        "actual_publish_execution_runner_network_call_enabled": False,
        "actual_publish_execution_runner_credential_read_enabled": False,
        "actual_publish_execution_runner_publish_enabled": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "separated_actual_publish_execution_runner_phase_gate_recorded": True,
        "separated_actual_publish_execution_runner_phase_gate_consumed": False,
        "actual_publish_execution_runner_final_boundary_ready": True,
        "actual_publish_execution_runner_final_boundary_consumed": False,
        "actual_publish_execution_runner_execute_now_recorded": True,
        "actual_publish_execution_runner_execute_now_consumed": False,
        "actual_publish_execution_runner_final_preflight_ready": True,
        "actual_publish_execution_runner_final_preflight_consumed": False,
        "actual_publish_execution_runner_boundary_ready": True,
        "actual_publish_execution_runner_boundary_consumed": False,
        "actual_publish_final_execution_command_recorded": True,
        "actual_publish_final_execution_command_consumed": False,
        "actual_publish_runner_final_gate_ready": True,
        "actual_publish_runner_final_gate_consumed": False,
        "actual_publish_final_preflight_ready": True,
        "actual_publish_final_preflight_consumed": False,
        "actual_publish_execution_boundary_ready": True,
        "actual_publish_execution_boundary_consumed": False,
        "actual_publish_execute_now_final_confirmation_consumed": False,
        "explicit_execute_now_for_actual_publish_required": True,
        "explicit_execute_now_for_actual_publish_received": True,
        "explicit_execute_now_for_actual_publish_consumed": False,
        "actual_publish_execution_allowed_by_this_phase": False,
        "actual_runner_execution_allowed_by_this_phase": False,
        "manual_publish_allowed_by_this_phase": False,
        "manual_publish_execution_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_creation_executed_by_this_phase": False,
        "wordpress_existing_post_update_executed": False,
        "wordpress_publish_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "post119_update_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "final_explicit_publish_execution_command_consumed": False,
        "actual_publish_execution_final_preflight_consumed": False,
        "actual_publish_runner_boundary_consumed": False,
        "actual_publish_execution_gate_consumed": False,
        "final_execution_command_consumed": False,
        "approval_label_consumed": False,
        "execute_now_confirmation_consumed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_actual_publish_execution_runner_no_execution_validation": True,
        "requires_actual_publish_execution_runner_execution_approval_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AO",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_no_execution_validation": True,
            "requires_actual_publish_execution_runner_execution_approval_gate": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_not_ready(output: Path, runtime_output: Path, lock_output: Path, report: Path, status: str, msg: str) -> None:
    result = build_common_result(status, RUNTIME_STATUS_NOT_READY, LOCK_STATUS_NOT_READY, 183, "", "", "", "", [msg])
    runtime_doc = {
        "phase": "LS-6AN",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RUNTIME",
        "status": RUNTIME_STATUS_NOT_READY,
        "locked": False,
        "errors": [msg],
        "generated_at": result["generated_at"],
    }
    lock_doc = {
        "phase": "LS-6AN",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCK",
        "status": LOCK_STATUS_NOT_READY,
        "locked": False,
        "rerun_allowed": False,
        "errors": [msg],
        "generated_at": result["generated_at"],
    }
    write_json(runtime_output, runtime_doc)
    write_json(lock_output, lock_doc)
    write_json(output, result)
    write_report(report, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()

    output_path = Path(args.output)
    runtime_output_path = Path(args.runtime_output)
    lock_output_path = Path(args.lock_output)
    report_path = Path(args.report)

    if not args.record_no_execution_implementation:
        write_not_ready(output_path, runtime_output_path, lock_output_path, report_path, STATUS_NOT_READY_MISSING_RECORD_FLAG, "missing --record-no-execution-implementation")
        return 0
    if not args.create_runner_skeleton_file:
        write_not_ready(output_path, runtime_output_path, lock_output_path, report_path, STATUS_NOT_READY_MISSING_SKELETON_FLAG, "missing --create-runner-skeleton-file")
        return 0
    if not args.enforce_no_network_no_credential_no_publish:
        write_not_ready(output_path, runtime_output_path, lock_output_path, report_path, STATUS_NOT_READY_MISSING_ENFORCE_FLAG, "missing --enforce-no-network-no-credential-no-publish")
        return 0

    errors: list[str] = []

    policy_path = Path(args.policy)
    policy = try_load_json(policy_path, errors)

    req(policy.get("phase") == "LS-6AN", "policy.phase mismatch", errors)
    req(
        policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_ONLY_NO_PUBLISH",
        "policy.execution_mode mismatch",
        errors,
    )

    target = policy.get("target_post", {})
    req(target.get("post_id") == 183, "policy.target_post.post_id mismatch", errors)
    req(target.get("expected_current_status") == "draft", "policy.target_post.expected_current_status mismatch", errors)

    docs_by_phase = load_required_previous_phase_docs(policy_path, policy, errors)
    check_required_previous_phase(policy, docs_by_phase, errors)

    runner_skeleton_path = Path(args.runner_skeleton)
    policy_skeleton_path = policy.get("runner_skeleton", {}).get("path")
    if isinstance(policy_skeleton_path, str) and policy_skeleton_path:
        policy_skeleton_abs = (policy_path.parent.parent / policy_skeleton_path).resolve()
        req(runner_skeleton_path.resolve() == policy_skeleton_abs, "runner_skeleton path mismatch with policy", errors)

    req(runner_skeleton_path.exists(), f"runner skeleton missing: {runner_skeleton_path}", errors)

    post_link = str(target.get("post_link", ""))
    payload_title = str(target.get("title", ""))
    payload_asin = str(target.get("asin", ""))
    returned_post_status = str(target.get("expected_current_status", ""))

    status = STATUS_READY if not errors else STATUS_NOT_READY

    result = build_common_result(
        status,
        RUNTIME_STATUS_READY if status == STATUS_READY else RUNTIME_STATUS_NOT_READY,
        LOCK_STATUS_READY if status == STATUS_READY else LOCK_STATUS_NOT_READY,
        int(target.get("post_id", 0)),
        post_link,
        payload_title,
        payload_asin,
        returned_post_status,
        errors,
    )

    runtime_doc = {
        "phase": "LS-6AN",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_RUNTIME",
        "status": RUNTIME_STATUS_READY if status == STATUS_READY else RUNTIME_STATUS_NOT_READY,
        "post_id": result["post_id"],
        "post_link": result["post_link"],
        "returned_post_status": result["returned_post_status"],
        "actual_publish_execution_runner_no_execution_implementation_ready": result[
            "actual_publish_execution_runner_no_execution_implementation_ready"
        ],
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "publish_execution_still_blocked": True,
        "locked": status == STATUS_READY,
        "errors": list(errors),
        "generated_at": result["generated_at"],
    }

    lock_doc = {
        "phase": "LS-6AN",
        "document_type": "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_LOCK",
        "status": LOCK_STATUS_READY if status == STATUS_READY else LOCK_STATUS_NOT_READY,
        "locked": status == STATUS_READY,
        "post_id": result["post_id"],
        "target_post_status": result["returned_post_status"],
        "actual_publish_execution_runner_no_execution_implementation_ready": result[
            "actual_publish_execution_runner_no_execution_implementation_ready"
        ],
        "actual_publish_execution_runner_no_execution_implementation_consumed": False,
        "actual_publish_execution_runner_execution_enabled": False,
        "actual_publish_execution_runner_executed": False,
        "rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "requires_next_phase": "LS-6AO",
        "requires_actual_publish_execution_runner_no_execution_validation": True,
        "requires_actual_publish_execution_runner_execution_approval_gate": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "errors": list(errors),
        "generated_at": result["generated_at"],
    }

    write_json(runtime_output_path, runtime_doc)
    write_json(lock_output_path, lock_doc)
    write_json(output_path, result)
    write_report(report_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
