#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALIDATED_STATUS = "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_VALIDATED_NO_PUBLISH"
NOT_READY_STATUS = "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_NOT_READY"
LOCKED_STATUS = "LS6AO_ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_LOCKED_NO_PUBLISH"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_policy.json",
    )
    parser.add_argument(
        "--ls6an-fix-a-normalization-result",
        default="exchange/runtime/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_result.json",
    )
    parser.add_argument(
        "--ls6an-fix-a-normalization-lock",
        default="exchange/locks/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization.lock.json",
    )
    parser.add_argument(
        "--ls6an-fix-a-validation-result",
        default="exchange/logs/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_validation_result.json",
    )
    parser.add_argument(
        "--ls6an-skeleton-result",
        default="exchange/runtime/start_ls6an_actual_publish_execution_runner_no_execution_skeleton_result.json",
    )
    parser.add_argument(
        "--ls6an-runner-skeleton",
        default="scripts/run_start_ls6an_actual_publish_execution_runner_no_execution_skeleton.py",
    )
    parser.add_argument(
        "--ls6an-implementation-result",
        default="exchange/runtime/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--ls6an-implementation-lock",
        default="exchange/locks/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation.lock.json",
    )
    parser.add_argument(
        "--ls6an-run-result",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--ls6an-validation-result",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--validation-output",
        default="exchange/runtime/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--validation-lock-output",
        default="exchange/locks/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6ao_actual_publish_execution_runner_no_execution_implementation_validation_report.md",
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
        "# LS-6AO Actual Publish Execution Runner No-Execution Implementation Validation Report",
        "",
        f"- phase: {result['phase']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6an_fix_a_status_normalization_validated: {result['ls6an_fix_a_status_normalization_validated']}",
        f"- ls6an_no_execution_implementation_validated: {result['ls6an_no_execution_implementation_validated']}",
        f"- runner_skeleton_static_safety_validated: {result['runner_skeleton_static_safety_validated']}",
        f"- source_artifacts_unchanged: {result['source_artifacts_unchanged']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def map_next_phase(next_phase_policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": next_phase_policy.get("phase", ""),
        "execution_allowed": bool(next_phase_policy.get("execution_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(
            next_phase_policy.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_publish_execution_allowed_by_this_phase": bool(
            next_phase_policy.get("actual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_runner_execution_allowed_by_this_phase": bool(
            next_phase_policy.get("actual_runner_execution_allowed_by_this_phase", False)
        ),
        "requires_actual_publish_execution_runner_execution_approval_gate": bool(
            next_phase_policy.get("requires_actual_publish_execution_runner_execution_approval_gate", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            next_phase_policy.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(next_phase_policy.get("publish_execution_still_blocked", False)),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    fixa_result = try_load_json(Path(args.ls6an_fix_a_normalization_result), errors)
    fixa_lock = try_load_json(Path(args.ls6an_fix_a_normalization_lock), errors)
    fixa_validation = try_load_json(Path(args.ls6an_fix_a_validation_result), errors)

    ls6an_skeleton_result = try_load_json(Path(args.ls6an_skeleton_result), errors)
    ls6an_impl_result = try_load_json(Path(args.ls6an_implementation_result), errors)
    ls6an_impl_lock = try_load_json(Path(args.ls6an_implementation_lock), errors)
    ls6an_run_result = try_load_json(Path(args.ls6an_run_result), errors)
    ls6an_validation = try_load_json(Path(args.ls6an_validation_result), errors)

    runner_skeleton_path = Path(args.ls6an_runner_skeleton)
    runner_skeleton_text = ""
    if runner_skeleton_path.exists():
        runner_skeleton_text = runner_skeleton_path.read_text(encoding="utf-8")
    else:
        errors.append(f"missing file: {runner_skeleton_path}")

    source_paths = [
        Path(args.ls6an_fix_a_normalization_result),
        Path(args.ls6an_fix_a_normalization_lock),
        Path(args.ls6an_fix_a_validation_result),
        Path(args.ls6an_skeleton_result),
        runner_skeleton_path,
        Path(args.ls6an_implementation_result),
        Path(args.ls6an_implementation_lock),
        Path(args.ls6an_run_result),
        Path(args.ls6an_validation_result),
    ]
    digest_before: dict[str, str] = {}
    for p in source_paths:
        if p.exists():
            digest_before[str(p)] = digest(p)

    req(policy.get("phase") == "LS-6AO", "policy.phase mismatch", errors)
    req(
        policy.get("execution_mode") == "NO_EXECUTION_IMPLEMENTATION_VALIDATION_ONLY_NO_PUBLISH",
        "policy.execution_mode mismatch",
        errors,
    )

    target = policy.get("target_post", {})
    expected_post_id = int(target.get("post_id", 0))
    expected_post_status = str(target.get("expected_current_status", ""))

    observed_post_id = int(ls6an_run_result.get("post_id", 0))
    observed_returned_status = str(ls6an_run_result.get("returned_post_status", ""))

    req(observed_post_id == expected_post_id, "post_id mismatch", errors)
    req(observed_returned_status == expected_post_status, "returned_post_status mismatch", errors)

    prev = policy.get("required_previous_phase", {})
    fixa_required = prev.get("ls6an_fix_a", {})
    ls6an_required = prev.get("ls6an", {})

    req(
        fixa_validation.get("status") == fixa_required.get("required_validation_status"),
        "ls6an-fix-a validation status mismatch",
        errors,
    )
    req(
        bool(fixa_result.get("source_artifacts_unchanged", False))
        is bool(fixa_required.get("required_source_artifacts_unchanged", True)),
        "source_artifacts_unchanged mismatch",
        errors,
    )
    req(
        bool(fixa_result.get("skeleton_status_alias_accepted", False))
        is bool(fixa_required.get("required_skeleton_status_alias_accepted", True)),
        "skeleton_status_alias_accepted mismatch",
        errors,
    )
    req(
        bool(fixa_result.get("run_status_alias_accepted", False))
        is bool(fixa_required.get("required_run_status_alias_accepted", True)),
        "run_status_alias_accepted mismatch",
        errors,
    )
    req(
        bool(fixa_result.get("status_normalized", False))
        is bool(fixa_required.get("required_status_normalized", True)),
        "status_normalized mismatch",
        errors,
    )
    req(
        bool(fixa_result.get("ls6an_validation_validated", False))
        is bool(fixa_required.get("required_ls6an_validation_validated", True)),
        "ls6an_validation_validated mismatch",
        errors,
    )

    skeleton_observed = str(ls6an_skeleton_result.get("status", ""))
    skeleton_canonical = str(ls6an_required.get("required_skeleton_canonical_status", ""))
    skeleton_alias = str(ls6an_required.get("accepted_skeleton_status_alias", ""))
    run_observed = str(ls6an_run_result.get("status", ""))
    run_canonical = str(ls6an_required.get("required_run_canonical_status", ""))
    run_alias = str(ls6an_required.get("accepted_run_status_alias", ""))
    validation_canonical = str(ls6an_required.get("required_validation_status", ""))

    req(skeleton_observed in {skeleton_canonical, skeleton_alias}, "skeleton status mismatch", errors)
    req(run_observed in {run_canonical, run_alias}, "run status mismatch", errors)
    req(str(ls6an_validation.get("status", "")) == validation_canonical, "ls6an validation status mismatch", errors)

    req(bool(ls6an_run_result.get("actual_publish_execution_runner_no_execution_implementation_ready", False)) is True, "implementation ready must be true", errors)
    req(bool(ls6an_run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)) is False, "implementation consumed must be false", errors)
    req(bool(ls6an_run_result.get("actual_publish_execution_runner_implementation_gate_consumed", False)) is False, "implementation gate consumed must be false", errors)
    req(bool(ls6an_run_result.get("actual_publish_execution_runner_file_created_by_this_phase", False)) is True, "runner file created flag must be true", errors)

    false_flags = policy.get("must_remain_false_flags", {})
    observed_doc = ls6an_run_result
    for key, expected in false_flags.items():
        if key == "runner_skeleton_reexecuted_by_this_phase":
            observed = False
        elif key == "actual_publish_execution_runner_reexecuted_by_this_phase":
            observed = False
        else:
            observed = bool(observed_doc.get(key, False))
        req(observed is bool(expected), f"{key} mismatch", errors)

    validation_policy = policy.get("validation_policy", {})

    ls6an_fix_a_status_normalization_validated = (
        fixa_validation.get("status")
        == fixa_required.get("required_validation_status")
    )
    ls6an_no_execution_implementation_validated = (
        str(ls6an_validation.get("status", "")) == validation_canonical
    )

    forbidden_tokens = list(policy.get("static_safety_scan", {}).get("forbidden_tokens", []))
    runner_skeleton_static_safety_validated = True
    for token in forbidden_tokens:
        if str(token) and str(token) in runner_skeleton_text:
            runner_skeleton_static_safety_validated = False
            errors.append(f"runner skeleton contains forbidden token: {token}")

    req(
        runner_skeleton_static_safety_validated
        is bool(validation_policy.get("runner_skeleton_static_safety_validated", True)),
        "runner_skeleton_static_safety_validated mismatch",
        errors,
    )

    req(
        ls6an_fix_a_status_normalization_validated
        is bool(validation_policy.get("ls6an_fix_a_status_normalization_validated", True)),
        "ls6an_fix_a_status_normalization_validated mismatch",
        errors,
    )
    req(
        ls6an_no_execution_implementation_validated
        is bool(validation_policy.get("ls6an_no_execution_implementation_validated", True)),
        "ls6an_no_execution_implementation_validated mismatch",
        errors,
    )

    digest_after: dict[str, str] = {}
    for p in source_paths:
        if p.exists():
            digest_after[str(p)] = digest(p)

    source_artifacts_unchanged = True
    for key, value in digest_before.items():
        if digest_after.get(key) != value:
            source_artifacts_unchanged = False
            errors.append(f"source artifact changed: {key}")

    req(
        source_artifacts_unchanged is bool(validation_policy.get("source_artifacts_unchanged", True)),
        "source_artifacts_unchanged mismatch",
        errors,
    )

    runner_skeleton_reexecuted_by_this_phase = False
    actual_publish_execution_runner_reexecuted_by_this_phase = False

    req(
        runner_skeleton_reexecuted_by_this_phase
        is bool(validation_policy.get("runner_skeleton_reexecuted_by_this_phase", False)),
        "runner_skeleton_reexecuted_by_this_phase mismatch",
        errors,
    )
    req(
        actual_publish_execution_runner_reexecuted_by_this_phase
        is bool(validation_policy.get("actual_publish_execution_runner_reexecuted_by_this_phase", False)),
        "actual_publish_execution_runner_reexecuted_by_this_phase mismatch",
        errors,
    )

    status = VALIDATED_STATUS if not errors else NOT_READY_STATUS
    locked = not errors

    next_phase = map_next_phase(policy.get("next_phase", {}))

    payload = {
        "phase": "LS-6AO",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_RESULT",
        "status": status,
        "execution_mode": "NO_EXECUTION_IMPLEMENTATION_VALIDATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": expected_post_id,
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "returned_post_status": observed_returned_status,
        "source_phase": "LS-6AN-FIX-A",
        "ls6an_fix_a_status_normalization_validated": ls6an_fix_a_status_normalization_validated,
        "ls6an_no_execution_implementation_validated": ls6an_no_execution_implementation_validated,
        "runner_skeleton_static_safety_validated": runner_skeleton_static_safety_validated,
        "source_artifacts_unchanged": source_artifacts_unchanged,
        "skeleton_status_canonical": skeleton_canonical,
        "run_status_canonical": run_canonical,
        "validation_status_canonical": validation_canonical,
        "skeleton_status_alias_accepted": bool(fixa_result.get("skeleton_status_alias_accepted", False)),
        "run_status_alias_accepted": bool(fixa_result.get("run_status_alias_accepted", False)),
        "status_normalized": bool(fixa_result.get("status_normalized", False)),
        "actual_publish_execution_runner_no_execution_implementation_ready": bool(
            ls6an_run_result.get("actual_publish_execution_runner_no_execution_implementation_ready", False)
        ),
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_gate_consumed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_implementation_gate_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": bool(
            ls6an_run_result.get("actual_publish_execution_runner_implementation_allowed_by_this_phase", False)
        ),
        "actual_publish_execution_runner_implemented_by_this_phase": bool(
            ls6an_run_result.get("actual_publish_execution_runner_implemented_by_this_phase", False)
        ),
        "actual_publish_execution_runner_file_created_by_this_phase": bool(
            ls6an_run_result.get("actual_publish_execution_runner_file_created_by_this_phase", False)
        ),
        "runner_skeleton_path": str(args.ls6an_runner_skeleton),
        "runner_skeleton_reexecuted_by_this_phase": runner_skeleton_reexecuted_by_this_phase,
        "actual_publish_execution_runner_reexecuted_by_this_phase": actual_publish_execution_runner_reexecuted_by_this_phase,
        "actual_publish_execution_runner_network_call_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_network_call_enabled", False)
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_credential_read_enabled", False)
        ),
        "actual_publish_execution_runner_publish_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_publish_enabled", False)
        ),
        "actual_publish_execution_runner_execution_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_execution_enabled", False)
        ),
        "actual_publish_execution_runner_executed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_executed", False)
        ),
        "manual_publish_executed": bool(ls6an_run_result.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(ls6an_run_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(ls6an_run_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(ls6an_run_result.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(ls6an_run_result.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(ls6an_run_result.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(ls6an_run_result.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(
            ls6an_run_result.get("wordpress_write_executed_by_this_phase", False)
        ),
        "wordpress_publish_executed": bool(ls6an_run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(ls6an_run_result.get("publish_executed", False)),
        "future_schedule_executed": bool(ls6an_run_result.get("future_schedule_executed", False)),
        "delete_executed": bool(ls6an_run_result.get("delete_executed", False)),
        "post119_update_executed": bool(ls6an_run_result.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(ls6an_run_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(ls6an_run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(ls6an_run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(ls6an_run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(ls6an_run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(ls6an_run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(ls6an_run_result.get("authorization_header_output", False)),
        "locked": locked,
        "rerun_allowed": bool(ls6an_run_result.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(ls6an_run_result.get("ls6oc1_rerun_executed", False)),
        "requires_actual_publish_execution_runner_execution_approval_gate": bool(
            ls6an_run_result.get("requires_actual_publish_execution_runner_execution_approval_gate", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            ls6an_run_result.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(ls6an_run_result.get("publish_execution_still_blocked", False)),
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock_payload = {
        "phase": "LS-6AO",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_NO_EXECUTION_IMPLEMENTATION_VALIDATION_LOCK",
        "status": LOCKED_STATUS if not errors else NOT_READY_STATUS,
        "locked": locked,
        "post_id": expected_post_id,
        "target_post_status": observed_returned_status,
        "source_phase": "LS-6AN-FIX-A",
        "ls6an_fix_a_status_normalization_validated": ls6an_fix_a_status_normalization_validated,
        "ls6an_no_execution_implementation_validated": ls6an_no_execution_implementation_validated,
        "runner_skeleton_static_safety_validated": runner_skeleton_static_safety_validated,
        "source_artifacts_unchanged": source_artifacts_unchanged,
        "runner_skeleton_reexecuted_by_this_phase": runner_skeleton_reexecuted_by_this_phase,
        "actual_publish_execution_runner_reexecuted_by_this_phase": actual_publish_execution_runner_reexecuted_by_this_phase,
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_gate_consumed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_implementation_gate_consumed", False)
        ),
        "actual_publish_execution_runner_network_call_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_network_call_enabled", False)
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_credential_read_enabled", False)
        ),
        "actual_publish_execution_runner_publish_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_publish_enabled", False)
        ),
        "actual_publish_execution_runner_execution_enabled": bool(
            ls6an_run_result.get("actual_publish_execution_runner_execution_enabled", False)
        ),
        "actual_publish_execution_runner_executed": bool(
            ls6an_run_result.get("actual_publish_execution_runner_executed", False)
        ),
        "manual_publish_executed": bool(ls6an_run_result.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(ls6an_run_result.get("wordpress_api_call_executed", False)),
        "credential_env_read_executed": bool(ls6an_run_result.get("credential_env_read_executed", False)),
        "publish_executed": bool(ls6an_run_result.get("publish_executed", False)),
        "rerun_allowed": bool(ls6an_run_result.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(ls6an_run_result.get("ls6oc1_rerun_executed", False)),
        "requires_next_phase": "LS-6AP",
        "requires_actual_publish_execution_runner_execution_approval_gate": bool(
            ls6an_run_result.get("requires_actual_publish_execution_runner_execution_approval_gate", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            ls6an_run_result.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(ls6an_run_result.get("publish_execution_still_blocked", False)),
        "errors": list(errors),
        "generated_at": payload["generated_at"],
    }

    write_json(Path(args.validation_output), payload)
    write_json(Path(args.validation_lock_output), lock_payload)
    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
