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


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6K", "policy phase must be LS-6K", errors)
    require(policy.get("execution_mode") == "FINAL_RUNNER_BOUNDARY_PREFLIGHT_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    boundary = policy.get("final_runner_boundary_policy", {})
    require(boundary.get("final_runner_boundary_only") is True, "policy final_runner_boundary_only must be true", errors)
    require(boundary.get("actual_execution_allowed_by_this_phase") is False, "policy actual_execution_allowed_by_this_phase must be false", errors)
    require(boundary.get("wordpress_api_call_allowed_by_this_phase") is False, "policy wordpress_api_call_allowed_by_this_phase must be false", errors)
    require(boundary.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(boundary.get("wordpress_draft_creation_allowed_by_this_phase") is False, "policy wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(boundary.get("credential_env_read_allowed_by_this_phase") is False, "policy credential_env_read_allowed_by_this_phase must be false", errors)
    require(boundary.get("runtime_freeze_applied_by_this_phase") is False, "policy runtime_freeze_applied_by_this_phase must be false", errors)
    require(boundary.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "policy one_shot_actual_execution_lock_consumed_by_this_phase must be false", errors)
    require(boundary.get("separate_execution_command_consumed_by_this_phase") is False, "policy separate_execution_command_consumed_by_this_phase must be false", errors)

    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6j(ls6j_result: dict[str, Any], ls6j_command: dict[str, Any], errors: list[str]) -> bool:
    require(ls6j_result.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    ready = ls6j_result.get("actual_separate_execution_command") is True
    require(ready, "LS-6J actual_separate_execution_command must be true", errors)
    require(ls6j_result.get("command_label") == "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6J command_label mismatch", errors)
    require(ls6j_result.get("separate_execution_command_consumed") is False, "LS-6J separate_execution_command_consumed must be false", errors)
    require(ls6j_result.get("actual_execution_allowed") is False, "LS-6J actual_execution_allowed must be false", errors)
    require(ls6j_result.get("next_phase", {}).get("execution_allowed") is False, "LS-6J next_phase.execution_allowed must be false", errors)

    require(ls6j_command.get("command_status") == "HUMAN_CONFIRMED_SEPARATE_EXECUTION_COMMAND_FOR_ONE_SHOT_DRAFT_CREATION", "LS-6J command command_status mismatch", errors)
    require(ls6j_command.get("command_label") == "SEPARATE_EXECUTION_COMMAND_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6J command command_label mismatch", errors)
    return ready


def validate_ls6i(ls6i_preflight: dict[str, Any], ls6i_validation: dict[str, Any], errors: list[str]) -> tuple[bool, bool, bool]:
    require(ls6i_preflight.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I preflight status mismatch", errors)
    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I validation status mismatch", errors)
    runner_implemented = ls6i_validation.get("runner_implemented") is True
    runner_preflight_passed = ls6i_validation.get("runner_preflight_passed") is True
    runner_validated = ls6i_validation.get("runner_preflight_passed") is True

    require(runner_implemented, "LS-6I runner_implemented must be true", errors)
    require(runner_preflight_passed, "LS-6I runner_preflight_passed must be true", errors)
    require(ls6i_validation.get("actual_execution_allowed") is False, "LS-6I actual_execution_allowed must be false", errors)
    require(ls6i_validation.get("runner_executed") is False, "LS-6I runner_executed must be false", errors)
    require(ls6i_validation.get("actual_execution_executed") is False, "LS-6I actual_execution_executed must be false", errors)

    return runner_implemented, runner_preflight_passed, runner_validated


def validate_ls6h(ls6h_result: dict[str, Any], ls6h_approval: dict[str, Any], errors: list[str]) -> None:
    require(ls6h_result.get("status") == "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION", "LS-6H status mismatch", errors)
    require(ls6h_result.get("actual_execute_approval") is True, "LS-6H actual_execute_approval must be true", errors)
    require(ls6h_result.get("execute_approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY", "LS-6H execute_approval_label mismatch", errors)
    require(ls6h_result.get("execute_approval_label_consumed") is False, "LS-6H execute_approval_label_consumed must be false", errors)
    require(ls6h_approval.get("execute_approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE", "LS-6H approval execute_approval_status mismatch", errors)


def validate_ls6g(ls6g_result: dict[str, Any], errors: list[str]) -> None:
    require(ls6g_result.get("status") == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6G status mismatch", errors)
    require(ls6g_result.get("final_preflight_passed") is True, "LS-6G final_preflight_passed must be true", errors)
    require(ls6g_result.get("execution_allowed") is False, "LS-6G execution_allowed must be false", errors)


def validate_ls6f(ls6f_plan: dict[str, Any], ls6f_result: dict[str, Any], errors: list[str]) -> None:
    require(ls6f_plan.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F plan status mismatch", errors)
    require(ls6f_result.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F result status mismatch", errors)
    require(ls6f_plan.get("runner_plan_ready") is True, "LS-6F plan runner_plan_ready must be true", errors)
    require(ls6f_result.get("runner_plan_ready") is True, "LS-6F result runner_plan_ready must be true", errors)
    require(ls6f_plan.get("runner_execution_allowed") is False, "LS-6F plan runner_execution_allowed must be false", errors)
    require(ls6f_result.get("runner_execution_allowed") is False, "LS-6F result runner_execution_allowed must be false", errors)
    require(ls6f_plan.get("runner_executed") is False, "LS-6F plan runner_executed must be false", errors)
    require(ls6f_result.get("runner_executed") is False, "LS-6F result runner_executed must be false", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str, str]:
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    payload_ready = ls6c_payload.get("payload_ready") is True
    require(payload_ready, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)

    title = ""
    asin = ""
    post_status = ""
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        asin = parse_asin(str(item.get("content", "")))
        post_status = str(item.get("post_status", ""))
        require(item.get("content_format") == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)
        require(post_status == "draft", "LS-6C post_status must be draft", errors)
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)

    return payload_ready, title, asin, post_status


def validate_ls7a(ls7a_result: dict[str, Any], ls7a_review: dict[str, Any], errors: list[str]) -> None:
    require(ls7a_result.get("status") == "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "LS-7A status mismatch", errors)
    require(ls7a_result.get("publish_decision") == "DO_NOT_PUBLISH", "LS-7A publish_decision mismatch", errors)
    require(ls7a_result.get("requires_payload_rebuild") is True, "LS-7A requires_payload_rebuild must be true", errors)
    require(ls7a_result.get("manual_publish_allowed") is False, "LS-7A manual_publish_allowed must be false", errors)
    require(ls7a_review.get("review_status") == "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "LS-7A review status mismatch", errors)


def validate_ls6b(ls6b_result: dict[str, Any], ls6b_validation: dict[str, Any], ls6b_lock: dict[str, Any], errors: list[str]) -> None:
    require(ls6b_result.get("status") == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN", "LS-6B status mismatch", errors)
    validation_status = ls6b_validation.get("validation_status") or ls6b_validation.get("status")
    require(validation_status == "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED", "LS-6B validation status mismatch", errors)
    require(ls6b_lock.get("locked") is True, "LS-6B lock.locked must be true", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B lock.rerun_allowed must be false", errors)


def validate_runtime_freeze_plan(plan: dict[str, Any], errors: list[str]) -> bool:
    require(plan.get("status") == "RUNTIME_FREEZE_PLAN_DEFINED_NO_EXECUTION", "runtime freeze plan status mismatch", errors)
    require(plan.get("runtime_freeze_required") is True, "runtime freeze plan runtime_freeze_required must be true", errors)
    require(plan.get("runtime_freeze_applied_by_this_phase") is False, "runtime freeze plan runtime_freeze_applied_by_this_phase must be false", errors)
    require(plan.get("runtime_freeze_restored_by_this_phase") is False, "runtime freeze plan runtime_freeze_restored_by_this_phase must be false", errors)
    for key, value in plan.get("current_phase_execution", {}).items():
        require(value is False, f"runtime freeze plan current_phase_execution.{key} must be false", errors)
    return True


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

    for key, value in plan.get("current_phase_execution", {}).items():
        require(value is False, f"credential boundary current_phase_execution.{key} must be false", errors)
    return True


def validate_execution_lock_plan(plan: dict[str, Any], errors: list[str]) -> bool:
    require(plan.get("status") == "ONE_SHOT_ACTUAL_EXECUTION_LOCK_PLAN_DEFINED_NO_CONSUMPTION", "actual execution lock plan status mismatch", errors)
    require(plan.get("one_shot_actual_execution_lock_required") is True, "actual execution lock plan required must be true", errors)
    require(plan.get("one_shot_actual_execution_lock_created_by_this_phase") is False, "actual execution lock plan created_by_this_phase must be false", errors)
    require(plan.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "actual execution lock plan consumed_by_this_phase must be false", errors)
    require(plan.get("rerun_allowed") is False, "actual execution lock plan rerun_allowed must be false", errors)
    for key, value in plan.get("current_phase_execution", {}).items():
        require(value is False, f"actual execution lock plan current_phase_execution.{key} must be false", errors)
    return True


def build_result(*, status: str, payload_ready: bool, payload_title: str, payload_asin: str, payload_post_status: str, ls6j_command_ready: bool, runner_implemented: bool, runner_preflight_passed: bool, runner_validated: bool, runtime_freeze_plan_ready: bool, credential_env_read_boundary_ready: bool, actual_execution_lock_plan_ready: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6K",
        "status": status,
        "execution_mode": "FINAL_RUNNER_BOUNDARY_PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": 1,
        "ls6j_command_ready": ls6j_command_ready,
        "separate_execution_command_consumed": False,
        "runner_implemented": runner_implemented,
        "runner_preflight_passed": runner_preflight_passed,
        "runner_validated": runner_validated,
        "runtime_freeze_plan_ready": runtime_freeze_plan_ready,
        "runtime_freeze_applied": False,
        "runtime_freeze_restored": False,
        "credential_env_read_boundary_ready": credential_env_read_boundary_ready,
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "actual_execution_lock_plan_ready": actual_execution_lock_plan_ready,
        "one_shot_actual_execution_lock_consumed": False,
        "actual_execution_allowed": False,
        "manual_publish_allowed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "execute_approval_label_consumed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6L",
            "execution_allowed": False,
            "requires_ls6k_boundary_pass": True,
            "requires_human_final_runtime_confirmation": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6K Actual Execution Final Runner Boundary Preflight Report",
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
        f"- ls6j_command_ready: {result['ls6j_command_ready']}",
        f"- separate_execution_command_consumed: {result['separate_execution_command_consumed']}",
        f"- runner_implemented: {result['runner_implemented']}",
        f"- runner_preflight_passed: {result['runner_preflight_passed']}",
        f"- runner_validated: {result['runner_validated']}",
        f"- runtime_freeze_plan_ready: {result['runtime_freeze_plan_ready']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- credential_env_read_boundary_ready: {result['credential_env_read_boundary_ready']}",
        f"- credential_env_read_allowed_by_this_phase: {result['credential_env_read_allowed_by_this_phase']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- actual_execution_lock_plan_ready: {result['actual_execution_lock_plan_ready']}",
        f"- one_shot_actual_execution_lock_consumed: {result['one_shot_actual_execution_lock_consumed']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- wordpress_api_call_allowed_by_this_phase: {result['wordpress_api_call_allowed_by_this_phase']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- future_schedule_executed: {result['future_schedule_executed']}",
        f"- delete_executed: {result['delete_executed']}",
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
        f"- requires_ls6k_boundary_pass: {result['next_phase']['requires_ls6k_boundary_pass']}",
        f"- requires_human_final_runtime_confirmation: {result['next_phase']['requires_human_final_runtime_confirmation']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend([f"- {e}" for e in result["errors"]])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_policy.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6j-command", default="exchange/human_review/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command.json")
    parser.add_argument("--ls6i-preflight-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_preflight_result.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6h-approved-result", default="exchange/logs/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_approved_result.json")
    parser.add_argument("--ls6h-approval", default="exchange/human_review/start_ls6h_real_payload_one_shot_draft_creation_execute_approval.json")
    parser.add_argument("--ls6g-result", default="exchange/logs/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_result.json")
    parser.add_argument("--ls6f-runner-plan", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_plan.json")
    parser.add_argument("--ls6f-result", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_prep_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls7a-result", default="exchange/logs/start_ls7a_human_review_result_evidence_result.json")
    parser.add_argument("--ls7a-review", default="exchange/human_review/start_ls7a_post119_human_review_decision.json")
    parser.add_argument("--ls6b-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6b-validation-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--runtime-freeze-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_runtime_freeze_plan.json")
    parser.add_argument("--credential-boundary-plan", default="exchange/runtime/start_ls6k_real_payload_one_shot_draft_creation_credential_env_read_boundary_plan.json")
    parser.add_argument("--actual-execution-lock-plan", default="exchange/locks/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_lock_plan.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_result.json")
    parser.add_argument("--report", default="reports/start_ls6k_real_payload_one_shot_draft_creation_actual_execution_final_runner_boundary_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    ls6j_result = load_json(Path(args.ls6j_ready_result))
    ls6j_command = load_json(Path(args.ls6j_command))
    ls6i_preflight = load_json(Path(args.ls6i_preflight_result))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6h_result = load_json(Path(args.ls6h_approved_result))
    ls6h_approval = load_json(Path(args.ls6h_approval))
    ls6g_result = load_json(Path(args.ls6g_result))
    ls6f_plan = load_json(Path(args.ls6f_runner_plan))
    ls6f_result = load_json(Path(args.ls6f_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls7a_result = load_json(Path(args.ls7a_result))
    ls7a_review = load_json(Path(args.ls7a_review))
    ls6b_result = load_json(Path(args.ls6b_result))
    ls6b_validation = load_json(Path(args.ls6b_validation_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))
    runtime_freeze_plan = load_json(Path(args.runtime_freeze_plan))
    credential_boundary_plan = load_json(Path(args.credential_boundary_plan))
    execution_lock_plan = load_json(Path(args.actual_execution_lock_plan))

    errors: list[str] = []
    validate_policy(policy, errors)
    ls6j_ready = validate_ls6j(ls6j_result, ls6j_command, errors)
    runner_implemented, runner_preflight_passed, runner_validated = validate_ls6i(ls6i_preflight, ls6i_validation, errors)
    validate_ls6h(ls6h_result, ls6h_approval, errors)
    validate_ls6g(ls6g_result, errors)
    validate_ls6f(ls6f_plan, ls6f_result, errors)
    payload_ready, payload_title, payload_asin, payload_post_status = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_ls6b(ls6b_result, ls6b_validation, ls6b_lock, errors)
    runtime_freeze_plan_ready = validate_runtime_freeze_plan(runtime_freeze_plan, errors)
    credential_env_read_boundary_ready = validate_credential_boundary(credential_boundary_plan, errors)
    actual_execution_lock_plan_ready = validate_execution_lock_plan(execution_lock_plan, errors)

    status = "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_PASSED_NO_EXECUTION"
    if errors:
        status = "LS6K_ACTUAL_EXECUTION_FINAL_RUNNER_BOUNDARY_PREFLIGHT_NOT_READY"

    result = build_result(
        status=status,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        ls6j_command_ready=ls6j_ready,
        runner_implemented=runner_implemented,
        runner_preflight_passed=runner_preflight_passed,
        runner_validated=runner_validated,
        runtime_freeze_plan_ready=runtime_freeze_plan_ready,
        credential_env_read_boundary_ready=credential_env_read_boundary_ready,
        actual_execution_lock_plan_ready=actual_execution_lock_plan_ready,
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
