#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PASS_STATUS = "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE"
NOT_READY_STATUS = "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def validate_prerequisites(
    *,
    policy: dict[str, Any],
    ls6m_run: dict[str, Any],
    ls6m_validation: dict[str, Any],
    credential_presence: dict[str, Any],
    runtime_state: dict[str, Any],
    runtime_lock: dict[str, Any],
    ls6l_ready: dict[str, Any],
    ls6l_confirmation: dict[str, Any],
    ls6k_result: dict[str, Any],
    ls6j_ready: dict[str, Any],
    ls6j_command: dict[str, Any],
    ls6i_validation: dict[str, Any],
    ls6c_payload: dict[str, Any],
    ls6c_result: dict[str, Any],
    ls6b_lock: dict[str, Any],
    errors: list[str],
) -> tuple[bool, str, str, str, int]:
    require(policy.get("phase") == "LS-6N", "policy phase must be LS-6N", errors)
    require(policy.get("execution_mode") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    require(ls6m_run.get("status") == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE", "LS-6M run status mismatch", errors)
    require(ls6m_validation.get("status") == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE", "LS-6M validation status mismatch", errors)

    require(credential_presence.get("status") == "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT", "credential presence status mismatch", errors)
    require(credential_presence.get("required_keys_present") is True, "required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "required_keys_non_empty must be true", errors)

    require(runtime_state.get("runtime_freeze_applied") is True, "runtime_freeze_applied must be true", errors)
    require(runtime_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true", errors)
    require(runtime_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)

    require(runtime_lock.get("locked") is True, "runtime lock locked must be true", errors)
    require(runtime_lock.get("runtime_freeze_active") is True, "runtime lock runtime_freeze_active must be true", errors)
    require(runtime_lock.get("runtime_freeze_applied") is True, "runtime lock runtime_freeze_applied must be true", errors)
    require(runtime_lock.get("rerun_allowed") is False, "runtime lock rerun_allowed must be false", errors)

    require(ls6l_ready.get("status") == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION", "LS-6L status mismatch", errors)
    require(ls6l_confirmation.get("confirmation_status") == "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6L confirmation status mismatch", errors)

    require(ls6k_result.get("status") == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6K status mismatch", errors)

    require(ls6j_ready.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    require(ls6j_command.get("command_status") == "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6J command status mismatch", errors)

    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I status mismatch", errors)

    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)

    payload_ready = ls6c_payload.get("payload_ready") is True
    require(payload_ready, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    max_items = int(ls6c_payload.get("max_items", 0))
    require(max_items == 1, "LS-6C max_items must be 1", errors)

    title = ""
    asin = ""
    post_status = ""
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must have one item", errors)
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        post_status = str(item.get("post_status", ""))
        asin = parse_asin(str(item.get("content", "")))
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
        require(post_status == "draft", "LS-6C post_status must be draft", errors)

    require(ls6b_lock.get("locked") is True, "LS-6B lock.locked must be true", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B lock.rerun_allowed must be false", errors)

    return payload_ready, title, asin, post_status, max_items


def validate_existing_lock(lock_data: dict[str, Any], errors: list[str]) -> None:
    require(lock_data.get("status") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_CREATED_NO_CONSUMPTION_NO_WORDPRESS_WRITE", "existing lock status mismatch", errors)
    require(lock_data.get("locked") is True, "existing lock locked must be true", errors)
    require(lock_data.get("one_shot_actual_execution_lock_created") is True, "existing lock created must be true", errors)
    require(lock_data.get("one_shot_actual_execution_lock_active") is True, "existing lock active must be true", errors)
    require(lock_data.get("one_shot_actual_execution_lock_consumed") is False, "existing lock consumed must be false", errors)
    require(lock_data.get("rerun_allowed") is False, "existing lock rerun_allowed must be false", errors)


def build_lock_payload(*, payload_title: str, payload_asin: str, payload_post_status: str, max_items: int) -> dict[str, Any]:
    return {
        "phase": "LS-6N",
        "document_type": "ONE_SHOT_ACTUAL_EXECUTION_LOCK",
        "status": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_CREATED_NO_CONSUMPTION_NO_WORDPRESS_WRITE",
        "locked": True,
        "one_shot_actual_execution_lock_created": True,
        "one_shot_actual_execution_lock_active": True,
        "one_shot_actual_execution_lock_consumed": False,
        "rerun_allowed": False,
        "created_by_phase": "LS-6N",
        "target_payload": {
            "title": payload_title,
            "asin": payload_asin,
            "post_status": payload_post_status,
            "max_items": max_items,
        },
        "lock_scope": {
            "block_second_execution": True,
            "block_repeated_execution": True,
            "block_publish": True,
            "block_existing_post_update": True,
            "block_non_target_payload": True,
            "block_non_target_asin": True,
            "block_non_draft_status": True,
            "block_max_items_over_one": True,
        },
        "depends_on": {
            "ls6m_runtime_freeze_active": True,
            "ls6m_credential_presence_validated": True,
            "ls6l_final_confirmation_ready": True,
            "ls6j_separate_execution_command_ready": True,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "one_shot_actual_execution_lock_consumed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
    }


def build_preflight_payload(*, payload_ready: bool, payload_title: str, payload_asin: str, payload_post_status: str, max_items: int) -> dict[str, Any]:
    return {
        "phase": "LS-6N",
        "document_type": "FINAL_EXECUTION_PREFLIGHT_RESULT",
        "status": "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE",
        "final_execution_preflight_passed": True,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": max_items,
        "ls6m_validated": True,
        "runtime_freeze_active": True,
        "runtime_freeze_applied": True,
        "credential_presence_check_validated": True,
        "one_shot_actual_execution_lock_created": True,
        "one_shot_actual_execution_lock_active": True,
        "one_shot_actual_execution_lock_consumed": False,
        "actual_execution_allowed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "runtime_freeze_restored": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "errors": [],
    }


def build_run_result(
    *,
    status: str,
    payload_ready: bool,
    payload_title: str,
    payload_asin: str,
    payload_post_status: str,
    max_items: int,
    errors: list[str],
    lock_preexisting: bool,
) -> dict[str, Any]:
    return {
        "phase": "LS-6N",
        "status": status,
        "execution_mode": "ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": max_items,
        "ls6m_validated": True if status == PASS_STATUS else False,
        "credential_presence_check_validated": True if status == PASS_STATUS else False,
        "runtime_freeze_active": True if status == PASS_STATUS else False,
        "runtime_freeze_applied": True if status == PASS_STATUS else False,
        "runtime_freeze_restored": False,
        "one_shot_actual_execution_lock_created": True if status == PASS_STATUS else False,
        "one_shot_actual_execution_lock_active": True if status == PASS_STATUS else False,
        "one_shot_actual_execution_lock_consumed": False,
        "final_execution_preflight_passed": True if status == PASS_STATUS else False,
        "actual_execution_allowed": False,
        "manual_publish_allowed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "execute_approval_label_consumed": False,
        "separate_execution_command_consumed": False,
        "final_runtime_confirmation_consumed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "one_shot_lock_preexisting": lock_preexisting,
        "next_phase": {
            "phase": "LS-6O",
            "execution_allowed": False,
            "requires_ls6n_lock_and_final_preflight_pass": True,
            "requires_explicit_human_actual_execution_go": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6N One-shot Actual Execution Lock and Final Preflight Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- one_shot_actual_execution_lock_created: {result['one_shot_actual_execution_lock_created']}",
        f"- one_shot_actual_execution_lock_active: {result['one_shot_actual_execution_lock_active']}",
        f"- one_shot_actual_execution_lock_consumed: {result['one_shot_actual_execution_lock_consumed']}",
        f"- final_execution_preflight_passed: {result['final_execution_preflight_passed']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        f"- one_shot_lock_preexisting: {result['one_shot_lock_preexisting']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_ls6n_lock_and_final_preflight_pass: {result['next_phase']['requires_ls6n_lock_and_final_preflight_pass']}",
        f"- requires_explicit_human_actual_execution_go: {result['next_phase']['requires_explicit_human_actual_execution_go']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_policy.json")
    parser.add_argument("--ls6m-run-result", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_result.json")
    parser.add_argument("--ls6m-validation-result", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_result.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--ls6l-ready-result", default="exchange/logs/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_ready_result.json")
    parser.add_argument("--ls6l-confirmation", default="exchange/human_review/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.json")
    parser.add_argument("--ls6k-result", default="exchange/logs/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_result.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6j-command", default="exchange/human_review/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--one-shot-lock-output", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--preflight-output", default="exchange/runtime/start_ls6n_final_execution_preflight_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_report.md")
    parser.add_argument("--allow-existing-lock-read-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = load_json(Path(args.policy))
    ls6m_run = load_json(Path(args.ls6m_run_result))
    ls6m_validation = load_json(Path(args.ls6m_validation_result))
    credential_presence = load_json(Path(args.credential_presence_result))
    runtime_state = load_json(Path(args.runtime_freeze_state))
    runtime_lock = load_json(Path(args.runtime_freeze_lock))
    ls6l_ready = load_json(Path(args.ls6l_ready_result))
    ls6l_confirmation = load_json(Path(args.ls6l_confirmation))
    ls6k_result = load_json(Path(args.ls6k_result))
    ls6j_ready = load_json(Path(args.ls6j_ready_result))
    ls6j_command = load_json(Path(args.ls6j_command))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    payload_ready, payload_title, payload_asin, payload_post_status, max_items = validate_prerequisites(
        policy=policy,
        ls6m_run=ls6m_run,
        ls6m_validation=ls6m_validation,
        credential_presence=credential_presence,
        runtime_state=runtime_state,
        runtime_lock=runtime_lock,
        ls6l_ready=ls6l_ready,
        ls6l_confirmation=ls6l_confirmation,
        ls6k_result=ls6k_result,
        ls6j_ready=ls6j_ready,
        ls6j_command=ls6j_command,
        ls6i_validation=ls6i_validation,
        ls6c_payload=ls6c_payload,
        ls6c_result=ls6c_result,
        ls6b_lock=ls6b_lock,
        errors=errors,
    )

    lock_path = Path(args.one_shot_lock_output)
    lock_preexisting = lock_path.exists()
    if lock_preexisting and not args.allow_existing_lock_read_only:
        errors.append(f"existing LS-6N one-shot lock detected: {lock_path}")

    lock_payload: dict[str, Any] | None = None
    if lock_preexisting:
        existing_lock = load_json(lock_path)
        validate_existing_lock(existing_lock, errors)
        lock_payload = existing_lock

    status = PASS_STATUS
    if errors:
        status = NOT_READY_STATUS

    if status == PASS_STATUS and not lock_preexisting:
        lock_payload = build_lock_payload(
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            max_items=max_items,
        )
        write_json(lock_path, lock_payload)

    if status == PASS_STATUS:
        preflight = build_preflight_payload(
            payload_ready=payload_ready,
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            max_items=max_items,
        )
        write_json(Path(args.preflight_output), preflight)

    result = build_run_result(
        status=status,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        max_items=max_items,
        errors=errors,
        lock_preexisting=lock_preexisting,
    )
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
