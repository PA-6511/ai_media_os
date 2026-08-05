#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def validate_all_false(mapping: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key, value in mapping.items():
        require(value is False, f"{prefix}.{key} must be false", errors)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6L", "policy phase must be LS-6L", errors)
    require(policy.get("execution_mode") == "FINAL_CONFIRMATION_GATE_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    final_policy = policy.get("final_confirmation_policy", {})
    require(final_policy.get("human_final_confirmation_required") is True, "policy human_final_confirmation_required must be true", errors)
    require(final_policy.get("actual_confirmation_file_auto_create_allowed") is False, "policy actual_confirmation_file_auto_create_allowed must be false", errors)
    require(final_policy.get("runtime_freeze_apply_allowed_by_this_phase") is False, "policy runtime_freeze_apply_allowed_by_this_phase must be false", errors)
    require(final_policy.get("credential_env_read_allowed_by_this_phase") is False, "policy credential_env_read_allowed_by_this_phase must be false", errors)
    require(final_policy.get("credential_presence_check_allowed_by_this_phase") is False, "policy credential_presence_check_allowed_by_this_phase must be false", errors)
    require(final_policy.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(final_policy.get("actual_execution_allowed_by_this_phase") is False, "policy actual_execution_allowed_by_this_phase must be false", errors)
    validate_all_false(policy.get("current_phase_safety_flags", {}), "policy current_phase_safety_flags", errors)


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("phase") == "LS-6L", "template phase must be LS-6L", errors)
    require(template.get("confirmation_type") == "HUMAN_FINAL_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_CONFIRMATION", "template confirmation_type mismatch", errors)
    require(template.get("confirmation_status") == "TEMPLATE_NOT_ACTUAL_FINAL_CONFIRMATION", "template confirmation_status mismatch", errors)
    require(template.get("confirmation_label") == "NOT_CONFIRMED_YET", "template confirmation_label mismatch", errors)


def validate_ls6k(ls6k_result: dict[str, Any], errors: list[str]) -> bool:
    require(ls6k_result.get("status") == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6K status mismatch", errors)
    require(ls6k_result.get("runtime_freeze_plan_ready") is True, "LS-6K runtime_freeze_plan_ready must be true", errors)
    require(ls6k_result.get("credential_env_read_boundary_ready") is True, "LS-6K credential_env_read_boundary_ready must be true", errors)
    require(ls6k_result.get("actual_execution_lock_plan_ready") is True, "LS-6K actual_execution_lock_plan_ready must be true", errors)
    require(ls6k_result.get("actual_execution_allowed") is False, "LS-6K actual_execution_allowed must be false", errors)
    require(ls6k_result.get("credential_env_read_executed") is False, "LS-6K credential_env_read_executed must be false", errors)
    require(ls6k_result.get("runtime_freeze_applied") is False, "LS-6K runtime_freeze_applied must be false", errors)
    require(ls6k_result.get("runtime_freeze_restored") is False, "LS-6K runtime_freeze_restored must be false", errors)
    return ls6k_result.get("status") == "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION"


def validate_runtime_freeze_plan(plan: dict[str, Any], errors: list[str]) -> bool:
    require(plan.get("status") == "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION", "runtime freeze plan status mismatch", errors)
    require(plan.get("runtime_freeze_required") is True, "runtime freeze plan runtime_freeze_required must be true", errors)
    require(plan.get("runtime_freeze_applied_by_this_phase") is False, "runtime freeze plan runtime_freeze_applied_by_this_phase must be false", errors)
    require(plan.get("runtime_freeze_restored_by_this_phase") is False, "runtime freeze plan runtime_freeze_restored_by_this_phase must be false", errors)
    validate_all_false(plan.get("current_phase_execution", {}), "runtime freeze plan current_phase_execution", errors)
    return plan.get("status") == "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION"


def validate_credential_boundary(plan: dict[str, Any], errors: list[str]) -> bool:
    require(plan.get("status") == "CREDENTIAL_ENV_READ_BOUNDARY_DEFINED_NO_READ", "credential boundary status mismatch", errors)
    require(plan.get("credential_env_read_allowed_by_this_phase") is False, "credential boundary credential_env_read_allowed_by_this_phase must be false", errors)
    require(plan.get("credential_env_read_executed") is False, "credential boundary credential_env_read_executed must be false", errors)
    require(plan.get("credential_secret_output_allowed") is False, "credential boundary credential_secret_output_allowed must be false", errors)
    future = plan.get("future_read_rules", {})
    require(future.get("value_output_forbidden") is True, "credential boundary value_output_forbidden must be true", errors)
    require(future.get("length_output_forbidden") is True, "credential boundary length_output_forbidden must be true", errors)
    require(future.get("hash_output_forbidden") is True, "credential boundary hash_output_forbidden must be true", errors)
    require(future.get("authorization_header_output_forbidden") is True, "credential boundary authorization_header_output_forbidden must be true", errors)
    validate_all_false(plan.get("current_phase_execution", {}), "credential boundary current_phase_execution", errors)
    return plan.get("status") == "CREDENTIAL_ENV_READ_BOUNDARY_DEFINED_NO_READ"


def validate_execution_lock_plan(plan: dict[str, Any], errors: list[str]) -> bool:
    require(plan.get("status") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION", "actual execution lock plan status mismatch", errors)
    require(plan.get("one_shot_actual_execution_lock_required") is True, "actual execution lock plan required must be true", errors)
    require(plan.get("one_shot_actual_execution_lock_created_by_this_phase") is False, "actual execution lock plan created_by_this_phase must be false", errors)
    require(plan.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "actual execution lock plan consumed_by_this_phase must be false", errors)
    require(plan.get("rerun_allowed") is False, "actual execution lock plan rerun_allowed must be false", errors)
    validate_all_false(plan.get("current_phase_execution", {}), "actual execution lock plan current_phase_execution", errors)
    return plan.get("status") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION"


def validate_ls6j(ls6j_result: dict[str, Any], ls6j_command: dict[str, Any], errors: list[str]) -> None:
    require(ls6j_result.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    require(ls6j_result.get("actual_separate_execution_command") is True, "LS-6J actual_separate_execution_command must be true", errors)
    require(ls6j_result.get("separate_execution_command_consumed") is False, "LS-6J separate_execution_command_consumed must be false", errors)
    require(ls6j_result.get("actual_execution_allowed") is False, "LS-6J actual_execution_allowed must be false", errors)
    require(ls6j_result.get("command_label") == "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6J command_label mismatch", errors)
    require(ls6j_command.get("command_status") == "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6J command_status mismatch", errors)
    require(ls6j_command.get("command_label") == "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6J command file command_label mismatch", errors)


def validate_ls6i(ls6i_validation: dict[str, Any], errors: list[str]) -> None:
    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I validation status mismatch", errors)
    require(ls6i_validation.get("actual_execution_allowed") is False, "LS-6I actual_execution_allowed must be false", errors)
    require(ls6i_validation.get("runner_executed") is False, "LS-6I runner_executed must be false", errors)
    require(ls6i_validation.get("actual_execution_executed") is False, "LS-6I actual_execution_executed must be false", errors)


def validate_ls6h(ls6h_result: dict[str, Any], errors: list[str]) -> None:
    require(ls6h_result.get("status") == "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION", "LS-6H status mismatch", errors)
    require(ls6h_result.get("execute_approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY", "LS-6H execute_approval_label mismatch", errors)
    require(ls6h_result.get("execute_approval_label_consumed") is False, "LS-6H execute_approval_label_consumed must be false", errors)


def validate_ls6g(ls6g_result: dict[str, Any], errors: list[str]) -> None:
    require(ls6g_result.get("status") == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6G status mismatch", errors)
    require(ls6g_result.get("execution_allowed") is False, "LS-6G execution_allowed must be false", errors)
    require(ls6g_result.get("approval_label_consumed") is False, "LS-6G approval_label_consumed must be false", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str, str, int]:
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    payload_ready = ls6c_payload.get("payload_ready") is True
    require(payload_ready, "LS-6C payload_ready must be true", errors)
    payload_count = int(ls6c_payload.get("payload_count", 0))
    max_items = int(ls6c_payload.get("max_items", 0))
    require(payload_count == 1, "LS-6C payload_count must be 1", errors)
    require(max_items == 1, "LS-6C max_items must be 1", errors)
    title = ""
    asin = ""
    post_status = ""
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        post_status = str(item.get("post_status", ""))
        asin = parse_asin(str(item.get("content", "")))
        require(post_status == "draft", "LS-6C post_status must be draft", errors)
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
    return payload_ready, title, asin, post_status, max_items


def validate_ls6b(ls6b_lock: dict[str, Any], errors: list[str]) -> None:
    require(ls6b_lock.get("locked") is True, "LS-6B lock.locked must be true", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B lock.rerun_allowed must be false", errors)


def validate_actual_confirmation(actual: dict[str, Any], errors: list[str]) -> str:
    require(actual.get("phase") == "LS-6L", "actual confirmation phase must be LS-6L", errors)
    require(actual.get("confirmation_type") == "HUMAN_FINAL_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_CONFIRMATION", "actual confirmation_type mismatch", errors)
    require(actual.get("confirmation_status") == "HUMAN_CONFIRMED_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_FOR_ONE_SHOT_DRAFT_CREATION", "actual confirmation_status mismatch", errors)
    label = str(actual.get("confirmation_label", ""))
    require(label == "FINAL_RUNTIME_CONFIRMATION_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "actual confirmation_label mismatch", errors)
    require(actual.get("confirmed_by") not in {None, "", "HUMAN_REQUIRED"}, "actual confirmed_by must be set", errors)
    require(actual.get("confirmed_at") not in {None, "", "HUMAN_REQUIRED"}, "actual confirmed_at must be set", errors)
    target = actual.get("target_payload", {})
    require(target.get("title_expected") == "2.5次元の誘惑", "actual target title mismatch", errors)
    require(target.get("asin_expected") == "B07X2G67B4", "actual target asin mismatch", errors)
    require(target.get("post_status_expected") == "draft", "actual target post_status mismatch", errors)
    require(target.get("max_items") == 1, "actual target max_items must be 1", errors)
    checklist = actual.get("confirmation_checklist", {})
    for key, value in checklist.items():
        require(value is True, f"actual confirmation_checklist.{key} must be true", errors)
    decision = actual.get("decision", {})
    require(decision.get("human_final_runtime_confirmation_granted") is True, "actual decision human_final_runtime_confirmation_granted must be true", errors)
    require(decision.get("final_runtime_confirmation_consumed") is False, "actual decision final_runtime_confirmation_consumed must be false", errors)
    require(decision.get("runtime_freeze_apply_allowed_by_this_phase") is False, "actual decision runtime_freeze_apply_allowed_by_this_phase must be false", errors)
    require(decision.get("credential_env_read_allowed_by_this_phase") is False, "actual decision credential_env_read_allowed_by_this_phase must be false", errors)
    require(decision.get("credential_presence_check_allowed_by_this_phase") is False, "actual decision credential_presence_check_allowed_by_this_phase must be false", errors)
    require(decision.get("wordpress_write_allowed_by_this_phase") is False, "actual decision wordpress_write_allowed_by_this_phase must be false", errors)
    require(decision.get("wordpress_draft_creation_allowed_by_this_phase") is False, "actual decision wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(decision.get("actual_execution_allowed_by_this_phase") is False, "actual decision actual_execution_allowed_by_this_phase must be false", errors)
    require(decision.get("requires_next_phase_credential_presence_and_freeze_apply_gate") is True, "actual decision requires_next_phase_credential_presence_and_freeze_apply_gate must be true", errors)
    validate_all_false(actual.get("current_phase_execution", {}), "actual current_phase_execution", errors)
    return label


def build_result(*, status: str, actual_final_runtime_confirmation: bool, payload_ready: bool, payload_title: str, payload_asin: str, payload_post_status: str, max_items: int, ls6k_boundary_passed: bool, runtime_freeze_plan_ready: bool, credential_env_read_boundary_ready: bool, actual_execution_lock_plan_ready: bool, confirmation_label: str | None, errors: list[str]) -> dict[str, Any]:
    result = {
        "phase": "LS-6L",
        "status": status,
        "execution_mode": "FINAL_CONFIRMATION_GATE_ONLY",
        "production_status": "NO_GO",
        "actual_final_runtime_confirmation": actual_final_runtime_confirmation,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": max_items,
        "ls6k_boundary_passed": ls6k_boundary_passed,
        "runtime_freeze_plan_ready": runtime_freeze_plan_ready,
        "credential_env_read_boundary_ready": credential_env_read_boundary_ready,
        "actual_execution_lock_plan_ready": actual_execution_lock_plan_ready,
        "actual_execution_allowed": False,
        "runtime_freeze_apply_allowed_by_this_phase": False,
        "runtime_freeze_applied": False,
        "runtime_freeze_restored": False,
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_presence_check_allowed_by_this_phase": False,
        "credential_presence_check_executed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "final_runtime_confirmation_consumed": False,
        "separate_execution_command_consumed": False,
        "one_shot_actual_execution_lock_created": False,
        "one_shot_actual_execution_lock_consumed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "execute_approval_label_consumed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6M",
            "execution_allowed": False,
            "requires_ls6l_final_confirmation_ready": True
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    if confirmation_label is not None:
        result["confirmation_label"] = confirmation_label
    return result


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6L Runtime Freeze and Credential Read Boundary Final Confirmation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- actual_final_runtime_confirmation: {result['actual_final_runtime_confirmation']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- ls6k_boundary_passed: {result['ls6k_boundary_passed']}",
        f"- runtime_freeze_plan_ready: {result['runtime_freeze_plan_ready']}",
        f"- credential_env_read_boundary_ready: {result['credential_env_read_boundary_ready']}",
        f"- actual_execution_lock_plan_ready: {result['actual_execution_lock_plan_ready']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- runtime_freeze_apply_allowed_by_this_phase: {result['runtime_freeze_apply_allowed_by_this_phase']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- credential_env_read_allowed_by_this_phase: {result['credential_env_read_allowed_by_this_phase']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- credential_presence_check_allowed_by_this_phase: {result['credential_presence_check_allowed_by_this_phase']}",
        f"- credential_presence_check_executed: {result['credential_presence_check_executed']}",
        f"- wordpress_api_call_allowed_by_this_phase: {result['wordpress_api_call_allowed_by_this_phase']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- final_runtime_confirmation_consumed: {result['final_runtime_confirmation_consumed']}",
        f"- separate_execution_command_consumed: {result['separate_execution_command_consumed']}",
        f"- one_shot_actual_execution_lock_created: {result['one_shot_actual_execution_lock_created']}",
        f"- one_shot_actual_execution_lock_consumed: {result['one_shot_actual_execution_lock_consumed']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_secret_output: {result['credential_secret_output']}",
        f"- secret_length_output: {result['secret_length_output']}",
        f"- secret_hash_output: {result['secret_hash_output']}",
        f"- authorization_header_output: {result['authorization_header_output']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- execute_approval_label_consumed: {result['execute_approval_label_consumed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_ls6l_final_confirmation_ready: {result['next_phase']['requires_ls6l_final_confirmation_ready']}",
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
    parser.add_argument("--policy", default="config/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.template.json")
    parser.add_argument("--confirmation", default="exchange/human_review/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation.json")
    parser.add_argument("--ls6k-result", default="exchange/logs/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_result.json")
    parser.add_argument("--runtime-freeze-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_runtime_freeze_plan.json")
    parser.add_argument("--credential-boundary-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_credential_env_read_boundary_plan.json")
    parser.add_argument("--actual-execution-lock-plan", default="exchange/locks/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_lock_plan.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6j-command", default="exchange/human_review/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6h-approved-result", default="exchange/logs/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_approved_result.json")
    parser.add_argument("--ls6g-result", default="exchange/logs/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_not_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_not_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    template = load_json(Path(args.template))
    ls6k_result = load_json(Path(args.ls6k_result))
    runtime_freeze_plan = load_json(Path(args.runtime_freeze_plan))
    credential_boundary_plan = load_json(Path(args.credential_boundary_plan))
    execution_lock_plan = load_json(Path(args.actual_execution_lock_plan))
    ls6j_result = load_json(Path(args.ls6j_ready_result))
    ls6j_command = load_json(Path(args.ls6j_command))
    ls6i_result = load_json(Path(args.ls6i_validation_result))
    ls6h_result = load_json(Path(args.ls6h_approved_result))
    ls6g_result = load_json(Path(args.ls6g_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []
    validate_policy(policy, errors)
    validate_template(template, errors)
    ls6k_boundary_passed = validate_ls6k(ls6k_result, errors)
    runtime_freeze_plan_ready = validate_runtime_freeze_plan(runtime_freeze_plan, errors)
    credential_env_read_boundary_ready = validate_credential_boundary(credential_boundary_plan, errors)
    actual_execution_lock_plan_ready = validate_execution_lock_plan(execution_lock_plan, errors)
    validate_ls6j(ls6j_result, ls6j_command, errors)
    validate_ls6i(ls6i_result, errors)
    validate_ls6h(ls6h_result, errors)
    validate_ls6g(ls6g_result, errors)
    payload_ready, payload_title, payload_asin, payload_post_status, max_items = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls6b(ls6b_lock, errors)

    confirmation_path = Path(args.confirmation)
    actual_final_runtime_confirmation = False
    confirmation_label: str | None = None

    if errors:
        status = "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"
    elif args.allow_template:
        status = "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_TEMPLATE_PASS_NO_ACTUAL_CONFIRMATION"
        confirmation_label = "NOT_CONFIRMED_YET"
    elif not confirmation_path.exists():
        status = "LS6L_ACTUAL_RUNTIME_FREEZE_AND_CREDENTIAL_BOUNDARY_CONFIRMATION_NOT_READY"
    else:
        actual_confirmation = load_json(confirmation_path)
        confirmation_label = validate_actual_confirmation(actual_confirmation, errors)
        if errors:
            status = "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_GATE_NOT_READY"
        else:
            actual_final_runtime_confirmation = True
            status = "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION"

    result = build_result(
        status=status,
        actual_final_runtime_confirmation=actual_final_runtime_confirmation,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        max_items=max_items,
        ls6k_boundary_passed=ls6k_boundary_passed,
        runtime_freeze_plan_ready=runtime_freeze_plan_ready,
        credential_env_read_boundary_ready=credential_env_read_boundary_ready,
        actual_execution_lock_plan_ready=actual_execution_lock_plan_ready,
        confirmation_label=confirmation_label,
        errors=errors,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
