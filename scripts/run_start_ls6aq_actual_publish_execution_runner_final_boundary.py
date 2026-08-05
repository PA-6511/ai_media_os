#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_PASSED_NO_PUBLISH"
STATUS_FAILED = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_FAILED_NO_PUBLISH"
STATUS_MISSING_RECORD_FLAG = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_RECORD_FLAG"
STATUS_MISSING_NO_WORDPRESS_API_FLAG = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_NO_WORDPRESS_API_FLAG"
STATUS_MISSING_NO_CREDENTIAL_READ_FLAG = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_NO_CREDENTIAL_READ_FLAG"
STATUS_MISSING_NO_PUBLISH_FLAG = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_NO_PUBLISH_FLAG"
STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_NOT_READY_MISSING_NO_RUNNER_EXECUTION_FLAG"
LOCKED_STATUS = "LS6AQ_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_LOCKED_NO_PUBLISH"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6aq_actual_publish_execution_runner_final_boundary_policy.json",
    )
    parser.add_argument(
        "--ls6ap-template-result",
        default="exchange/logs/start_ls6ap_actual_publish_execution_runner_execution_approval_gate_template_result.json",
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
        "--boundary-output",
        default="exchange/runtime/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--boundary-lock-output",
        default="exchange/locks/start_ls6aq_actual_publish_execution_runner_final_boundary.lock.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6aq_actual_publish_execution_runner_final_boundary_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6aq_actual_publish_execution_runner_final_boundary_report.md",
    )
    parser.add_argument("--record-final-boundary", action="store_true")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-runner-execution", action="store_true")
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
        "# LS-6AQ Actual Publish Execution Runner Final Boundary Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- phase: {result['phase']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6ap_execution_approval_gate_validated: {result['ls6ap_execution_approval_gate_validated']}",
        f"- ls6ao_validation_validated: {result['ls6ao_validation_validated']}",
        f"- actual_publish_execution_runner_final_boundary_ready: {result['actual_publish_execution_runner_final_boundary_ready']}",
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


