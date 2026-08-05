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


def validate_false_fields(data: dict[str, Any], keys: list[str], prefix: str, errors: list[str]) -> None:
    for key in keys:
        require(data.get(key) is False, f"{prefix}.{key} must be false", errors)


def build_validation_result(status: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6M",
        "status": status,
        "execution_mode": "CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_ONLY",
        "production_status": "NO_GO",
        "credential_presence_check_validated": status == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE",
        "runtime_freeze_apply_validated": status == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE",
        "runtime_freeze_active": True if not errors else False,
        "runtime_freeze_restored": False,
        "actual_execution_allowed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "one_shot_actual_execution_lock_created": False,
        "one_shot_actual_execution_lock_consumed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
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
        "# LS-6M Credential Presence Check and Runtime Freeze Apply Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- credential_presence_check_validated: {result['credential_presence_check_validated']}",
        f"- runtime_freeze_apply_validated: {result['runtime_freeze_apply_validated']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
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
    parser.add_argument("--run-result", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_result.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--ls6l-ready-result", default="exchange/logs/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_ready_result.json")
    parser.add_argument("--ls6k-result", default="exchange/logs/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_result.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    run_result = load_json(Path(args.run_result))
    cp_result = load_json(Path(args.credential_presence_result))
    freeze_state = load_json(Path(args.runtime_freeze_state))
    freeze_lock = load_json(Path(args.runtime_freeze_lock))
    ls6l_ready = load_json(Path(args.ls6l_ready_result))
    ls6k_result = load_json(Path(args.ls6k_result))
    ls6j_ready = load_json(Path(args.ls6j_ready_result))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []

    require(policy.get("phase") == "LS-6M", "policy phase must be LS-6M", errors)
    require(run_result.get("status") == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_PASSED_NO_WORDPRESS_WRITE", "run result status mismatch", errors)

    require(ls6l_ready.get("status") == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION", "LS-6L ready status mismatch", errors)
    require(ls6k_result.get("status") == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6K status mismatch", errors)
    require(ls6j_ready.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B rerun_allowed must be false", errors)

    require(cp_result.get("status") == "CREDENTIAL_PRESENCE_CHECK_PASSED_NO_SECRET_OUTPUT", "credential presence status mismatch", errors)
    require(cp_result.get("credential_env_exists") is True, "credential_env_exists must be true", errors)
    require(cp_result.get("credential_env_is_file") is True, "credential_env_is_file must be true", errors)
    require(cp_result.get("required_keys_present") is True, "required_keys_present must be true", errors)
    require(cp_result.get("required_keys_non_empty") is True, "required_keys_non_empty must be true", errors)

    validate_false_fields(
        cp_result,
        [
            "credential_value_output",
            "credential_value_persisted",
            "credential_secret_output",
            "secret_length_output",
            "secret_hash_output",
            "authorization_header_output",
        ],
        "credential_presence_result",
        errors,
    )

    require(freeze_state.get("status") == "RUNTIME_FREEZE_APPLIED_FOR_ONE_SHOT_DRAFT_CREATION_NO_WORDPRESS_WRITE", "runtime freeze state status mismatch", errors)
    require(freeze_state.get("runtime_freeze_applied") is True, "runtime_freeze_applied must be true", errors)
    require(freeze_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true", errors)
    require(freeze_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)

    require(freeze_lock.get("locked") is True, "runtime freeze lock locked must be true", errors)
    require(freeze_lock.get("rerun_allowed") is False, "runtime freeze lock rerun_allowed must be false", errors)

    validate_false_fields(
        run_result,
        [
            "one_shot_actual_execution_lock_created",
            "one_shot_actual_execution_lock_consumed",
            "wordpress_api_call_executed",
            "wordpress_write_executed",
            "wordpress_draft_creation_executed",
            "runner_executed",
            "actual_execution_executed",
            "actual_execution_allowed",
            "wordpress_write_allowed_by_this_phase",
            "wordpress_draft_creation_allowed_by_this_phase",
        ],
        "run_result",
        errors,
    )

    require(run_result.get("runtime_freeze_applied") is True, "run_result.runtime_freeze_applied must be true", errors)
    require(run_result.get("runtime_freeze_active") is True, "run_result.runtime_freeze_active must be true", errors)
    require(run_result.get("runtime_freeze_restored") is False, "run_result.runtime_freeze_restored must be false", errors)
    require(run_result.get("next_phase", {}).get("phase") == "LS-6N", "next_phase.phase must be LS-6N", errors)
    require(run_result.get("next_phase", {}).get("execution_allowed") is False, "next_phase.execution_allowed must be false", errors)

    status = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE"
    if errors:
        status = "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATION_NOT_READY"

    validation_result = build_validation_result(status, errors)
    write_json(Path(args.output), validation_result)
    write_report(validation_result, Path(args.report))
    print(json.dumps(validation_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
