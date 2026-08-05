#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AP_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_NOT_READY"

TEMPLATE_DOCUMENT_TYPE = "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_TEMPLATE"
READY_DOCUMENT_TYPE = "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE"
TEMPLATE_GATE_STATUS = "TEMPLATE_NOT_CONFIRMED"
READY_GATE_STATUS = "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTION_APPROVAL_GATE_RECORDED_NO_PUBLISH_EXECUTION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6ap_actual_publish_execution_runner_execution_approval_gate_policy.json",
    )
    parser.add_argument(
        "--template",
        default="exchange/human_review/start_ls6ap_actual_publish_execution_runner_execution_approval_gate.template.json",
    )
    parser.add_argument(
        "--approval-gate",
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
        default="exchange/logs/start_ls6ap_actual_publish_execution_runner_execution_approval_gate_ready_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6ap_actual_publish_execution_runner_execution_approval_gate_ready_report.md",
    )
    parser.add_argument("--allow-template", action="store_true")
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
        "# LS-6AP Actual Publish Execution Runner Execution Approval Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- phase: {result['phase']}",
        f"- status: {result['status']}",
        f"- gate_status: {result['gate_status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6ao_validation_validated: {result['ls6ao_validation_validated']}",
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


def bool_from(source: dict[str, Any], key: str) -> bool:
    return bool(source.get(key, False))


