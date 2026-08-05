#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALIDATED_STATUS = "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_VALIDATED_NO_PUBLISH"
NOT_READY_STATUS = "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_NOT_READY"
NORMALIZATION_READY_STATUS = "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_READY_NO_PUBLISH"
NORMALIZATION_LOCKED_STATUS = "LS6AN_FIX_A_ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_LOCKED_NO_PUBLISH"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_policy.json",
    )
    parser.add_argument(
        "--skeleton-result",
        default="exchange/runtime/start_ls6an_actual_publish_execution_runner_no_execution_skeleton_result.json",
    )
    parser.add_argument(
        "--implementation-result",
        default="exchange/runtime/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--implementation-lock",
        default="exchange/locks/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_result.json",
    )
    parser.add_argument(
        "--validation-result",
        default="exchange/logs/start_ls6an_manual_publish_actual_publish_execution_runner_no_execution_implementation_validation_result.json",
    )
    parser.add_argument(
        "--normalization-output",
        default="exchange/runtime/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_result.json",
    )
    parser.add_argument(
        "--normalization-lock-output",
        default="exchange/locks/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_validation_report.md",
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


def write_report(path: Path, title: str, status: str, errors: list[str], body: list[str]) -> None:
    lines = [f"# {title}", "", *body, "", "## Errors"]
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- none")
    lines.append("")
    lines.append(f"- status: {status}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def pick(documents: list[dict[str, Any]], key: str, default: Any) -> Any:
    for doc in documents:
        if key in doc:
            return doc.get(key)
    return default


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
        "requires_actual_publish_execution_runner_no_execution_validation": bool(
            next_phase_policy.get("requires_actual_publish_execution_runner_no_execution_validation", False)
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

    policy_path = Path(args.policy)
    policy = try_load_json(policy_path, errors)

    skeleton_path = Path(args.skeleton_result)
    implementation_result_path = Path(args.implementation_result)
    implementation_lock_path = Path(args.implementation_lock)
    run_result_path = Path(args.run_result)
    validation_result_path = Path(args.validation_result)

    skeleton = try_load_json(skeleton_path, errors)
    implementation_result = try_load_json(implementation_result_path, errors)
    implementation_lock = try_load_json(implementation_lock_path, errors)
    run_result = try_load_json(run_result_path, errors)
    validation_result = try_load_json(validation_result_path, errors)

    source_paths = [
        skeleton_path,
        implementation_result_path,
        implementation_lock_path,
        run_result_path,
        validation_result_path,
    ]
    before_digest: dict[str, str] = {}
    for path in source_paths:
        if path.exists():
            before_digest[str(path)] = digest(path)

    req(policy.get("phase") == "LS-6AN-FIX-A", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "STATUS_NORMALIZATION_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)

    target_post = policy.get("target_post", {})
    expected_post_id = int(target_post.get("post_id", 0))
    expected_status = target_post.get("expected_current_status", "")

    observed_post_id = int(run_result.get("post_id", 0))
    observed_returned_status = str(run_result.get("returned_post_status", ""))

    req(observed_post_id == expected_post_id, "post_id mismatch", errors)
    req(observed_returned_status == expected_status, "returned_post_status mismatch", errors)

    normalization = policy.get("status_normalization", {})
    skeleton_norm = normalization.get("skeleton_status", {})
    run_norm = normalization.get("run_status", {})
    validation_norm = normalization.get("validation_status", {})

    skeleton_observed = str(skeleton.get("status", ""))
    run_observed = str(run_result.get("status", ""))
    validation_observed = str(validation_result.get("status", ""))

    skeleton_canonical = str(skeleton_norm.get("canonical", ""))
    run_canonical = str(run_norm.get("canonical", ""))
    validation_canonical = str(validation_norm.get("canonical", ""))

    skeleton_aliases = [str(x) for x in skeleton_norm.get("accepted_aliases", [])]
    run_aliases = [str(x) for x in run_norm.get("accepted_aliases", [])]

    skeleton_allowed = [skeleton_canonical, *skeleton_aliases]
    run_allowed = [run_canonical, *run_aliases]

    req(skeleton_observed in skeleton_allowed, "skeleton status is not canonical/accepted alias", errors)
    req(run_observed in run_allowed, "run status is not canonical/accepted alias", errors)
    req(validation_observed == validation_canonical, "validation status mismatch", errors)

    documents = [run_result, validation_result, implementation_result, implementation_lock]

    false_flags = policy.get("must_remain_false_flags", {})
    for key, expected in false_flags.items():
        observed = bool(pick(documents, key, False))
        req(observed is bool(expected), f"{key} mismatch", errors)

    true_flags = policy.get("must_remain_true_flags", {})

    source_artifacts_unchanged = True
    after_digest: dict[str, str] = {}
    for path in source_paths:
        if path.exists():
            after_digest[str(path)] = digest(path)
    for path_str, before in before_digest.items():
        after = after_digest.get(path_str)
        if after != before:
            source_artifacts_unchanged = False
            errors.append(f"source artifact changed: {path_str}")

    skeleton_alias_accepted = skeleton_observed in skeleton_aliases or skeleton_observed == skeleton_canonical
    run_alias_accepted = run_observed in run_aliases or run_observed == run_canonical
    status_normalized = skeleton_alias_accepted and run_alias_accepted and validation_observed == validation_canonical
    ls6an_validation_validated = validation_observed == validation_canonical

    req(ls6an_validation_validated is bool(true_flags.get("ls6an_validation_validated", True)), "ls6an_validation_validated mismatch", errors)
    req(skeleton_alias_accepted is bool(true_flags.get("skeleton_status_alias_accepted", True)), "skeleton_status_alias_accepted mismatch", errors)
    req(run_alias_accepted is bool(true_flags.get("run_status_alias_accepted", True)), "run_status_alias_accepted mismatch", errors)
    req(status_normalized is bool(true_flags.get("status_normalized", True)), "status_normalized mismatch", errors)
    req(source_artifacts_unchanged is bool(true_flags.get("source_artifacts_unchanged", True)), "source_artifacts_unchanged mismatch", errors)

    for key, expected in true_flags.items():
        if key in {
            "ls6an_validation_validated",
            "skeleton_status_alias_accepted",
            "run_status_alias_accepted",
            "status_normalized",
            "source_artifacts_unchanged",
        }:
            continue
        observed = bool(pick(documents, key, False))
        req(observed is bool(expected), f"{key} mismatch", errors)

    next_phase = map_next_phase(policy.get("next_phase", {}))

    normalized_result_status = (
        NORMALIZATION_READY_STATUS if not errors else NOT_READY_STATUS
    )
    locked = not errors

    normalization_result = {
        "phase": "LS-6AN-FIX-A",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_RESULT",
        "status": normalized_result_status,
        "execution_mode": "STATUS_NORMALIZATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": expected_post_id,
        "post_link": str(target_post.get("post_link", "")),
        "payload_title": str(target_post.get("title", "")),
        "payload_asin": str(target_post.get("asin", "")),
        "returned_post_status": observed_returned_status,
        "source_phase": "LS-6AN",
        "source_artifacts_unchanged": source_artifacts_unchanged,
        "skeleton_status_observed": skeleton_observed,
        "skeleton_status_canonical": skeleton_canonical,
        "skeleton_status_alias_accepted": skeleton_alias_accepted,
        "run_status_observed": run_observed,
        "run_status_canonical": run_canonical,
        "run_status_alias_accepted": run_alias_accepted,
        "validation_status_observed": validation_observed,
        "validation_status_canonical": validation_canonical,
        "status_normalized": status_normalized,
        "ls6an_validation_validated": ls6an_validation_validated,
        "actual_publish_execution_runner_no_execution_implementation_ready": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_ready", False)
        ),
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
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
        "wordpress_write_executed_by_this_phase": bool(run_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_publish_executed": bool(run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "future_schedule_executed": bool(run_result.get("future_schedule_executed", False)),
        "delete_executed": bool(run_result.get("delete_executed", False)),
        "post119_update_executed": bool(run_result.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "credential_value_persisted": bool(run_result.get("credential_value_persisted", False)),
        "credential_secret_output": bool(run_result.get("credential_secret_output", False)),
        "secret_length_output": bool(run_result.get("secret_length_output", False)),
        "secret_hash_output": bool(run_result.get("secret_hash_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": locked,
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
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    normalization_lock = {
        "phase": "LS-6AN-FIX-A",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_STATUS_NORMALIZATION_LOCK",
        "status": NORMALIZATION_LOCKED_STATUS if not errors else NOT_READY_STATUS,
        "locked": locked,
        "post_id": expected_post_id,
        "target_post_status": observed_returned_status,
        "source_phase": "LS-6AN",
        "source_artifacts_unchanged": source_artifacts_unchanged,
        "skeleton_status_alias_accepted": skeleton_alias_accepted,
        "run_status_alias_accepted": run_alias_accepted,
        "status_normalized": status_normalized,
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
        ),
        "actual_publish_execution_runner_implementation_gate_consumed": bool(
            run_result.get("actual_publish_execution_runner_implementation_gate_consumed", False)
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
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "rerun_allowed": bool(run_result.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(run_result.get("ls6oc1_rerun_executed", False)),
        "requires_next_phase": "LS-6AO",
        "requires_actual_publish_execution_runner_no_execution_validation": bool(
            run_result.get("requires_actual_publish_execution_runner_no_execution_validation", False)
        ),
        "requires_actual_publish_execution_runner_execution_approval_gate": bool(
            run_result.get("requires_actual_publish_execution_runner_execution_approval_gate", False)
        ),
        "requires_separate_publish_execution_phase": bool(run_result.get("requires_separate_publish_execution_phase", False)),
        "publish_execution_still_blocked": bool(run_result.get("publish_execution_still_blocked", False)),
        "errors": list(errors),
        "generated_at": normalization_result["generated_at"],
    }

    validation_payload = {
        "phase": "LS-6AN-FIX-A",
        "status": VALIDATED_STATUS if not errors else NOT_READY_STATUS,
        "execution_mode": "STATUS_NORMALIZATION_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": expected_post_id,
        "returned_post_status": observed_returned_status,
        "source_phase": "LS-6AN",
        "source_artifacts_unchanged": source_artifacts_unchanged,
        "skeleton_status_observed": skeleton_observed,
        "skeleton_status_canonical": skeleton_canonical,
        "skeleton_status_alias_accepted": skeleton_alias_accepted,
        "run_status_observed": run_observed,
        "run_status_canonical": run_canonical,
        "run_status_alias_accepted": run_alias_accepted,
        "validation_status_observed": validation_observed,
        "validation_status_canonical": validation_canonical,
        "status_normalized": status_normalized,
        "ls6an_validation_validated": ls6an_validation_validated,
        "actual_publish_execution_runner_no_execution_implementation_ready": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_ready", False)
        ),
        "actual_publish_execution_runner_no_execution_implementation_consumed": bool(
            run_result.get("actual_publish_execution_runner_no_execution_implementation_consumed", False)
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
        "wordpress_write_executed_by_this_phase": bool(run_result.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_publish_executed": bool(run_result.get("wordpress_publish_executed", False)),
        "publish_executed": bool(run_result.get("publish_executed", False)),
        "credential_env_read_executed": bool(run_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(run_result.get("credential_value_output", False)),
        "authorization_header_output": bool(run_result.get("authorization_header_output", False)),
        "locked": locked,
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
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": normalization_result["generated_at"],
    }

    write_json(Path(args.normalization_output), normalization_result)
    write_json(Path(args.normalization_lock_output), normalization_lock)
    write_json(Path(args.output), validation_payload)

    outputs = policy.get("outputs", {})
    normalization_report_path = policy_path.parent.parent / str(
        outputs.get(
            "normalization_report",
            "reports/start_ls6an_fix_a_actual_publish_execution_runner_status_normalization_report.md",
        )
    )

    write_report(
        normalization_report_path,
        "LS-6AN-FIX-A Actual Publish Execution Runner Status Normalization Report",
        normalization_result["status"],
        errors,
        [
            f"- phase: {normalization_result['phase']}",
            f"- source_phase: {normalization_result['source_phase']}",
            f"- post_id: {normalization_result['post_id']}",
            f"- returned_post_status: {normalization_result['returned_post_status']}",
            f"- skeleton_status_observed: {normalization_result['skeleton_status_observed']}",
            f"- skeleton_status_canonical: {normalization_result['skeleton_status_canonical']}",
            f"- run_status_observed: {normalization_result['run_status_observed']}",
            f"- run_status_canonical: {normalization_result['run_status_canonical']}",
            f"- validation_status_observed: {normalization_result['validation_status_observed']}",
            f"- validation_status_canonical: {normalization_result['validation_status_canonical']}",
            f"- source_artifacts_unchanged: {normalization_result['source_artifacts_unchanged']}",
            f"- status_normalized: {normalization_result['status_normalized']}",
        ],
    )

    write_report(
        Path(args.report),
        "LS-6AN-FIX-A Actual Publish Execution Runner Status Normalization Validation Report",
        validation_payload["status"],
        errors,
        [
            f"- phase: {validation_payload['phase']}",
            f"- post_id: {validation_payload['post_id']}",
            f"- returned_post_status: {validation_payload['returned_post_status']}",
            f"- skeleton_status_alias_accepted: {validation_payload['skeleton_status_alias_accepted']}",
            f"- run_status_alias_accepted: {validation_payload['run_status_alias_accepted']}",
            f"- status_normalized: {validation_payload['status_normalized']}",
            f"- ls6an_validation_validated: {validation_payload['ls6an_validation_validated']}",
            f"- publish_execution_still_blocked: {validation_payload['publish_execution_still_blocked']}",
            f"- next_phase: {validation_payload['next_phase']}",
        ],
    )

    print(json.dumps(validation_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