def bool_from(source: dict[str, Any], key: str) -> bool:
    return bool(source.get(key, False))


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
        "requires_actual_publish_execution_runner_credential_preflight": bool(
            next_phase.get("requires_actual_publish_execution_runner_credential_preflight", False)
        ),
        "requires_actual_publish_execution_runner_final_command": bool(
            next_phase.get("requires_actual_publish_execution_runner_final_command", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            next_phase.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(next_phase.get("publish_execution_still_blocked", False)),
    }


def choose_missing_flag_status(args: argparse.Namespace) -> str | None:
    if not args.record_final_boundary:
        return STATUS_MISSING_RECORD_FLAG
    if not args.require_no_wordpress_api:
        return STATUS_MISSING_NO_WORDPRESS_API_FLAG
    if not args.require_no_credential_read:
        return STATUS_MISSING_NO_CREDENTIAL_READ_FLAG
    if not args.require_no_publish:
        return STATUS_MISSING_NO_PUBLISH_FLAG
    if not args.require_no_runner_execution:
        return STATUS_MISSING_NO_RUNNER_EXECUTION_FLAG
    return None


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    missing_flag_status = choose_missing_flag_status(args)

    policy = try_load_json(Path(args.policy), errors)
    ls6ap_template = try_load_json(Path(args.ls6ap_template_result), errors)
    ls6ap_ready = try_load_json(Path(args.ls6ap_ready_result), errors)
    ls6ap_approval = try_load_json(Path(args.ls6ap_approval_gate_result), errors)
    ls6ao_result = try_load_json(Path(args.ls6ao_validation_result), errors)
    ls6ao_lock = try_load_json(Path(args.ls6ao_validation_lock), errors)
    ls6ao_log = try_load_json(Path(args.ls6ao_validation_log), errors)

    req(policy.get("phase") == "LS-6AQ", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "FINAL_BOUNDARY_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)

    target = policy.get("target_post", {})
    ls6ap_req = policy.get("required_previous_phase", {}).get("ls6ap", {})
    ls6ao_req = policy.get("required_previous_phase", {}).get("ls6ao", {})
    final_policy = policy.get("final_boundary_policy", {})

    post_id = int(target.get("post_id", 0))
    expected_status = str(target.get("expected_current_status", ""))

    req(ls6ap_template.get("status") == ls6ap_req.get("required_template_status"), "LS-6AP template status mismatch", errors)
    req(ls6ap_ready.get("status") == ls6ap_req.get("required_ready_status"), "LS-6AP ready status mismatch", errors)
    req(ls6ap_ready.get("gate_status") == ls6ap_req.get("required_gate_status"), "LS-6AP gate status mismatch", errors)
    req(ls6ap_ready.get("post_id") == post_id, "LS-6AP post_id mismatch", errors)
    req(ls6ap_ready.get("returned_post_status") == expected_status, "LS-6AP returned_post_status mismatch", errors)

    req(
        ls6ap_ready.get("actual_publish_execution_runner_execution_approval_gate_label")
        == ls6ap_req.get("required_approval_gate_label"),
        "LS-6AP approval gate label mismatch",
        errors,
    )

    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_approval_gate_consumed", False))
        is bool(ls6ap_req.get("required_approval_gate_consumed", False)),
        "LS-6AP approval gate consumed mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_approval_allowed_by_this_phase", False))
        is bool(ls6ap_req.get("required_execution_approval_allowed_by_this_phase", False)),
        "LS-6AP execution approval allowed mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_approved_for_later_phase", False))
        is bool(ls6ap_req.get("required_approved_for_later_phase", True)),
        "LS-6AP approved_for_later_phase mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_requires_later_final_boundary", False))
        is bool(ls6ap_req.get("required_later_final_boundary", True)),
        "LS-6AP later final boundary requirement mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_requires_later_credential_preflight", False))
        is bool(ls6ap_req.get("required_later_credential_preflight", True)),
        "LS-6AP later credential preflight requirement mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_requires_later_final_command", False))
        is bool(ls6ap_req.get("required_later_final_command", True)),
        "LS-6AP later final command requirement mismatch",
        errors,
    )
    req(
        bool(ls6ap_ready.get("actual_publish_execution_runner_execution_requires_separate_publish_execution_phase", False))
        is bool(ls6ap_req.get("required_separate_publish_phase", True)),
        "LS-6AP separate publish phase requirement mismatch",
        errors,
    )

    approval_gate = ls6ap_approval.get("approval_gate", {})
    approval_current = ls6ap_approval.get("current_phase_execution", {})

    req(ls6ap_approval.get("gate_status") == ls6ap_req.get("required_gate_status"), "LS-6AP approval result gate status mismatch", errors)
    req(
        approval_gate.get("actual_publish_execution_runner_execution_approval_gate_label")
        == ls6ap_req.get("required_approval_gate_label"),
        "LS-6AP approval result label mismatch",
        errors,
    )
    req(
        bool(approval_gate.get("actual_publish_execution_runner_execution_approval_gate_consumed", False))
        is bool(ls6ap_req.get("required_approval_gate_consumed", False)),
        "LS-6AP approval result consumed mismatch",
        errors,
    )

    req(ls6ao_result.get("status") == ls6ao_req.get("required_validation_status"), "LS-6AO validation status mismatch", errors)
    req(ls6ao_log.get("status") == ls6ao_req.get("required_validation_status"), "LS-6AO validation log status mismatch", errors)
    req(ls6ao_result.get("post_id") == post_id, "LS-6AO post_id mismatch", errors)
    req(ls6ao_result.get("returned_post_status") == expected_status, "LS-6AO returned_post_status mismatch", errors)
    req(ls6ao_lock.get("post_id") == post_id, "LS-6AO lock post_id mismatch", errors)

    req(
        bool(ls6ao_result.get("ls6an_fix_a_status_normalization_validated", False))
        is bool(ls6ao_req.get("required_ls6an_fix_a_status_normalization_validated", True)),
        "LS-6AO fix-a validation mismatch",
        errors,
    )
    req(
        bool(ls6ao_result.get("ls6an_no_execution_implementation_validated", False))
        is bool(ls6ao_req.get("required_ls6an_no_execution_implementation_validated", True)),
        "LS-6AO no-execution implementation validation mismatch",
        errors,
    )
    req(
        bool(ls6ao_result.get("runner_skeleton_static_safety_validated", False))
        is bool(ls6ao_req.get("required_runner_skeleton_static_safety_validated", True)),
        "LS-6AO runner skeleton static safety mismatch",
        errors,
    )
    req(
        bool(ls6ao_result.get("source_artifacts_unchanged", False))
        is bool(ls6ao_req.get("required_source_artifacts_unchanged", True)),
        "LS-6AO source artifacts unchanged mismatch",
        errors,
    )

    sources_for_false = [ls6ap_ready, approval_gate, approval_current, ls6ao_result, ls6ao_lock]
    for key, expected in policy.get("must_remain_false_flags", {}).items():
        observed = False
        for src in sources_for_false:
            if key in src:
                observed = bool(src.get(key, False))
                break
        req(observed is bool(expected), f"{key} mismatch", errors)

    ls6ap_execution_approval_gate_validated = (
        ls6ap_ready.get("status") == ls6ap_req.get("required_ready_status")
        and ls6ap_ready.get("gate_status") == ls6ap_req.get("required_gate_status")
        and ls6ap_ready.get("actual_publish_execution_runner_execution_approval_gate_label")
        == ls6ap_req.get("required_approval_gate_label")
    )
    ls6ao_validation_validated = ls6ao_result.get("status") == ls6ao_req.get("required_validation_status")

    status = STATUS_PASSED if (not errors and missing_flag_status is None) else STATUS_FAILED
    if missing_flag_status is not None:
        status = missing_flag_status

    locked = status == STATUS_PASSED

    next_phase = build_next_phase(policy)

    payload = {
        "phase": "LS-6AQ",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_RESULT",
        "status": status,
        "execution_mode": "FINAL_BOUNDARY_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": post_id,
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "returned_post_status": str(ls6ap_ready.get("returned_post_status", "")),
        "ls6ap_execution_approval_gate_validated": ls6ap_execution_approval_gate_validated,
        "ls6ao_validation_validated": ls6ao_validation_validated,
        "actual_publish_execution_runner_final_boundary_ready": bool(
            final_policy.get("actual_publish_execution_runner_final_boundary_ready", True)
        ),
        "actual_publish_execution_runner_final_boundary_consumed": bool(
            final_policy.get("actual_publish_execution_runner_final_boundary_consumed", False)
        ),
        "actual_publish_execution_runner_execution_approval_gate_recorded": bool(
            final_policy.get("actual_publish_execution_runner_execution_approval_gate_recorded", True)
        ),
        "actual_publish_execution_runner_execution_approval_gate_label": str(
            ls6ap_req.get("required_approval_gate_label", "")
        ),
        "actual_publish_execution_runner_execution_approval_gate_consumed": bool(
            final_policy.get("actual_publish_execution_runner_execution_approval_gate_consumed", False)
        ),
        "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": bool(
            final_policy.get("actual_publish_execution_runner_execution_approval_allowed_by_this_phase", False)
        ),
        "actual_publish_execution_runner_execution_approved_for_later_phase": bool(
            final_policy.get("actual_publish_execution_runner_execution_approved_for_later_phase", True)
        ),
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": bool(
            final_policy.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase", False)
        ),
        "actual_publish_execution_runner_credential_preflight_required": bool(
            final_policy.get("actual_publish_execution_runner_credential_preflight_required", True)
        ),
        "actual_publish_execution_runner_final_command_required": bool(
            final_policy.get("actual_publish_execution_runner_final_command_required", True)
        ),
        "actual_publish_execution_runner_separate_publish_execution_phase_required": bool(
            final_policy.get("actual_publish_execution_runner_separate_publish_execution_phase_required", True)
        ),
        "actual_publish_execution_runner_no_execution_implementation_validated": bool(
            final_policy.get("actual_publish_execution_runner_no_execution_implementation_validated", True)
        ),
        "runner_skeleton_static_safety_validated": bool(
            final_policy.get("runner_skeleton_static_safety_validated", True)
        ),
        "source_artifacts_unchanged": bool(final_policy.get("source_artifacts_unchanged", True)),
        "runner_skeleton_reexecuted_by_this_phase": bool(
            final_policy.get("runner_skeleton_reexecuted_by_this_phase", False)
        ),
        "actual_publish_execution_runner_reexecuted_by_this_phase": bool(
            final_policy.get("actual_publish_execution_runner_reexecuted_by_this_phase", False)
        ),
        "actual_publish_execution_runner_network_call_enabled": bool(
            final_policy.get("actual_publish_execution_runner_network_call_enabled", False)
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool(
            final_policy.get("actual_publish_execution_runner_credential_read_enabled", False)
        ),
        "actual_publish_execution_runner_publish_enabled": bool(
            final_policy.get("actual_publish_execution_runner_publish_enabled", False)
        ),
        "actual_publish_execution_runner_execution_enabled": bool(
            final_policy.get("actual_publish_execution_runner_execution_enabled", False)
        ),
        "actual_publish_execution_runner_executed": bool(final_policy.get("actual_publish_execution_runner_executed", False)),
        "manual_publish_executed": bool(final_policy.get("manual_publish_executed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(
            final_policy.get("actual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_runner_execution_allowed_by_this_phase": bool(
            final_policy.get("actual_runner_execution_allowed_by_this_phase", False)
        ),
        "manual_publish_allowed_by_this_phase": bool(final_policy.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(
            final_policy.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "wordpress_api_call_executed": bool_from(ls6ap_ready, "wordpress_api_call_executed"),
        "wordpress_get_executed": bool_from(ls6ap_ready, "wordpress_get_executed"),
        "wordpress_post_executed": bool_from(ls6ap_ready, "wordpress_post_executed"),
        "wordpress_put_executed": bool_from(ls6ap_ready, "wordpress_put_executed"),
        "wordpress_patch_executed": bool_from(ls6ap_ready, "wordpress_patch_executed"),
        "wordpress_delete_executed": bool_from(ls6ap_ready, "wordpress_delete_executed"),
        "wordpress_write_executed_by_this_phase": bool_from(ls6ap_ready, "wordpress_write_executed_by_this_phase"),
        "wordpress_publish_executed": bool_from(ls6ap_ready, "wordpress_publish_executed"),
        "publish_executed": bool_from(ls6ap_ready, "publish_executed"),
        "future_schedule_executed": bool_from(ls6ap_ready, "future_schedule_executed"),
        "delete_executed": bool_from(ls6ap_ready, "delete_executed"),
        "post119_update_executed": bool_from(ls6ap_ready, "post119_update_executed"),
        "credential_env_read_executed": bool_from(ls6ap_ready, "credential_env_read_executed"),
        "credential_value_output": bool_from(ls6ap_ready, "credential_value_output"),
        "credential_value_persisted": bool_from(ls6ap_ready, "credential_value_persisted"),
        "credential_secret_output": bool_from(ls6ap_ready, "credential_secret_output"),
        "secret_length_output": bool_from(ls6ap_ready, "secret_length_output"),
        "secret_hash_output": bool_from(ls6ap_ready, "secret_hash_output"),
        "authorization_header_output": bool_from(ls6ap_ready, "authorization_header_output"),
        "locked": locked,
        "rerun_allowed": bool_from(ls6ap_ready, "rerun_allowed"),
        "ls6oc1_rerun_executed": bool_from(ls6ap_ready, "ls6oc1_rerun_executed"),
        "requires_actual_publish_execution_runner_credential_preflight": bool(
            final_policy.get("requires_actual_publish_execution_runner_credential_preflight", True)
        ),
        "requires_actual_publish_execution_runner_final_command": bool(
            final_policy.get("requires_actual_publish_execution_runner_final_command", True)
        ),
        "requires_separate_publish_execution_phase": bool(
            final_policy.get("requires_separate_publish_execution_phase", True)
        ),
        "publish_execution_still_blocked": bool(final_policy.get("publish_execution_still_blocked", True)),
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock_payload = {
        "phase": "LS-6AQ",
        "document_type": "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_LOCK",
        "status": LOCKED_STATUS if locked else status,
        "locked": locked,
        "post_id": post_id,
        "target_post_status": str(ls6ap_ready.get("returned_post_status", "")),
        "actual_publish_execution_runner_final_boundary_ready": payload[
            "actual_publish_execution_runner_final_boundary_ready"
        ],
        "actual_publish_execution_runner_final_boundary_consumed": payload[
            "actual_publish_execution_runner_final_boundary_consumed"
        ],
        "actual_publish_execution_runner_execution_approval_gate_consumed": payload[
            "actual_publish_execution_runner_execution_approval_gate_consumed"
        ],
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": payload[
            "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase"
        ],
        "actual_publish_execution_runner_credential_preflight_required": payload[
            "actual_publish_execution_runner_credential_preflight_required"
        ],
        "actual_publish_execution_runner_final_command_required": payload[
            "actual_publish_execution_runner_final_command_required"
        ],
        "actual_publish_execution_runner_separate_publish_execution_phase_required": payload[
            "actual_publish_execution_runner_separate_publish_execution_phase_required"
        ],
        "actual_publish_execution_runner_network_call_enabled": payload[
            "actual_publish_execution_runner_network_call_enabled"
        ],
        "actual_publish_execution_runner_credential_read_enabled": payload[
            "actual_publish_execution_runner_credential_read_enabled"
        ],
        "actual_publish_execution_runner_publish_enabled": payload[
            "actual_publish_execution_runner_publish_enabled"
        ],
        "actual_publish_execution_runner_execution_enabled": payload[
            "actual_publish_execution_runner_execution_enabled"
        ],
        "actual_publish_execution_runner_executed": payload["actual_publish_execution_runner_executed"],
        "manual_publish_executed": payload["manual_publish_executed"],
        "wordpress_api_call_executed": payload["wordpress_api_call_executed"],
        "credential_env_read_executed": payload["credential_env_read_executed"],
        "publish_executed": payload["publish_executed"],
        "rerun_allowed": payload["rerun_allowed"],
        "ls6oc1_rerun_executed": payload["ls6oc1_rerun_executed"],
        "requires_next_phase": "LS-6AR",
        "requires_actual_publish_execution_runner_credential_preflight": payload[
            "requires_actual_publish_execution_runner_credential_preflight"
        ],
        "requires_actual_publish_execution_runner_final_command": payload[
            "requires_actual_publish_execution_runner_final_command"
        ],
        "requires_separate_publish_execution_phase": payload["requires_separate_publish_execution_phase"],
        "publish_execution_still_blocked": payload["publish_execution_still_blocked"],
    }

    write_json(Path(args.boundary_output), payload)
    write_json(Path(args.boundary_lock_output), lock_payload)
    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