def make_next_phase(policy: dict[str, Any]) -> dict[str, Any]:
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
        "requires_actual_publish_execution_runner_final_boundary": bool(
            next_phase.get("requires_actual_publish_execution_runner_final_boundary", False)
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


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    template = try_load_json(Path(args.template), errors)
    approval_gate = try_load_json(Path(args.approval_gate), errors)
    ls6ao_validation_result = try_load_json(Path(args.ls6ao_validation_result), errors)
    ls6ao_validation_lock = try_load_json(Path(args.ls6ao_validation_lock), errors)
    ls6ao_validation_log = try_load_json(Path(args.ls6ao_validation_log), errors)

    req(policy.get("phase") == "LS-6AP", "policy.phase mismatch", errors)
    req(
        policy.get("execution_mode") == "EXECUTION_APPROVAL_GATE_ONLY_NO_PUBLISH",
        "policy.execution_mode mismatch",
        errors,
    )

    target = policy.get("target_post", {})
    required_prev = policy.get("required_previous_phase", {}).get("ls6ao", {})
    approval_policy = policy.get("approval_gate_policy", {})

    expected_post_id = int(target.get("post_id", 0))
    expected_post_status = str(target.get("expected_current_status", ""))

    req(int(required_prev.get("required_post_id", 0)) == expected_post_id, "required_post_id mismatch", errors)
    req(
        str(required_prev.get("required_returned_post_status", "")) == expected_post_status,
        "required_returned_post_status mismatch",
        errors,
    )

    req(int(ls6ao_validation_result.get("post_id", 0)) == expected_post_id, "post_id mismatch", errors)
    req(
        str(ls6ao_validation_result.get("returned_post_status", "")) == expected_post_status,
        "returned_post_status mismatch",
        errors,
    )

    req(
        str(ls6ao_validation_result.get("status", ""))
        == str(required_prev.get("required_validation_status", "")),
        "ls6ao validation status mismatch",
        errors,
    )
    req(
        str(ls6ao_validation_log.get("status", ""))
        == str(required_prev.get("required_validation_status", "")),
        "ls6ao validation log status mismatch",
        errors,
    )

    req(
        bool(ls6ao_validation_result.get("ls6an_fix_a_status_normalization_validated", False))
        is bool(required_prev.get("required_ls6an_fix_a_status_normalization_validated", True)),
        "ls6an_fix_a_status_normalization_validated mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("ls6an_no_execution_implementation_validated", False))
        is bool(required_prev.get("required_ls6an_no_execution_implementation_validated", True)),
        "ls6an_no_execution_implementation_validated mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("runner_skeleton_static_safety_validated", False))
        is bool(required_prev.get("required_runner_skeleton_static_safety_validated", True)),
        "runner_skeleton_static_safety_validated mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("source_artifacts_unchanged", False))
        is bool(required_prev.get("required_source_artifacts_unchanged", True)),
        "source_artifacts_unchanged mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("runner_skeleton_reexecuted_by_this_phase", False))
        is bool(required_prev.get("required_runner_skeleton_reexecuted_by_this_phase", False)),
        "runner_skeleton_reexecuted_by_this_phase mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_reexecuted_by_this_phase", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_reexecuted_by_this_phase", False)),
        "actual_publish_execution_runner_reexecuted_by_this_phase mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_network_call_enabled", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_network_call_enabled", False)),
        "actual_publish_execution_runner_network_call_enabled mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_credential_read_enabled", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_credential_read_enabled", False)),
        "actual_publish_execution_runner_credential_read_enabled mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_publish_enabled", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_publish_enabled", False)),
        "actual_publish_execution_runner_publish_enabled mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_execution_enabled", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_execution_enabled", False)),
        "actual_publish_execution_runner_execution_enabled mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("actual_publish_execution_runner_executed", False))
        is bool(required_prev.get("required_actual_publish_execution_runner_executed", False)),
        "actual_publish_execution_runner_executed mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("manual_publish_executed", False))
        is bool(required_prev.get("required_manual_publish_executed", False)),
        "manual_publish_executed mismatch",
        errors,
    )
    req(
        bool(ls6ao_validation_result.get("publish_execution_still_blocked", False))
        is bool(required_prev.get("required_publish_execution_still_blocked", True)),
        "publish_execution_still_blocked mismatch",
        errors,
    )

    req(
        int(ls6ao_validation_lock.get("post_id", 0)) == expected_post_id,
        "ls6ao validation lock post_id mismatch",
        errors,
    )

    active_doc = template if args.allow_template else approval_gate
    approval = active_doc.get("approval_gate", {})
    current = active_doc.get("current_phase_execution", {})

    required_doc_type = TEMPLATE_DOCUMENT_TYPE if args.allow_template else READY_DOCUMENT_TYPE
    required_gate_status = TEMPLATE_GATE_STATUS if args.allow_template else READY_GATE_STATUS

    req(str(active_doc.get("document_type", "")) == required_doc_type, "document_type mismatch", errors)
    req(str(active_doc.get("gate_status", "")) == required_gate_status, "gate_status mismatch", errors)

    active_target = active_doc.get("target_post", {})
    req(int(active_target.get("post_id", 0)) == expected_post_id, "target_post.post_id mismatch", errors)
    req(
        str(active_target.get("expected_current_status", "")) == expected_post_status,
        "target_post.expected_current_status mismatch",
        errors,
    )

    required_label = str(
        approval.get(
            "required_actual_publish_execution_runner_execution_approval_gate_label",
            approval_policy.get("actual_publish_execution_runner_execution_approval_gate_label", ""),
        )
    )
    actual_label = str(approval.get("actual_publish_execution_runner_execution_approval_gate_label", ""))

    req(required_label == str(approval_policy.get("actual_publish_execution_runner_execution_approval_gate_label", "")), "required label mismatch", errors)
    if args.allow_template:
        req(actual_label in {"", required_label}, "template label mismatch", errors)
    else:
        req(actual_label == required_label, "approval gate label mismatch", errors)

    req(
        bool_from(approval, "actual_publish_execution_runner_execution_approval_gate_consumed") is False,
        "approval gate consumed must be false",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_approval_allowed_by_this_phase") is False,
        "execution approval allowed by this phase must be false",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_approved_for_later_phase") is True,
        "approved for later phase must be true",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_requires_later_final_boundary") is True,
        "requires later final boundary must be true",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_requires_later_credential_preflight") is True,
        "requires later credential preflight must be true",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_requires_later_final_command") is True,
        "requires later final command must be true",
        errors,
    )
    req(
        bool_from(approval, "actual_publish_execution_runner_execution_requires_separate_publish_execution_phase") is True,
        "requires separate publish execution phase must be true",
        errors,
    )

    req(bool_from(approval, "actual_publish_execution_runner_no_execution_implementation_validated") is True, "no-execution implementation validated must be true", errors)
    req(bool_from(approval, "ls6ao_validation_validated") is True, "ls6ao_validation_validated must be true", errors)
    req(bool_from(approval, "runner_skeleton_static_safety_validated") is True, "runner_skeleton_static_safety_validated must be true", errors)
    req(bool_from(approval, "source_artifacts_unchanged") is True, "source_artifacts_unchanged must be true", errors)

    must_false = policy.get("must_remain_false_flags", {})
    for key, expected in must_false.items():
        expected_bool = bool(expected)
        if key in current:
            observed = bool(current.get(key, False))
        elif key in approval:
            observed = bool(approval.get(key, False))
        elif key in ls6ao_validation_result:
            observed = bool(ls6ao_validation_result.get(key, False))
        elif key in ls6ao_validation_lock:
            observed = bool(ls6ao_validation_lock.get(key, False))
        else:
            observed = False
        req(observed is expected_bool, f"{key} mismatch", errors)

    ls6ao_validation_validated = (
        str(ls6ao_validation_result.get("status", ""))
        == str(required_prev.get("required_validation_status", ""))
    )

    gate_recorded = str(active_doc.get("gate_status", "")) == READY_GATE_STATUS

    status = STATUS_TEMPLATE_READY if args.allow_template else STATUS_READY
    if errors:
        status = STATUS_NOT_READY

    next_phase = make_next_phase(policy)

    payload = {
        "phase": "LS-6AP",
        "status": status,
        "execution_mode": "EXECUTION_APPROVAL_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": expected_post_id,
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "returned_post_status": str(ls6ao_validation_result.get("returned_post_status", "")),
        "ls6ao_validation_validated": ls6ao_validation_validated,
        "actual_publish_execution_runner_execution_approval_gate_recorded": gate_recorded,
        "gate_status": str(active_doc.get("gate_status", "")),
        "actual_publish_execution_runner_execution_approval_gate_label": actual_label,
        "actual_publish_execution_runner_execution_approval_gate_consumed": bool_from(
            approval, "actual_publish_execution_runner_execution_approval_gate_consumed"
        ),
        "actual_publish_execution_runner_execution_approval_allowed_by_this_phase": bool_from(
            approval, "actual_publish_execution_runner_execution_approval_allowed_by_this_phase"
        ),
        "actual_publish_execution_runner_execution_approved_for_later_phase": bool_from(
            approval, "actual_publish_execution_runner_execution_approved_for_later_phase"
        ),
        "actual_publish_execution_runner_execution_requires_later_final_boundary": bool_from(
            approval, "actual_publish_execution_runner_execution_requires_later_final_boundary"
        ),
        "actual_publish_execution_runner_execution_requires_later_credential_preflight": bool_from(
            approval, "actual_publish_execution_runner_execution_requires_later_credential_preflight"
        ),
        "actual_publish_execution_runner_execution_requires_later_final_command": bool_from(
            approval, "actual_publish_execution_runner_execution_requires_later_final_command"
        ),
        "actual_publish_execution_runner_execution_requires_separate_publish_execution_phase": bool_from(
            approval, "actual_publish_execution_runner_execution_requires_separate_publish_execution_phase"
        ),
        "actual_publish_execution_runner_no_execution_implementation_validated": bool_from(
            approval, "actual_publish_execution_runner_no_execution_implementation_validated"
        ),
        "runner_skeleton_static_safety_validated": bool_from(approval, "runner_skeleton_static_safety_validated"),
        "source_artifacts_unchanged": bool_from(approval, "source_artifacts_unchanged"),
        "runner_skeleton_reexecuted_by_this_phase": bool_from(approval, "runner_skeleton_reexecuted_by_this_phase"),
        "actual_publish_execution_runner_reexecuted_by_this_phase": bool_from(
            approval, "actual_publish_execution_runner_reexecuted_by_this_phase"
        ),
        "actual_publish_execution_runner_network_call_enabled": bool_from(
            approval, "actual_publish_execution_runner_network_call_enabled"
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool_from(
            approval, "actual_publish_execution_runner_credential_read_enabled"
        ),
        "actual_publish_execution_runner_publish_enabled": bool_from(
            approval, "actual_publish_execution_runner_publish_enabled"
        ),
        "actual_publish_execution_runner_execution_enabled": bool_from(
            approval, "actual_publish_execution_runner_execution_enabled"
        ),
        "actual_publish_execution_runner_executed": bool_from(approval, "actual_publish_execution_runner_executed"),
        "manual_publish_executed": bool_from(approval, "manual_publish_executed"),
        "actual_publish_execution_allowed_by_this_phase": bool_from(
            approval, "actual_publish_execution_allowed_by_this_phase"
        ),
        "actual_runner_execution_allowed_by_this_phase": bool_from(
            approval, "actual_runner_execution_allowed_by_this_phase"
        ),
        "manual_publish_allowed_by_this_phase": bool_from(approval, "manual_publish_allowed_by_this_phase"),
        "manual_publish_execution_allowed_by_this_phase": bool_from(
            approval, "manual_publish_execution_allowed_by_this_phase"
        ),
        "wordpress_api_call_executed": bool_from(current, "wordpress_api_call_executed"),
        "wordpress_get_executed": bool_from(current, "wordpress_get_executed"),
        "wordpress_post_executed": bool_from(current, "wordpress_post_executed"),
        "wordpress_put_executed": bool_from(current, "wordpress_put_executed"),
        "wordpress_patch_executed": bool_from(current, "wordpress_patch_executed"),
        "wordpress_delete_executed": bool_from(current, "wordpress_delete_executed"),
        "wordpress_write_executed_by_this_phase": bool_from(current, "wordpress_write_executed_by_this_phase"),
        "wordpress_publish_executed": bool_from(current, "wordpress_publish_executed"),
        "publish_executed": bool_from(current, "publish_executed"),
        "future_schedule_executed": bool_from(current, "future_schedule_executed"),
        "delete_executed": bool_from(current, "delete_executed"),
        "post119_update_executed": bool_from(current, "post119_update_executed"),
        "credential_env_read_executed": bool_from(current, "credential_env_read_executed"),
        "credential_value_output": bool_from(current, "credential_value_output"),
        "credential_value_persisted": bool_from(current, "credential_value_persisted"),
        "credential_secret_output": bool_from(current, "credential_secret_output"),
        "secret_length_output": bool_from(current, "secret_length_output"),
        "secret_hash_output": bool_from(current, "secret_hash_output"),
        "authorization_header_output": bool_from(current, "authorization_header_output"),
        "rerun_allowed": bool_from(current, "rerun_allowed"),
        "ls6oc1_rerun_executed": bool_from(current, "ls6oc1_rerun_executed"),
        "requires_actual_publish_execution_runner_final_boundary": bool(
            approval_policy.get("requires_actual_publish_execution_runner_final_boundary", False)
        ),
        "requires_actual_publish_execution_runner_credential_preflight": bool(
            approval_policy.get("requires_actual_publish_execution_runner_credential_preflight", False)
        ),
        "requires_actual_publish_execution_runner_final_command": bool(
            approval_policy.get("requires_actual_publish_execution_runner_final_command", False)
        ),
        "requires_separate_publish_execution_phase": bool(
            approval_policy.get("requires_separate_publish_execution_phase", False)
        ),
        "publish_execution_still_blocked": bool(approval_policy.get("publish_execution_still_blocked", False)),
        "next_phase": next_phase,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
