#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_READY = "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION"
STATUS_NOT_READY = "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def read_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing required file: {label}: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        errors.append(f"failed to parse json: {label}: {path}: {exc}")
        return {}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6O-C-0 Final Execute-Now Confirmation Ready Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- phase: {result['phase']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- final_execute_now_confirmation_ready: {result['final_execute_now_confirmation_ready']}",
        f"- final_execute_now_granted: {result['final_execute_now_granted']}",
        f"- final_execute_now_consumed: {result['final_execute_now_consumed']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- ls6oa_actual_go_ready: {result['ls6oa_actual_go_ready']}",
        f"- ls6ob_runner_final_preflight_passed: {result['ls6ob_runner_final_preflight_passed']}",
        f"- ls6oc1_missing_final_execute_now_stop_checked: {result['ls6oc1_missing_final_execute_now_stop_checked']}",
        f"- one_shot_actual_execution_lock_active: {result['one_shot_actual_execution_lock_active']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- credential_presence_check_validated: {result['credential_presence_check_validated']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6oc0_final_execute_now_confirmation_policy.json")
    parser.add_argument("--confirmation", default="exchange/human_review/start_ls6oc0_final_execute_now_confirmation.json")
    parser.add_argument("--ls6oa-ready-result", default="exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_ready_result.json")
    parser.add_argument("--ls6oa-go", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json")
    parser.add_argument("--ls6ob-preflight-result", default="exchange/runtime/start_ls6ob_actual_execution_runner_final_preflight_result.json")
    parser.add_argument("--ls6ob-run-result", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_result.json")
    parser.add_argument("--ls6ob-validation-result", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_validation_result.json")
    parser.add_argument("--ls6oc1-not-ready-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_not_ready_result.json")
    parser.add_argument("--one-shot-lock", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6oc0_final_execute_now_confirmation_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6oc0_final_execute_now_confirmation_ready_report.md")
    return parser.parse_args()


def build_result(
    status: str,
    policy: dict[str, Any],
    confirmation: dict[str, Any],
    ls6oa_ready: dict[str, Any],
    ls6oa_go: dict[str, Any],
    ls6ob_preflight: dict[str, Any],
    ls6ob_run: dict[str, Any],
    ls6ob_validation: dict[str, Any],
    ls6oc1_not_ready: dict[str, Any],
    one_shot_lock: dict[str, Any],
    runtime_freeze_state: dict[str, Any],
    credential_presence: dict[str, Any],
    ls6c_payload: dict[str, Any],
    ls6b_lock: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    target_payload = policy.get("target_payload", {})
    decision = confirmation.get("decision", {})
    current_phase_execution = confirmation.get("current_phase_execution", {})

    payloads = ls6c_payload.get("payloads", [])
    payload0 = payloads[0] if isinstance(payloads, list) and payloads else {}

    ls6oc1_runner = Path("scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py")
    ls6oc1_guarded_runner_exists = ls6oc1_runner.exists()

    return {
        "phase": "LS-6O-C-0",
        "status": status,
        "execution_mode": "FINAL_EXECUTE_NOW_CONFIRMATION_GATE_ONLY",
        "production_status": "NO_GO",
        "final_execute_now_confirmation_ready": status == STATUS_READY,
        "final_execute_now_granted": bool(decision.get("final_execute_now_granted")),
        "final_execute_now_consumed": bool(decision.get("final_execute_now_consumed")),
        "confirmation_label": confirmation.get("confirmation_label", ""),
        "confirmation_status": confirmation.get("confirmation_status", ""),
        "payload_ready": bool(ls6c_payload.get("payload_ready")),
        "payload_title": payload0.get("title", ""),
        "payload_asin": payload0.get("asin", target_payload.get("asin", "")),
        "payload_post_status": payload0.get("post_status", ""),
        "max_items": int(ls6c_payload.get("max_items", 0) or 0),
        "ls6oa_actual_go_ready": ls6oa_ready.get("status") == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION",
        "actual_wordpress_go_consumed": bool(ls6oa_ready.get("actual_wordpress_go_consumed")),
        "ls6ob_runner_final_preflight_passed": bool(ls6ob_run.get("runner_final_preflight_passed")) and bool(ls6ob_preflight.get("runner_final_preflight_passed")),
        "ls6oc1_guarded_runner_exists": ls6oc1_guarded_runner_exists,
        "ls6oc1_missing_final_execute_now_stop_checked": ls6oc1_not_ready.get("status") == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_FINAL_EXECUTE_NOW",
        "one_shot_actual_execution_lock_active": bool(one_shot_lock.get("one_shot_actual_execution_lock_active")),
        "one_shot_actual_execution_lock_consumed": bool(one_shot_lock.get("one_shot_actual_execution_lock_consumed")),
        "runtime_freeze_active": bool(runtime_freeze_state.get("runtime_freeze_active")),
        "runtime_freeze_restored": bool(runtime_freeze_state.get("runtime_freeze_restored")),
        "credential_presence_check_validated": bool(credential_presence.get("required_keys_present")) and bool(credential_presence.get("required_keys_non_empty")),
        "actual_execution_allowed": bool(decision.get("actual_execution_allowed_by_this_phase")),
        "runner_execution_allowed_by_this_phase": bool(decision.get("runner_execution_allowed_by_this_phase")),
        "wordpress_api_call_allowed_by_this_phase": bool(decision.get("wordpress_api_call_allowed_by_this_phase")),
        "wordpress_write_allowed_by_this_phase": bool(decision.get("wordpress_write_allowed_by_this_phase")),
        "wordpress_draft_creation_allowed_by_this_phase": bool(decision.get("wordpress_draft_creation_allowed_by_this_phase")),
        "credential_env_read_allowed_by_this_phase": bool(decision.get("credential_env_read_allowed_by_this_phase")),
        "credential_env_read_executed": bool(current_phase_execution.get("credential_env_read_executed")),
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "wordpress_api_call_executed": bool(current_phase_execution.get("wordpress_api_call_executed")),
        "wordpress_write_executed": bool(current_phase_execution.get("wordpress_write_executed")),
        "wordpress_draft_creation_executed": bool(current_phase_execution.get("wordpress_draft_creation_executed")),
        "wordpress_existing_post_update_executed": bool(current_phase_execution.get("wordpress_existing_post_update_executed")),
        "post119_update_executed": bool(current_phase_execution.get("post119_update_executed")),
        "publish_executed": bool(current_phase_execution.get("publish_executed")),
        "future_schedule_executed": bool(current_phase_execution.get("future_schedule_executed")),
        "delete_executed": bool(current_phase_execution.get("delete_executed")),
        "actual_wordpress_go_consumed_by_this_phase": bool(current_phase_execution.get("actual_wordpress_go_consumed_by_this_phase")),
        "final_execute_now_consumed_by_this_phase": bool(current_phase_execution.get("final_execute_now_consumed_by_this_phase")),
        "one_shot_actual_execution_lock_consumed_by_this_phase": bool(current_phase_execution.get("one_shot_actual_execution_lock_consumed_by_this_phase")),
        "runtime_freeze_restored_by_this_phase": bool(current_phase_execution.get("runtime_freeze_restored_by_this_phase")),
        "runner_executed": bool(current_phase_execution.get("runner_executed")),
        "actual_execution_executed": bool(current_phase_execution.get("actual_execution_executed")),
        "ls6b_rerun_executed": bool(current_phase_execution.get("ls6b_rerun_executed")),
        "next_phase": {
            "phase": "LS-6O-C-1",
            "execution_allowed": False,
            "requires_execute_now_cli": True,
            "requires_confirm_final_label": "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
            "requires_ls6oc0_ready": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = read_json(Path(args.policy), errors, "policy")
    confirmation = read_json(Path(args.confirmation), errors, "confirmation")
    ls6oa_ready = read_json(Path(args.ls6oa_ready_result), errors, "ls6oa_ready")
    ls6oa_go = read_json(Path(args.ls6oa_go), errors, "ls6oa_go")
    ls6ob_preflight = read_json(Path(args.ls6ob_preflight_result), errors, "ls6ob_preflight")
    ls6ob_run = read_json(Path(args.ls6ob_run_result), errors, "ls6ob_run")
    ls6ob_validation = read_json(Path(args.ls6ob_validation_result), errors, "ls6ob_validation")
    ls6oc1_not_ready = read_json(Path(args.ls6oc1_not_ready_result), errors, "ls6oc1_not_ready")
    one_shot_lock = read_json(Path(args.one_shot_lock), errors, "one_shot_lock")
    runtime_freeze_state = read_json(Path(args.runtime_freeze_state), errors, "runtime_freeze_state")
    credential_presence = read_json(Path(args.credential_presence_result), errors, "credential_presence")
    ls6c_payload = read_json(Path(args.ls6c_payload), errors, "ls6c_payload")
    ls6c_result = read_json(Path(args.ls6c_result), errors, "ls6c_result")
    ls6b_lock = read_json(Path(args.ls6b_lock), errors, "ls6b_lock")

    require(policy.get("phase") == "LS-6O-C-0", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "FINAL_EXECUTE_NOW_CONFIRMATION_GATE_ONLY", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy.production_status mismatch", errors)

    require(
        confirmation.get("confirmation_status") == "HUMAN_CONFIRMED_FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION",
        "confirmation.confirmation_status mismatch",
        errors,
    )
    require(
        confirmation.get("confirmation_label") == "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY",
        "confirmation.confirmation_label mismatch",
        errors,
    )

    decision = confirmation.get("decision", {})
    require(decision.get("final_execute_now_granted") is True, "decision.final_execute_now_granted must be true", errors)
    require(decision.get("final_execute_now_consumed") is False, "decision.final_execute_now_consumed must be false", errors)
    require(decision.get("actual_execution_allowed_by_this_phase") is False, "decision.actual_execution_allowed_by_this_phase must be false", errors)
    require(decision.get("wordpress_write_allowed_by_this_phase") is False, "decision.wordpress_write_allowed_by_this_phase must be false", errors)
    require(decision.get("wordpress_draft_creation_allowed_by_this_phase") is False, "decision.wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(decision.get("credential_env_read_allowed_by_this_phase") is False, "decision.credential_env_read_allowed_by_this_phase must be false", errors)
    require(decision.get("requires_ls6oc1_execute_now_cli") is True, "decision.requires_ls6oc1_execute_now_cli must be true", errors)

    checklist = confirmation.get("execute_now_checklist", {})
    require(bool(checklist), "execute_now_checklist missing", errors)
    for key, value in checklist.items():
        require(value is True, f"execute_now_checklist {key} must be true", errors)

    current_phase_execution = confirmation.get("current_phase_execution", {})
    require(bool(current_phase_execution), "current_phase_execution missing", errors)
    for key, value in current_phase_execution.items():
        require(value is False, f"current_phase_execution {key} must be false", errors)

    require(ls6oa_ready.get("status") == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION", "LS-6O-A ready status mismatch", errors)
    require(ls6oa_ready.get("actual_wordpress_go_consumed") is False, "LS-6O-A actual_wordpress_go_consumed must be false", errors)
    require(ls6oa_go.get("go_label") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY", "LS-6O-A go label mismatch", errors)

    require(ls6ob_run.get("status") == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE", "LS-6O-B run status mismatch", errors)
    require(ls6ob_validation.get("status") == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE", "LS-6O-B validation status mismatch", errors)
    require(ls6ob_preflight.get("runner_final_preflight_passed") is True, "LS-6O-B runner_final_preflight_passed must be true", errors)

    require(
        ls6oc1_not_ready.get("status") == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_FINAL_EXECUTE_NOW",
        "LS-6O-C-1 not_ready status mismatch",
        errors,
    )

    require(one_shot_lock.get("one_shot_actual_execution_lock_active") is True, "one-shot lock active must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_consumed") is False, "one-shot lock consumed must be false", errors)

    require(runtime_freeze_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)

    require(credential_presence.get("required_keys_present") is True, "credential required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "credential required_keys_non_empty must be true", errors)

    payloads = ls6c_payload.get("payloads", [])
    payload0 = payloads[0] if isinstance(payloads, list) and payloads else {}
    target_payload = policy.get("target_payload", {})
    require(payload0.get("title") == target_payload.get("title") == "2.5次元の誘惑", "payload title mismatch", errors)
    payload_asin = payload0.get("asin")
    if payload_asin is None:
        content = payload0.get("content", "")
        payload_asin = "B07X2G67B4" if "B07X2G67B4" in content else ""
    require(payload_asin == target_payload.get("asin") == "B07X2G67B4", "payload asin mismatch", errors)
    require(payload0.get("post_status") == "draft", "payload post_status must be draft", errors)
    require(str(payload0.get("content_format", "")).lower() == "html", "payload content_format must be html", errors)
    require(int(ls6c_payload.get("max_items", 0) or 0) == 1, "payload max_items must be 1", errors)

    ls6c_status = ls6c_payload.get("status")
    ls6c_result_status = ls6c_result.get("status")
    require(
        ls6c_status == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "LS-6C payload status mismatch",
        errors,
    )
    require(
        ls6c_result_status in {"LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY"},
        "LS-6C result status mismatch",
        errors,
    )

    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B rerun_allowed must be false", errors)

    status = STATUS_READY if not errors else STATUS_NOT_READY
    result = build_result(
        status=status,
        policy=policy,
        confirmation=confirmation,
        ls6oa_ready=ls6oa_ready,
        ls6oa_go=ls6oa_go,
        ls6ob_preflight=ls6ob_preflight,
        ls6ob_run=ls6ob_run,
        ls6ob_validation=ls6ob_validation,
        ls6oc1_not_ready=ls6oc1_not_ready,
        one_shot_lock=one_shot_lock,
        runtime_freeze_state=runtime_freeze_state,
        credential_presence=credential_presence,
        ls6c_payload=ls6c_payload,
        ls6b_lock=ls6b_lock,
        errors=errors,
    )

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
