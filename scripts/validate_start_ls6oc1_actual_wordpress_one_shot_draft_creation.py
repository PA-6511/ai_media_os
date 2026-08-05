#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATED_ONE_SHOT_DRAFT_ONLY"
STATUS_NOT_READY = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_VALIDATION_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def resolve_required_final_label(policy: dict[str, Any]) -> str:
    primary = policy.get("actual_execution_policy", {}).get("required_confirm_final_label")
    fallback = policy.get("required_previous_phase", {}).get("ls6oc0", {}).get("required_label")
    if isinstance(primary, str) and primary:
        return primary
    if isinstance(fallback, str) and fallback:
        return fallback
    return "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"


def get_confirmation_label(ls6oc0_confirmation: dict[str, Any]) -> str:
    return str(
        ls6oc0_confirmation.get("confirmation_label")
        or ls6oc0_confirmation.get("confirm_final_label")
        or ls6oc0_confirmation.get("final_execute_now_label")
        or ls6oc0_confirmation.get("label")
        or ""
    )


def build_result(status: str, execution: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ok = status == STATUS_VALIDATED
    return {
        "phase": "LS-6O-C-1",
        "status": status,
        "execution_mode": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONE_SHOT_ONLY",
        "production_status": "ONE_SHOT_DRAFT_CREATED" if ok else "VALIDATION_NOT_READY",
        "new_post_id": int(execution.get("new_post_id", 0)),
        "returned_post_status": execution.get("returned_post_status", ""),
        "created_count": int(execution.get("created_count", 0)),
        "wordpress_api_call_executed": bool(execution.get("wordpress_api_call_executed")),
        "wordpress_write_executed": bool(execution.get("wordpress_write_executed")),
        "wordpress_draft_creation_executed": bool(execution.get("wordpress_draft_creation_executed")),
        "wordpress_existing_post_update_executed": bool(execution.get("wordpress_existing_post_update_executed")),
        "post119_update_executed": bool(execution.get("post119_update_executed")),
        "publish_executed": bool(execution.get("publish_executed")),
        "future_schedule_executed": bool(execution.get("future_schedule_executed")),
        "delete_executed": bool(execution.get("delete_executed")),
        "credential_env_read_executed": bool(execution.get("credential_env_read_executed")),
        "credential_value_output": bool(execution.get("credential_value_output")),
        "credential_value_persisted": bool(execution.get("credential_value_persisted")),
        "credential_secret_output": bool(execution.get("credential_secret_output")),
        "secret_length_output": bool(execution.get("secret_length_output")),
        "secret_hash_output": bool(execution.get("secret_hash_output")),
        "authorization_header_output": bool(execution.get("authorization_header_output")),
        "actual_wordpress_go_consumed_by_this_phase": bool(execution.get("actual_wordpress_go_consumed_by_this_phase")),
        "final_execute_now_consumed_by_this_phase": bool(execution.get("final_execute_now_consumed_by_this_phase")),
        "one_shot_actual_execution_lock_consumed_by_this_phase": bool(execution.get("one_shot_actual_execution_lock_consumed_by_this_phase")),
        "runtime_freeze_restored": bool(execution.get("runtime_freeze_restored")),
        "runner_executed": bool(execution.get("runner_executed")),
        "actual_execution_executed": bool(execution.get("actual_execution_executed")),
        "next_phase": {
            "phase": "LS-6P",
            "requires_post_id_verification": True,
            "requires_runtime_freeze_restore": True,
            "execution_allowed": False,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6O-C-1 Actual WordPress One-shot Draft Creation Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- new_post_id: {result['new_post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- created_count: {result['created_count']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
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
    parser.add_argument("--policy", default="config/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_policy.json")
    parser.add_argument("--execution-result", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6oc0-ready-result", default="exchange/logs/start_ls6oc0_final_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6oc0-confirmation", default="exchange/human_review/start_ls6oc0_final_execute_now_confirmation.json")
    parser.add_argument("--ls6ob-validation-result", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_validation_result.json")
    parser.add_argument("--ls6oa-ready-result", default="exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_ready_result.json")
    parser.add_argument("--ls6oa-go", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json")
    parser.add_argument("--one-shot-lock", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls6oc1_actual_wordpress_one_shot_draft_creation_validation_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = load_json(Path(args.policy))
    execution = load_json(Path(args.execution_result))
    consumption = load_json(Path(args.consumption_lock))
    run_result = load_json(Path(args.run_result))
    ls6oc0_ready = load_json(Path(args.ls6oc0_ready_result))
    ls6oc0_confirmation = load_json(Path(args.ls6oc0_confirmation))
    ls6ob_validation = load_json(Path(args.ls6ob_validation_result))
    ls6oa_ready = load_json(Path(args.ls6oa_ready_result))
    ls6oa_go = load_json(Path(args.ls6oa_go))
    one_shot_lock = load_json(Path(args.one_shot_lock))
    runtime_freeze_state = load_json(Path(args.runtime_freeze_state))
    credential_presence = load_json(Path(args.credential_presence_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))

    require(policy.get("phase") == "LS-6O-C-1", "policy phase mismatch", errors)
    require(run_result.get("status") == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY", "run status must be EXECUTED", errors)
    require(execution.get("status") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATED_DRAFT_ONLY", "execution result status mismatch", errors)

    require(ls6oc0_ready.get("status") == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION", "LS-6O-C-0 ready status mismatch", errors)
    required_label = resolve_required_final_label(policy)
    require(ls6oc0_ready.get("confirmation_label") == required_label, "LS-6O-C-0 ready confirmation_label mismatch", errors)
    require(get_confirmation_label(ls6oc0_confirmation) == required_label, "LS-6O-C-0 confirmation label mismatch", errors)
    require(
        ls6oc0_confirmation.get("decision", {}).get("required_confirm_final_label") == required_label,
        "LS-6O-C-0 confirmation decision required label mismatch",
        errors,
    )

    require(ls6ob_validation.get("status") == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE", "LS-6O-B validation status mismatch", errors)
    require(ls6oa_ready.get("status") == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION", "LS-6O-A ready status mismatch", errors)
    require(ls6oa_go.get("go_label") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY", "LS-6O-A go label mismatch", errors)

    require(one_shot_lock.get("one_shot_actual_execution_lock_active") is True, "one-shot lock must be active", errors)
    require(runtime_freeze_state.get("runtime_freeze_active") is True, "runtime freeze active must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_restored") is False, "runtime freeze restored must be false", errors)
    require(credential_presence.get("required_keys_present") is True, "credential presence required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "credential presence required_keys_non_empty must be true", errors)

    require(execution.get("payload_title") == "2.5次元の誘惑", "payload_title mismatch", errors)
    require(execution.get("payload_asin") == "B07X2G67B4", "payload_asin mismatch", errors)
    require(execution.get("requested_post_status") == "draft", "requested_post_status must be draft", errors)
    require(execution.get("returned_post_status") == "draft", "returned_post_status must be draft", errors)
    require(int(execution.get("new_post_id", 0)) >= 1, "new_post_id must be >= 1", errors)
    require(int(execution.get("created_count", 0)) == 1, "created_count must be 1", errors)
    require(int(execution.get("max_items", 0)) == 1, "max_items must be 1", errors)

    require(execution.get("wordpress_api_call_executed") is True, "wordpress_api_call_executed must be true", errors)
    require(execution.get("wordpress_write_executed") is True, "wordpress_write_executed must be true", errors)
    require(execution.get("wordpress_draft_creation_executed") is True, "wordpress_draft_creation_executed must be true", errors)
    require(execution.get("credential_env_read_executed") is True, "credential_env_read_executed must be true", errors)

    require(execution.get("credential_value_output") is False, "credential_value_output must be false", errors)
    require(execution.get("credential_value_persisted") is False, "credential_value_persisted must be false", errors)
    require(execution.get("credential_secret_output") is False, "credential_secret_output must be false", errors)
    require(execution.get("secret_length_output") is False, "secret_length_output must be false", errors)
    require(execution.get("secret_hash_output") is False, "secret_hash_output must be false", errors)
    require(execution.get("authorization_header_output") is False, "authorization_header_output must be false", errors)

    require(execution.get("wordpress_existing_post_update_executed") is False, "wordpress_existing_post_update_executed must be false", errors)
    require(execution.get("post119_update_executed") is False, "post119_update_executed must be false", errors)
    require(execution.get("publish_executed") is False, "publish_executed must be false", errors)
    require(execution.get("future_schedule_executed") is False, "future_schedule_executed must be false", errors)
    require(execution.get("delete_executed") is False, "delete_executed must be false", errors)

    require(execution.get("actual_wordpress_go_consumed_by_this_phase") is True, "actual_wordpress_go_consumed_by_this_phase must be true", errors)
    require(execution.get("final_execute_now_consumed_by_this_phase") is True, "final_execute_now_consumed_by_this_phase must be true", errors)
    require(execution.get("one_shot_actual_execution_lock_consumed_by_this_phase") is True, "one_shot_actual_execution_lock_consumed_by_this_phase must be true", errors)

    require(execution.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)
    require(execution.get("runner_executed") is True, "runner_executed must be true", errors)
    require(execution.get("actual_execution_executed") is True, "actual_execution_executed must be true", errors)

    require(consumption.get("locked") is True, "consumption.locked must be true", errors)
    require(consumption.get("rerun_allowed") is False, "consumption.rerun_allowed must be false", errors)
    require(consumption.get("actual_wordpress_go_consumed") is True, "consumption.actual_wordpress_go_consumed must be true", errors)
    require(consumption.get("final_execute_now_consumed") is True, "consumption.final_execute_now_consumed must be true", errors)
    require(consumption.get("one_shot_actual_execution_lock_consumed") is True, "consumption.one_shot_actual_execution_lock_consumed must be true", errors)
    require(consumption.get("created_count") == 1, "consumption.created_count must be 1", errors)
    require(int(consumption.get("new_post_id", 0)) >= 1, "consumption.new_post_id must be >= 1", errors)
    require(consumption.get("next_phase", {}).get("phase") == "LS-6P", "consumption next_phase must be LS-6P", errors)

    expected_payloads = ls6c_payload.get("payloads", [])
    if isinstance(expected_payloads, list) and len(expected_payloads) == 1:
        expected_title = expected_payloads[0].get("title")
        require(expected_title == execution.get("payload_title"), "execution payload_title and LS-6C payload title mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_READY
    result = build_result(status, execution, errors)
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
