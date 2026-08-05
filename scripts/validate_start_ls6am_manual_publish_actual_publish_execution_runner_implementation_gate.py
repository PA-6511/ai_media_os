#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AM_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_NOT_READY"

TEMPLATE_DOCUMENT_TYPE = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_TEMPLATE"
READY_DOCUMENT_TYPE = "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE"
TEMPLATE_GATE_STATUS = "TEMPLATE_NOT_CONFIRMED"
READY_GATE_STATUS = "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_RECORDED_NO_PUBLISH_EXECUTION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate.template.json")
    parser.add_argument("--implementation-gate", default="exchange/human_review/start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate.json")
    parser.add_argument("--ls6al-ready-result", default="exchange/logs/start_ls6al_manual_publish_actual_publish_execution_runner_separated_phase_gate_ready_result.json")
    parser.add_argument("--ls6al-separated-phase-gate-result", default="exchange/human_review/start_ls6al_manual_publish_actual_publish_execution_runner_separated_phase_gate.json")
    parser.add_argument("--ls6ak-validation-result", default="exchange/logs/start_ls6ak_manual_publish_actual_publish_execution_runner_final_boundary_validation_result.json")
    parser.add_argument("--ls6ak-final-boundary-result", default="exchange/runtime/start_ls6ak_manual_publish_actual_publish_execution_runner_final_boundary_result.json")
    parser.add_argument("--ls6ak-final-boundary-lock", default="exchange/locks/start_ls6ak_manual_publish_actual_publish_execution_runner_final_boundary.lock.json")
    parser.add_argument("--ls6aj-ready-result", default="exchange/logs/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate_ready_result.json")
    parser.add_argument("--ls6aj-execute-now-result", default="exchange/human_review/start_ls6aj_manual_publish_actual_publish_execution_runner_execute_now_gate.json")
    parser.add_argument("--ls6ai-validation-result", default="exchange/logs/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_validation_result.json")
    parser.add_argument("--ls6ai-wordpress-current-draft-status-result", default="exchange/runtime/start_ls6ai_wordpress_current_draft_status_verification_result.json")
    parser.add_argument("--ls6ai-final-preflight-result", default="exchange/runtime/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight_result.json")
    parser.add_argument("--ls6ai-final-preflight-lock", default="exchange/locks/start_ls6ai_manual_publish_actual_publish_execution_runner_final_preflight.lock.json")
    parser.add_argument("--ls6ah-validation-result", default="exchange/logs/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary_validation_result.json")
    parser.add_argument("--ls6ah-boundary-result", default="exchange/runtime/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary_result.json")
    parser.add_argument("--ls6ah-boundary-lock", default="exchange/locks/start_ls6ah_manual_publish_actual_publish_execution_runner_boundary.lock.json")
    parser.add_argument("--ls6ag-ready-result", default="exchange/logs/start_ls6ag_manual_publish_actual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6ag-command-result", default="exchange/human_review/start_ls6ag_manual_publish_actual_publish_final_execution_command.json")
    parser.add_argument("--ls6af-validation-result", default="exchange/logs/start_ls6af_manual_publish_actual_publish_runner_final_gate_validation_result.json")
    parser.add_argument("--ls6af-runner-final-gate-result", default="exchange/runtime/start_ls6af_manual_publish_actual_publish_runner_final_gate_result.json")
    parser.add_argument("--ls6af-runner-final-gate-lock", default="exchange/locks/start_ls6af_manual_publish_actual_publish_runner_final_gate.lock.json")
    parser.add_argument("--ls6ae-validation-result", default="exchange/logs/start_ls6ae_manual_publish_actual_publish_final_preflight_validation_result.json")
    parser.add_argument("--ls6ae-final-preflight-result", default="exchange/runtime/start_ls6ae_manual_publish_actual_publish_final_preflight_result.json")
    parser.add_argument("--ls6ae-final-preflight-lock", default="exchange/locks/start_ls6ae_manual_publish_actual_publish_final_preflight.lock.json")
    parser.add_argument("--ls6ad-validation-result", default="exchange/logs/start_ls6ad_manual_publish_actual_publish_execution_boundary_validation_result.json")
    parser.add_argument("--ls6ad-boundary-result", default="exchange/runtime/start_ls6ad_manual_publish_actual_publish_execution_boundary_result.json")
    parser.add_argument("--ls6ad-boundary-lock", default="exchange/locks/start_ls6ad_manual_publish_actual_publish_execution_boundary.lock.json")
    parser.add_argument("--ls6ac-ready-result", default="exchange/logs/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation_ready_result.json")
    parser.add_argument("--ls6ac-confirmation-result", default="exchange/human_review/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation.json")
    parser.add_argument("--ls6ab-validation-result", default="exchange/logs/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_validation_result.json")
    parser.add_argument("--ls6ab-blocked-runner-result", default="exchange/runtime/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_blocked_result.json")
    parser.add_argument("--ls6ab-blocked-runner-lock", default="exchange/locks/start_ls6ab_manual_publish_separated_actual_publish_execution_runner.lock.json")
    parser.add_argument("--ls6aa-validation-result", default="exchange/logs/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_validation_result.json")
    parser.add_argument("--ls6aa-final-preflight-result", default="exchange/runtime/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--ls6aa-final-preflight-lock", default="exchange/locks/start_ls6aa_manual_publish_actual_publish_execution_final_preflight.lock.json")
    parser.add_argument("--ls6z-ready-result", default="exchange/logs/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_result.json")
    parser.add_argument("--ls6z-command-result", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.json")
    parser.add_argument("--ls6y-validation-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--ls6y-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6am_manual_publish_actual_publish_execution_runner_implementation_gate_ready_report.md")
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
        "# LS-6AM Manual Publish Actual Publish Execution Runner Implementation Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
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


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def resolve_from_policy(policy_path: Path, rel_path: str) -> Path:
    return policy_path.parent.parent / rel_path


def bool_from(source: dict[str, Any], key: str) -> bool:
    return bool(source.get(key, False))


def build_result(
    args: argparse.Namespace,
    ls6al_ready: dict[str, Any],
    ls6al_gate: dict[str, Any],
    active_doc: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    impl = safe_get(active_doc, "implementation_gate") or {}
    upstream = safe_get(active_doc, "upstream_consumption_state") or {}
    current = safe_get(active_doc, "current_phase_execution") or {}

    status = STATUS_TEMPLATE_READY if args.allow_template else STATUS_READY
    if errors:
        status = STATUS_NOT_READY

    return {
        "phase": "LS-6AM",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": ls6al_ready.get("post_id", 0),
        "post_link": ls6al_ready.get("post_link", ""),
        "payload_title": ls6al_ready.get("payload_title", ""),
        "payload_asin": ls6al_ready.get("payload_asin", ""),
        "returned_post_status": ls6al_ready.get("returned_post_status", ""),
        "ls6al_separated_phase_gate_validated": ls6al_ready.get("status") == "LS6AL_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PHASE_GATE_READY_NO_PUBLISH",
        "actual_publish_execution_runner_implementation_gate_recorded": active_doc.get("gate_status") == READY_GATE_STATUS,
        "gate_status": active_doc.get("gate_status", ""),
        "actual_publish_execution_runner_implementation_gate_label": impl.get("actual_publish_execution_runner_implementation_gate_label", ""),
        "actual_publish_execution_runner_implementation_gate_consumed": bool_from(impl, "actual_publish_execution_runner_implementation_gate_consumed"),
        "actual_publish_execution_runner_implementation_allowed_by_this_phase": bool_from(impl, "actual_publish_execution_runner_implementation_allowed_by_this_phase"),
        "actual_publish_execution_runner_implemented_by_this_phase": bool_from(impl, "actual_publish_execution_runner_implemented_by_this_phase"),
        "actual_publish_execution_runner_file_created_by_this_phase": bool_from(impl, "actual_publish_execution_runner_file_created_by_this_phase"),
        "separated_actual_publish_execution_runner_phase_gate_recorded": bool_from(impl, "separated_actual_publish_execution_runner_phase_gate_recorded"),
        "separated_actual_publish_execution_runner_phase_gate_consumed": bool_from(impl, "separated_actual_publish_execution_runner_phase_gate_consumed"),
        "actual_publish_execution_runner_final_boundary_ready": bool_from(impl, "actual_publish_execution_runner_final_boundary_ready"),
        "actual_publish_execution_runner_final_boundary_consumed": bool_from(impl, "actual_publish_execution_runner_final_boundary_consumed"),
        "actual_publish_execution_runner_execute_now_recorded": bool_from(impl, "actual_publish_execution_runner_execute_now_recorded"),
        "actual_publish_execution_runner_execute_now_label": ls6al_ready.get("actual_publish_execution_runner_execute_now_label", ""),
        "actual_publish_execution_runner_execute_now_consumed": bool_from(impl, "actual_publish_execution_runner_execute_now_consumed"),
        "actual_publish_execution_runner_final_preflight_ready": bool_from(impl, "actual_publish_execution_runner_final_preflight_ready"),
        "actual_publish_execution_runner_final_preflight_consumed": bool_from(impl, "actual_publish_execution_runner_final_preflight_consumed"),
        "actual_publish_execution_runner_boundary_ready": bool_from(impl, "actual_publish_execution_runner_boundary_ready"),
        "actual_publish_execution_runner_boundary_consumed": bool_from(impl, "actual_publish_execution_runner_boundary_consumed"),
        "actual_publish_final_execution_command_recorded": bool_from(impl, "actual_publish_final_execution_command_recorded"),
        "actual_publish_final_execution_command_label": ls6al_ready.get("actual_publish_final_execution_command_label", ""),
        "actual_publish_final_execution_command_consumed": bool_from(impl, "actual_publish_final_execution_command_consumed"),
        "actual_publish_runner_final_gate_ready": bool_from(impl, "actual_publish_runner_final_gate_ready"),
        "actual_publish_runner_final_gate_consumed": bool_from(impl, "actual_publish_runner_final_gate_consumed"),
        "actual_publish_final_preflight_ready": bool_from(impl, "actual_publish_final_preflight_ready"),
        "actual_publish_final_preflight_consumed": bool_from(impl, "actual_publish_final_preflight_consumed"),
        "actual_publish_execution_boundary_ready": bool_from(impl, "actual_publish_execution_boundary_ready"),
        "actual_publish_execution_boundary_consumed": bool_from(impl, "actual_publish_execution_boundary_consumed"),
        "actual_publish_execute_now_final_confirmation_label": ls6al_ready.get("actual_publish_execute_now_final_confirmation_label", ""),
        "actual_publish_execute_now_final_confirmation_consumed": bool_from(impl, "actual_publish_execute_now_final_confirmation_consumed"),
        "explicit_execute_now_for_actual_publish_required": bool_from(impl, "explicit_execute_now_for_actual_publish_required"),
        "explicit_execute_now_for_actual_publish_received": bool_from(impl, "explicit_execute_now_for_actual_publish_received"),
        "explicit_execute_now_for_actual_publish_consumed": bool_from(impl, "explicit_execute_now_for_actual_publish_consumed"),
        "actual_publish_execution_runner_ready": bool_from(impl, "actual_publish_execution_runner_ready"),
        "actual_publish_execution_runner_executed": bool_from(impl, "actual_publish_execution_runner_executed"),
        "actual_publish_execution_runner_blocked": bool_from(impl, "actual_publish_execution_runner_blocked"),
        "final_explicit_publish_execution_command_label": ls6al_ready.get("final_explicit_publish_execution_command_label", ""),
        "final_explicit_publish_execution_command_consumed": bool_from(upstream, "final_explicit_publish_execution_command_consumed"),
        "actual_publish_execution_final_preflight_ready": bool(ls6al_ready.get("actual_publish_execution_final_preflight_ready", False)),
        "actual_publish_execution_final_preflight_consumed": bool_from(upstream, "actual_publish_execution_final_preflight_consumed"),
        "actual_publish_runner_boundary_consumed": bool_from(upstream, "actual_publish_runner_boundary_consumed"),
        "actual_publish_execution_gate_consumed": bool_from(upstream, "actual_publish_execution_gate_consumed"),
        "final_execution_command_consumed": bool_from(upstream, "final_execution_command_consumed"),
        "approval_label_consumed": bool_from(upstream, "approval_label_consumed"),
        "execute_now_confirmation_consumed": bool_from(upstream, "execute_now_confirmation_consumed"),
        "actual_publish_execution_allowed_by_this_phase": bool_from(impl, "actual_publish_execution_allowed_by_this_phase"),
        "actual_runner_execution_allowed_by_this_phase": bool_from(impl, "actual_runner_execution_allowed_by_this_phase"),
        "manual_publish_allowed_by_this_phase": bool_from(impl, "manual_publish_allowed_by_this_phase"),
        "manual_publish_execution_allowed_by_this_phase": bool_from(impl, "manual_publish_execution_allowed_by_this_phase"),
        "manual_publish_executed": bool_from(impl, "manual_publish_executed"),
        "wordpress_api_call_executed": bool_from(current, "wordpress_api_call_executed"),
        "wordpress_get_executed": bool_from(current, "wordpress_get_executed"),
        "wordpress_post_executed": bool_from(current, "wordpress_post_executed"),
        "wordpress_put_executed": bool_from(current, "wordpress_put_executed"),
        "wordpress_patch_executed": bool_from(current, "wordpress_patch_executed"),
        "wordpress_delete_executed": bool_from(current, "wordpress_delete_executed"),
        "wordpress_write_executed_by_this_phase": bool_from(current, "wordpress_write_executed_by_this_phase"),
        "wordpress_draft_creation_executed_by_this_phase": bool_from(current, "wordpress_draft_creation_executed_by_this_phase"),
        "wordpress_existing_post_update_executed": bool_from(current, "wordpress_existing_post_update_executed"),
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
        "requires_actual_publish_execution_runner_implementation_phase": True,
        "requires_actual_publish_execution_runner_no_execution_implementation": True,
        "requires_separated_actual_publish_execution_runner_phase": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AN",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "actual_publish_execution_runner_implementation_allowed_by_this_phase": False,
            "requires_actual_publish_execution_runner_implementation_phase": True,
            "requires_actual_publish_execution_runner_no_execution_implementation": True,
            "requires_separated_actual_publish_execution_runner_phase": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy_path = Path(args.policy)
    policy = try_load_json(policy_path, errors)
    template = try_load_json(Path(args.template), errors)
    impl_gate_doc = try_load_json(Path(args.implementation_gate), errors) if not args.allow_template else {}

    ls6al_ready = try_load_json(Path(args.ls6al_ready_result), errors)
    ls6al_gate = try_load_json(Path(args.ls6al_separated_phase_gate_result), errors)
    ls6ak_validation = try_load_json(Path(args.ls6ak_validation_result), errors)
    ls6ak_final_boundary = try_load_json(Path(args.ls6ak_final_boundary_result), errors)
    ls6ak_lock = try_load_json(Path(args.ls6ak_final_boundary_lock), errors)
    ls6aj_ready = try_load_json(Path(args.ls6aj_ready_result), errors)
    ls6aj_execute = try_load_json(Path(args.ls6aj_execute_now_result), errors)
    ls6ai_validation = try_load_json(Path(args.ls6ai_validation_result), errors)
    ls6ai_wp = try_load_json(Path(args.ls6ai_wordpress_current_draft_status_result), errors)
    ls6ai_final = try_load_json(Path(args.ls6ai_final_preflight_result), errors)
    ls6ai_lock = try_load_json(Path(args.ls6ai_final_preflight_lock), errors)
    ls6ah_validation = try_load_json(Path(args.ls6ah_validation_result), errors)
    ls6ah_boundary = try_load_json(Path(args.ls6ah_boundary_result), errors)
    ls6ah_lock = try_load_json(Path(args.ls6ah_boundary_lock), errors)
    ls6ag_ready = try_load_json(Path(args.ls6ag_ready_result), errors)
    ls6ag_command = try_load_json(Path(args.ls6ag_command_result), errors)
    ls6af_validation = try_load_json(Path(args.ls6af_validation_result), errors)
    ls6af_runtime = try_load_json(Path(args.ls6af_runner_final_gate_result), errors)
    ls6af_lock = try_load_json(Path(args.ls6af_runner_final_gate_lock), errors)
    ls6ae_validation = try_load_json(Path(args.ls6ae_validation_result), errors)
    ls6ae_final = try_load_json(Path(args.ls6ae_final_preflight_result), errors)
    ls6ae_lock = try_load_json(Path(args.ls6ae_final_preflight_lock), errors)
    ls6ad_validation = try_load_json(Path(args.ls6ad_validation_result), errors)
    ls6ad_boundary = try_load_json(Path(args.ls6ad_boundary_result), errors)
    ls6ad_lock = try_load_json(Path(args.ls6ad_boundary_lock), errors)
    ls6ac_ready = try_load_json(Path(args.ls6ac_ready_result), errors)
    ls6ac_confirmation = try_load_json(Path(args.ls6ac_confirmation_result), errors)
    ls6ab_validation = try_load_json(Path(args.ls6ab_validation_result), errors)
    ls6ab_blocked = try_load_json(Path(args.ls6ab_blocked_runner_result), errors)
    ls6ab_lock = try_load_json(Path(args.ls6ab_blocked_runner_lock), errors)
    ls6aa_validation = try_load_json(Path(args.ls6aa_validation_result), errors)
    ls6aa_final = try_load_json(Path(args.ls6aa_final_preflight_result), errors)
    ls6aa_lock = try_load_json(Path(args.ls6aa_final_preflight_lock), errors)
    ls6z_ready = try_load_json(Path(args.ls6z_ready_result), errors)
    ls6z_command = try_load_json(Path(args.ls6z_command_result), errors)
    ls6y_validation = try_load_json(Path(args.ls6y_validation_result), errors)
    ls6y_lock = try_load_json(Path(args.ls6y_boundary_lock), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    ls6p_lock: dict[str, Any] = {}
    ls6p_rel = safe_get(policy, "required_previous_phase", "ls6p", "rerun_prevention_final_lock")
    if isinstance(ls6p_rel, str) and ls6p_rel:
        ls6p_lock = try_load_json(resolve_from_policy(policy_path, ls6p_rel), errors)

    req(policy.get("phase") == "LS-6AM", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)

    target = policy.get("target_post", {})
    req(target.get("post_id") == 183, "policy.target_post.post_id mismatch", errors)
    req(target.get("expected_current_status") == "draft", "policy.target_post.expected_current_status mismatch", errors)

    req(ls6al_ready.get("status") == "LS6AL_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PHASE_GATE_READY_NO_PUBLISH", "LS-6AL ready status mismatch", errors)
    req(ls6al_ready.get("gate_status") == "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AL gate status mismatch", errors)
    req(ls6al_ready.get("separated_actual_publish_execution_runner_phase_gate_label") == "SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_PHASE_GATE_ONLY", "LS-6AL gate label mismatch", errors)
    req(ls6al_ready.get("separated_actual_publish_execution_runner_phase_gate_consumed") is False, "LS-6AL gate consumed must be false", errors)
    req(ls6al_ready.get("requires_actual_publish_execution_runner_implementation") is True, "LS-6AL requires_actual_publish_execution_runner_implementation must be true", errors)
    req(ls6al_ready.get("publish_execution_still_blocked") is True, "LS-6AL publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6al_gate, "separated_phase_gate", "separated_actual_publish_execution_runner_phase_gate_consumed") is False, "LS-6AL separated gate consumed must be false", errors)

    req(ls6ak_validation.get("status") == "LS6AK_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AK validation status mismatch", errors)
    req(ls6ak_final_boundary.get("actual_publish_execution_runner_final_boundary_ready") is True, "LS-6AK final boundary ready must be true", errors)
    req(ls6ak_final_boundary.get("actual_publish_execution_runner_final_boundary_consumed") is False, "LS-6AK final boundary consumed must be false", errors)
    req(ls6ak_lock.get("actual_publish_execution_runner_final_boundary_consumed") is False, "LS-6AK lock consumed must be false", errors)

    req(ls6aj_ready.get("status") == "LS6AJ_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_GATE_READY_NO_PUBLISH", "LS-6AJ ready status mismatch", errors)
    req(ls6aj_execute.get("execute_now_status") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_EXECUTE_NOW_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AJ execute_now_status mismatch", errors)
    req(safe_get(ls6aj_execute, "actual_publish_execution_runner_execute_now_gate", "actual_publish_execution_runner_execute_now_label") == "EXECUTE_NOW_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "LS-6AJ execute-now label mismatch", errors)
    req(safe_get(ls6aj_execute, "actual_publish_execution_runner_execute_now_gate", "actual_publish_execution_runner_execute_now_consumed") is False, "LS-6AJ execute-now consumed must be false", errors)

    req(ls6ai_validation.get("status") == "LS6AI_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AI validation status mismatch", errors)
    req((ls6ai_wp.get("draft_verified") is True) or (ls6ai_wp.get("status") == "WORDPRESS_CURRENT_DRAFT_STATUS_VERIFIED"), "LS-6AI draft verification mismatch", errors)
    req(ls6ai_wp.get("returned_post_status") == "draft", "LS-6AI returned_post_status mismatch", errors)
    req(ls6ai_final.get("actual_publish_execution_runner_final_preflight_ready") is True, "LS-6AI final preflight ready must be true", errors)
    req(ls6ai_final.get("actual_publish_execution_runner_final_preflight_consumed") is False, "LS-6AI final preflight consumed must be false", errors)
    req(ls6ai_lock.get("actual_publish_execution_runner_final_preflight_consumed") is False, "LS-6AI lock consumed must be false", errors)

    req(ls6ah_validation.get("status") == "LS6AH_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_RUNNER_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AH validation status mismatch", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_ready") is True, "LS-6AH boundary ready must be true", errors)
    req(ls6ah_boundary.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH boundary consumed must be false", errors)
    req(ls6ah_lock.get("actual_publish_execution_runner_boundary_consumed") is False, "LS-6AH lock consumed must be false", errors)

    req(ls6ag_ready.get("status") == "LS6AG_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6AG ready status mismatch", errors)
    req(ls6ag_command.get("command_status") == "ACTUAL_PUBLISH_FINAL_EXECUTION_COMMAND_RECORDED_NO_PUBLISH_EXECUTION", "LS-6AG command status mismatch", errors)
    req(safe_get(ls6ag_command, "actual_publish_final_execution_command", "actual_publish_final_execution_command_label") == "FINAL_COMMAND_FOR_ACTUAL_PUBLISH_EXECUTION_RUNNER_GATE_ONLY", "LS-6AG final command label mismatch", errors)
    req(safe_get(ls6ag_command, "actual_publish_final_execution_command", "actual_publish_final_execution_command_consumed") is False, "LS-6AG final command consumed must be false", errors)

    req(ls6af_validation.get("status") == "LS6AF_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_FINAL_GATE_VALIDATED_NO_PUBLISH", "LS-6AF validation status mismatch", errors)
    req(ls6af_runtime.get("actual_publish_runner_final_gate_ready") is True, "LS-6AF runner final gate ready must be true", errors)
    req(ls6af_runtime.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF runner final gate consumed must be false", errors)
    req(ls6af_lock.get("actual_publish_runner_final_gate_consumed") is False, "LS-6AF lock consumed must be false", errors)

    req(ls6ae_validation.get("status") == "LS6AE_MANUAL_PUBLISH_ACTUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AE validation status mismatch", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_ready") is True, "LS-6AE final preflight ready must be true", errors)
    req(ls6ae_final.get("actual_publish_final_preflight_consumed") is False, "LS-6AE final preflight consumed must be false", errors)
    req(ls6ae_lock.get("actual_publish_final_preflight_consumed") is False, "LS-6AE lock consumed must be false", errors)

    req(ls6ad_validation.get("status") == "LS6AD_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6AD validation status mismatch", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_ready") is True, "LS-6AD boundary ready must be true", errors)
    req(ls6ad_boundary.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD boundary consumed must be false", errors)
    req(ls6ad_lock.get("actual_publish_execution_boundary_consumed") is False, "LS-6AD lock consumed must be false", errors)

    req(ls6ac_ready.get("status") == "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH", "LS-6AC ready status mismatch", errors)
    req(ls6ac_ready.get("actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC ready consumed must be false", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "actual_publish_execute_now_final_confirmation_consumed") is False, "LS-6AC confirmation consumed must be false", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_required") is True, "LS-6AC explicit required must be true", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_received") is True, "LS-6AC explicit received must be true", errors)
    req(safe_get(ls6ac_confirmation, "actual_publish_execute_now_final_confirmation", "explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AC explicit consumed must be false", errors)

    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_ready") is True, "LS-6AB runner ready must be true", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner executed must be false", errors)
    req(ls6ab_blocked.get("actual_publish_execution_runner_blocked") is True, "LS-6AB runner blocked must be true", errors)
    req(ls6ab_lock.get("actual_publish_execution_runner_executed") is False, "LS-6AB lock runner executed must be false", errors)

    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_final.get("actual_publish_execution_final_preflight_ready") is True, "LS-6AA final preflight ready must be true", errors)
    req(ls6aa_final.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA final preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock consumed must be false", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z ready status mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z consumed must be false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("status") == "LS6Y_MANUAL_PUBLISH_ACTUAL_PUBLISH_RUNNER_EXECUTION_BOUNDARY_VALIDATED_NO_PUBLISH", "LS-6Y validation status mismatch", errors)
    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    req(ls6x_ready.get("status") == "LS6X_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_GATE_READY_NO_PUBLISH", "LS-6X ready status mismatch", errors)
    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)

    req(ls6v_ready.get("status") == "LS6V_MANUAL_PUBLISH_FINAL_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6V ready status mismatch", errors)
    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V consumed must be false", errors)

    req(ls6t_ready.get("status") == "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH", "LS-6T ready status mismatch", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T consumed must be false", errors)

    req(ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH", "LS-6R ready status mismatch", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R consumed must be false", errors)

    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)
    if ls6p_lock:
        req(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)

    active_doc = template if args.allow_template else impl_gate_doc
    impl = safe_get(active_doc, "implementation_gate") or {}
    upstream = safe_get(active_doc, "upstream_consumption_state") or {}
    current = safe_get(active_doc, "current_phase_execution") or {}
    active_target = safe_get(active_doc, "target_post") or {}

    req(active_doc.get("phase") == "LS-6AM", "phase mismatch", errors)
    req(active_target.get("post_id") == target.get("post_id"), "post_id mismatch", errors)
    req(active_target.get("expected_current_status") == "draft", "expected_current_status must be draft", errors)

    if args.allow_template:
        req(active_doc.get("document_type") == TEMPLATE_DOCUMENT_TYPE, "template document_type mismatch", errors)
        req(active_doc.get("gate_status") == TEMPLATE_GATE_STATUS, "template gate_status mismatch", errors)
    else:
        req(active_doc.get("document_type") == READY_DOCUMENT_TYPE, "implementation gate document_type mismatch", errors)
        req(active_doc.get("gate_status") == READY_GATE_STATUS, "gate_status mismatch", errors)
        req(impl.get("actual_publish_execution_runner_implementation_gate_label") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_IMPLEMENTATION_GATE_ONLY", "wrong implementation gate label", errors)
        req(impl.get("requires_next_phase") == "LS-6AN", "requires_next_phase mismatch", errors)

    req(impl.get("actual_publish_execution_runner_implementation_gate_consumed") is False, "actual_publish_execution_runner_implementation_gate_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_implementation_allowed_by_this_phase") is False, "actual_publish_execution_runner_implementation_allowed_by_this_phase must be false", errors)
    req(impl.get("actual_publish_execution_runner_implemented_by_this_phase") is False, "actual_publish_execution_runner_implemented_by_this_phase must be false", errors)
    req(impl.get("actual_publish_execution_runner_file_created_by_this_phase") is False, "actual_publish_execution_runner_file_created_by_this_phase must be false", errors)
    req(impl.get("separated_actual_publish_execution_runner_phase_gate_recorded") is True, "separated_actual_publish_execution_runner_phase_gate_recorded must be true", errors)
    req(impl.get("separated_actual_publish_execution_runner_phase_gate_consumed") is False, "separated_actual_publish_execution_runner_phase_gate_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_final_boundary_ready") is True, "actual_publish_execution_runner_final_boundary_ready must be true", errors)
    req(impl.get("actual_publish_execution_runner_final_boundary_consumed") is False, "actual_publish_execution_runner_final_boundary_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_execute_now_recorded") is True, "actual_publish_execution_runner_execute_now_recorded must be true", errors)
    req(impl.get("actual_publish_execution_runner_execute_now_consumed") is False, "actual_publish_execution_runner_execute_now_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_final_preflight_ready") is True, "actual_publish_execution_runner_final_preflight_ready must be true", errors)
    req(impl.get("actual_publish_execution_runner_final_preflight_consumed") is False, "actual_publish_execution_runner_final_preflight_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_boundary_ready") is True, "actual_publish_execution_runner_boundary_ready must be true", errors)
    req(impl.get("actual_publish_execution_runner_boundary_consumed") is False, "actual_publish_execution_runner_boundary_consumed must be false", errors)
    req(impl.get("actual_publish_final_execution_command_recorded") is True, "actual_publish_final_execution_command_recorded must be true", errors)
    req(impl.get("actual_publish_final_execution_command_consumed") is False, "actual_publish_final_execution_command_consumed must be false", errors)
    req(impl.get("actual_publish_runner_final_gate_ready") is True, "actual_publish_runner_final_gate_ready must be true", errors)
    req(impl.get("actual_publish_runner_final_gate_consumed") is False, "actual_publish_runner_final_gate_consumed must be false", errors)
    req(impl.get("actual_publish_final_preflight_ready") is True, "actual_publish_final_preflight_ready must be true", errors)
    req(impl.get("actual_publish_final_preflight_consumed") is False, "actual_publish_final_preflight_consumed must be false", errors)
    req(impl.get("actual_publish_execution_boundary_ready") is True, "actual_publish_execution_boundary_ready must be true", errors)
    req(impl.get("actual_publish_execution_boundary_consumed") is False, "actual_publish_execution_boundary_consumed must be false", errors)
    req(impl.get("actual_publish_execute_now_final_confirmation_consumed") is False, "actual_publish_execute_now_final_confirmation_consumed must be false", errors)
    req(impl.get("explicit_execute_now_for_actual_publish_required") is True, "explicit_execute_now_for_actual_publish_required must be true", errors)
    req(impl.get("explicit_execute_now_for_actual_publish_received") is True, "explicit_execute_now_for_actual_publish_received must be true", errors)
    req(impl.get("explicit_execute_now_for_actual_publish_consumed") is False, "explicit_execute_now_for_actual_publish_consumed must be false", errors)
    req(impl.get("actual_publish_execution_runner_ready") is True, "actual_publish_execution_runner_ready must be true", errors)
    req(impl.get("actual_publish_execution_runner_executed") is False, "actual_publish_execution_runner_executed must be false", errors)
    req(impl.get("actual_publish_execution_runner_blocked") is True, "actual_publish_execution_runner_blocked must be true", errors)
    req(impl.get("actual_publish_execution_allowed_by_this_phase") is False, "actual_publish_execution_allowed_by_this_phase must be false", errors)
    req(impl.get("actual_runner_execution_allowed_by_this_phase") is False, "actual_runner_execution_allowed_by_this_phase must be false", errors)
    req(impl.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    req(impl.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    req(impl.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)

    req(upstream.get("final_explicit_publish_execution_command_consumed") is False, "final_explicit_publish_execution_command_consumed must be false", errors)
    req(upstream.get("actual_publish_execution_final_preflight_consumed") is False, "actual_publish_execution_final_preflight_consumed must be false", errors)
    req(upstream.get("actual_publish_runner_boundary_consumed") is False, "actual_publish_runner_boundary_consumed must be false", errors)
    req(upstream.get("actual_publish_execution_gate_consumed") is False, "actual_publish_execution_gate_consumed must be false", errors)
    req(upstream.get("final_execution_command_consumed") is False, "final_execution_command_consumed must be false", errors)
    req(upstream.get("approval_label_consumed") is False, "approval_label_consumed must be false", errors)
    req(upstream.get("execute_now_confirmation_consumed") is False, "execute_now_confirmation_consumed must be false", errors)

    for key in [
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
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]:
        req(current.get(key) is False, f"current_phase_execution.{key} must be false", errors)

    result = build_result(args, ls6al_ready, ls6al_gate, active_doc, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
