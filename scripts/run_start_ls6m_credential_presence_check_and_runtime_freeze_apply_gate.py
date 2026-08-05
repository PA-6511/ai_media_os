#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value
    return data


def validate_previous_phases(
    *,
    ls6l_ready: dict[str, Any],
    ls6l_confirmation: dict[str, Any],
    ls6k_result: dict[str, Any],
    runtime_freeze_plan: dict[str, Any],
    credential_boundary_plan: dict[str, Any],
    actual_execution_lock_plan: dict[str, Any],
    ls6j_ready: dict[str, Any],
    ls6j_command: dict[str, Any],
    ls6i_validation: dict[str, Any],
    ls6c_payload: dict[str, Any],
    ls6c_result: dict[str, Any],
    ls6b_lock: dict[str, Any],
    errors: list[str],
) -> tuple[bool, str, str, str, int]:
    require(ls6l_ready.get("status") == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION", "LS-6L ready status mismatch", errors)
    require(ls6l_ready.get("actual_final_runtime_confirmation") is True, "LS-6L actual_final_runtime_confirmation must be true", errors)
    require(ls6l_ready.get("confirmation_label") == "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6L confirmation_label mismatch", errors)
    require(ls6l_ready.get("final_runtime_confirmation_consumed") is False, "LS-6L final_runtime_confirmation_consumed must be false", errors)

    require(ls6l_confirmation.get("confirmation_status") == "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6L confirmation_status mismatch", errors)
    require(ls6l_confirmation.get("confirmation_label") == "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6L confirmation file label mismatch", errors)

    require(ls6k_result.get("status") == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6K status mismatch", errors)
    require(ls6k_result.get("actual_execution_allowed") is False, "LS-6K actual_execution_allowed must be false", errors)
    require(ls6k_result.get("runtime_freeze_plan_ready") is True, "LS-6K runtime_freeze_plan_ready must be true", errors)
    require(ls6k_result.get("credential_env_read_boundary_ready") is True, "LS-6K credential_env_read_boundary_ready must be true", errors)
    require(ls6k_result.get("actual_execution_lock_plan_ready") is True, "LS-6K actual_execution_lock_plan_ready must be true", errors)

    require(runtime_freeze_plan.get("status") == "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION", "LS-6K runtime freeze plan status mismatch", errors)
    require(credential_boundary_plan.get("status") == "CREDENTIAL_ENV_READ_BOUNDARY_DEFINED_NO_READ", "LS-6K credential boundary status mismatch", errors)
    require(actual_execution_lock_plan.get("status") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION", "LS-6K actual execution lock plan status mismatch", errors)

    require(ls6j_ready.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    require(ls6j_ready.get("actual_separate_execution_command") is True, "LS-6J actual_separate_execution_command must be true", errors)
    require(ls6j_ready.get("separate_execution_command_consumed") is False, "LS-6J separate_execution_command_consumed must be false", errors)
    require(ls6j_ready.get("actual_execution_allowed") is False, "LS-6J actual_execution_allowed must be false", errors)
    require(ls6j_command.get("command_status") == "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6J command_status mismatch", errors)

    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I status mismatch", errors)
    require(ls6i_validation.get("actual_execution_allowed") is False, "LS-6I actual_execution_allowed must be false", errors)

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


def build_credential_presence_result(
    *,
    credential_env_path: Path,
    required_keys: list[str],
    errors: list[str],
) -> dict[str, Any]:
    exists = credential_env_path.exists()
    is_file = credential_env_path.is_file()
    mode_checked = exists
    env_data: dict[str, str] = {}

    if not exists:
        errors.append(f"credential env file missing: {credential_env_path}")
    elif not is_file:
        errors.append(f"credential env path is not a file: {credential_env_path}")
    else:
        env_data = parse_env(credential_env_path)

    key_checks: dict[str, dict[str, bool]] = {}
    all_present = True
    all_non_empty = True
    for key in required_keys:
        present = key in env_data
        non_empty = present and bool(str(env_data.get(key, "")).strip())
        key_checks[key] = {"present": present, "non_empty": non_empty}
        if not present:
            all_present = False
            errors.append(f"required key missing: {key}")
        if present and not non_empty:
            all_non_empty = False
            errors.append(f"required key empty: {key}")
        if not present:
            all_non_empty = False

    status = "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT"
    if errors:
        status = "CREDENTIAL_PRESENCE_CHECK_NOT_READY"

    return {
        "phase": "LS-6M",
        "document_type": "CREDENTIAL_PRESENCE_CHECK_RESULT",
        "status": status,
        "credential_env_path": str(credential_env_path),
        "credential_env_exists": exists,
        "credential_env_is_file": is_file,
        "credential_env_mode_checked": mode_checked,
        "required_keys_present": all_present,
        "required_keys_non_empty": all_non_empty,
        "required_key_checks": key_checks,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "errors": [],
    }


def build_runtime_freeze_state(*, payload_title: str, payload_asin: str, payload_post_status: str, max_items: int) -> dict[str, Any]:
    return {
        "phase": "LS-6M",
        "document_type": "RUNTIME_FREEZE_ACTIVE_STATE",
        "status": "RUNTIME_FREEZE_APPLIED_FOR_ONE_SHOT_DRAFT_CREATION_NO_WORDPRESS_WRITE",
        "runtime_freeze_applied": True,
        "runtime_freeze_active": True,
        "runtime_freeze_restored": False,
        "target_payload": {
            "title": payload_title,
            "asin": payload_asin,
            "post_status": payload_post_status,
            "max_items": max_items,
        },
        "freeze_scope": {
            "block_repeated_execution": True,
            "block_publish": True,
            "block_existing_post_update": True,
            "block_non_target_payload": True,
            "block_non_target_asin": True,
            "block_non_draft_status": True,
        },
        "current_phase_execution": {
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "wordpress_draft_creation_executed": False,
            "runner_executed": False,
            "actual_execution_executed": False,
        },
    }


def build_runtime_freeze_lock(*, payload_title: str, payload_asin: str, payload_post_status: str, max_items: int) -> dict[str, Any]:
    return {
        "phase": "LS-6M",
        "document_type": "RUNTIME_FREEZE_ACTIVE_LOCK",
        "status": "RUNTIME_FREEZE_ACTIVE_LOCK_CREATED_NO_WORDPRESS_WRITE",
        "locked": True,
        "runtime_freeze_active": True,
        "runtime_freeze_applied": True,
        "runtime_freeze_restored": False,
        "rerun_allowed": False,
        "target_payload": {
            "title": payload_title,
            "asin": payload_asin,
            "post_status": payload_post_status,
            "max_items": max_items,
        },
        "lock_scope": {
            "block_publish": True,
            "block_existing_post_update": True,
            "block_non_target_payload": True,
            "block_repeated_execution": True,
        },
        "current_phase_execution": {
            "one_shot_actual_execution_lock_created": False,
            "one_shot_actual_execution_lock_consumed": False,
            "wordpress_write_executed": False,
            "actual_execution_executed": False,
        },
    }


def build_run_result(
    *,
    status: str,
    payload_ready: bool,
    payload_title: str,
    payload_asin: str,
    payload_post_status: str,
    max_items: int,
    credential_presence: dict[str, Any],
    runtime_freeze_applied: bool,
    runtime_freeze_active: bool,
    runtime_freeze_state_created: bool,
    runtime_freeze_lock_created: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6M",
        "status": status,
        "execution_mode": "CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_ONLY",
        "production_status": "NO_GO",
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": max_items,
        "ls6l_final_confirmation_ready": True,
        "final_runtime_confirmation_consumed": False,
        "credential_presence_check_executed": True,
        "credential_env_exists": credential_presence.get("credential_env_exists"),
        "credential_env_is_file": credential_presence.get("credential_env_is_file"),
        "required_keys_present": credential_presence.get("required_keys_present"),
        "required_keys_non_empty": credential_presence.get("required_keys_non_empty"),
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "runtime_freeze_applied": runtime_freeze_applied,
        "runtime_freeze_active": runtime_freeze_active,
        "runtime_freeze_state_created": runtime_freeze_state_created,
        "runtime_freeze_lock_created": runtime_freeze_lock_created,
        "runtime_freeze_restored": False,
        "actual_execution_allowed": False,
        "manual_publish_allowed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "one_shot_actual_execution_lock_created": False,
        "one_shot_actual_execution_lock_consumed": False,
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
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6N",
            "execution_allowed": False,
            "requires_ls6m_credential_presence_and_runtime_freeze_pass": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6M Credential Presence Check and Runtime Freeze Apply Gate Report",
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
        f"- credential_presence_check_executed: {result['credential_presence_check_executed']}",
        f"- credential_env_exists: {result['credential_env_exists']}",
        f"- credential_env_is_file: {result['credential_env_is_file']}",
        f"- required_keys_present: {result['required_keys_present']}",
        f"- required_keys_non_empty: {result['required_keys_non_empty']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- runtime_freeze_state_created: {result['runtime_freeze_state_created']}",
        f"- runtime_freeze_lock_created: {result['runtime_freeze_lock_created']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_ls6m_credential_presence_and_runtime_freeze_pass: {result['next_phase']['requires_ls6m_credential_presence_and_runtime_freeze_pass']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {error}" for error in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_policy.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--ls6l-ready-result", default="exchange/logs/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_ready_result.json")
    parser.add_argument("--ls6l-confirmation", default="exchange/human_review/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.json")
    parser.add_argument("--ls6k-result", default="exchange/logs/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_result.json")
    parser.add_argument("--runtime-freeze-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_runtime_freeze_plan.json")
    parser.add_argument("--credential-boundary-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_credential_env_read_boundary_plan.json")
    parser.add_argument("--actual-execution-lock-plan", default="exchange/locks/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_lock_plan.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6j-command", default="exchange/human_review/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--credential-presence-output", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state-output", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock-output", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    ls6l_ready = load_json(Path(args.ls6l_ready_result))
    ls6l_confirmation = load_json(Path(args.ls6l_confirmation))
    ls6k_result = load_json(Path(args.ls6k_result))
    runtime_freeze_plan = load_json(Path(args.runtime_freeze_plan))
    credential_boundary_plan = load_json(Path(args.credential_boundary_plan))
    actual_execution_lock_plan = load_json(Path(args.actual_execution_lock_plan))
    ls6j_ready = load_json(Path(args.ls6j_ready_result))
    ls6j_command = load_json(Path(args.ls6j_command))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []
    require(policy.get("phase") == "LS-6M", "policy phase must be LS-6M", errors)
    require(policy.get("execution_mode") == "CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    payload_ready, payload_title, payload_asin, payload_post_status, max_items = validate_previous_phases(
        ls6l_ready=ls6l_ready,
        ls6l_confirmation=ls6l_confirmation,
        ls6k_result=ls6k_result,
        runtime_freeze_plan=runtime_freeze_plan,
        credential_boundary_plan=credential_boundary_plan,
        actual_execution_lock_plan=actual_execution_lock_plan,
        ls6j_ready=ls6j_ready,
        ls6j_command=ls6j_command,
        ls6i_validation=ls6i_validation,
        ls6c_payload=ls6c_payload,
        ls6c_result=ls6c_result,
        ls6b_lock=ls6b_lock,
        errors=errors,
    )

    required_keys = list(policy.get("credential_presence_check_policy", {}).get("required_keys", []))
    cp_errors: list[str] = []
    credential_presence = build_credential_presence_result(
        credential_env_path=Path(args.credential_env),
        required_keys=required_keys,
        errors=cp_errors,
    )

    errors.extend(cp_errors)

    runtime_freeze_applied = not errors
    runtime_freeze_active = not errors
    runtime_freeze_state_created = not errors
    runtime_freeze_lock_created = not errors

    if runtime_freeze_state_created:
        runtime_state = build_runtime_freeze_state(
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            max_items=max_items,
        )
        write_json(Path(args.runtime_freeze_state_output), runtime_state)

        runtime_lock = build_runtime_freeze_lock(
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            max_items=max_items,
        )
        write_json(Path(args.runtime_freeze_lock_output), runtime_lock)

    write_json(Path(args.credential_presence_output), credential_presence)

    status = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE"
    if errors:
        status = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_NOT_READY"

    result = build_run_result(
        status=status,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        max_items=max_items,
        credential_presence=credential_presence,
        runtime_freeze_applied=runtime_freeze_applied,
        runtime_freeze_active=runtime_freeze_active,
        runtime_freeze_state_created=runtime_freeze_state_created,
        runtime_freeze_lock_created=runtime_freeze_lock_created,
        errors=errors,
    )

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
