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
    require(policy.get("phase") == "LS-6G", "policy phase must be LS-6G", errors)
    require(policy.get("execution_mode") == "FINAL_PREFLIGHT_ONLY", "policy execution_mode must be FINAL_PREFLIGHT_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    preflight = policy.get("final_preflight_policy", {})
    require(preflight.get("final_preflight_only") is True, "policy final_preflight_only must be true", errors)
    require(preflight.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(preflight.get("wordpress_draft_creation_allowed_by_this_phase") is False, "policy wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(preflight.get("runner_execution_allowed_by_this_phase") is False, "policy runner_execution_allowed_by_this_phase must be false", errors)
    require(preflight.get("credential_env_read_allowed_by_this_phase") is False, "policy credential_env_read_allowed_by_this_phase must be false", errors)
    require(preflight.get("approval_label_consumed_by_this_phase") is False, "policy approval_label_consumed_by_this_phase must be false", errors)
    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6f(ls6f_plan: dict[str, Any], ls6f_result: dict[str, Any], errors: list[str]) -> tuple[bool, bool]:
    require(ls6f_plan.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F runner plan status mismatch", errors)
    require(ls6f_result.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F result status mismatch", errors)
    require(ls6f_plan.get("runner_plan_ready") is True, "LS-6F runner plan ready must be true", errors)
    require(ls6f_result.get("runner_plan_ready") is True, "LS-6F result runner_plan_ready must be true", errors)
    require(ls6f_plan.get("runner_execution_allowed") is False, "LS-6F plan runner_execution_allowed must be false", errors)
    require(ls6f_result.get("runner_execution_allowed") is False, "LS-6F result runner_execution_allowed must be false", errors)
    require(ls6f_plan.get("approval_label_consumed") is False, "LS-6F plan approval_label_consumed must be false", errors)
    require(ls6f_result.get("approval_label_consumed") is False, "LS-6F result approval_label_consumed must be false", errors)
    require(ls6f_plan.get("wordpress_write_allowed_by_this_phase") is False, "LS-6F plan wordpress_write_allowed_by_this_phase must be false", errors)
    require(ls6f_result.get("wordpress_write_allowed_by_this_phase") is False, "LS-6F result wordpress_write_allowed_by_this_phase must be false", errors)
    require(ls6f_plan.get("wordpress_draft_creation_allowed_by_this_phase") is False, "LS-6F plan wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(ls6f_result.get("wordpress_draft_creation_allowed_by_this_phase") is False, "LS-6F result wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(ls6f_plan.get("credential_env_read_executed") is False, "LS-6F plan credential_env_read_executed must be false", errors)
    require(ls6f_result.get("credential_env_read_executed") is False, "LS-6F result credential_env_read_executed must be false", errors)
    require(ls6f_plan.get("wordpress_api_call_executed") is False, "LS-6F plan wordpress_api_call_executed must be false", errors)
    require(ls6f_result.get("wordpress_api_call_executed") is False, "LS-6F result wordpress_api_call_executed must be false", errors)
    require(ls6f_plan.get("wordpress_write_executed") is False, "LS-6F plan wordpress_write_executed must be false", errors)
    require(ls6f_result.get("wordpress_write_executed") is False, "LS-6F result wordpress_write_executed must be false", errors)
    require(ls6f_plan.get("wordpress_draft_creation_executed") is False, "LS-6F plan wordpress_draft_creation_executed must be false", errors)
    require(ls6f_result.get("wordpress_draft_creation_executed") is False, "LS-6F result wordpress_draft_creation_executed must be false", errors)
    require(ls6f_plan.get("post119_update_executed") is False, "LS-6F plan post119_update_executed must be false", errors)
    require(ls6f_result.get("post119_update_executed") is False, "LS-6F result post119_update_executed must be false", errors)
    require(ls6f_plan.get("publish_executed") is False, "LS-6F plan publish_executed must be false", errors)
    require(ls6f_result.get("publish_executed") is False, "LS-6F result publish_executed must be false", errors)
    require(ls6f_plan.get("runner_executed") is False, "LS-6F plan runner_executed must be false", errors)
    require(ls6f_result.get("runner_executed") is False, "LS-6F result runner_executed must be false", errors)
    return bool(ls6f_plan.get("runner_plan_ready")), bool(ls6f_plan.get("runner_execution_allowed"))


def validate_ls6e(ls6e_result: dict[str, Any], ls6e_approval: dict[str, Any], errors: list[str]) -> tuple[bool, str]:
    require(ls6e_result.get("status") == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION", "LS-6E approved result status mismatch", errors)
    require(ls6e_result.get("actual_approval") is True, "LS-6E actual_approval must be true", errors)
    require(ls6e_result.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6E approval_label mismatch", errors)
    require(ls6e_result.get("approval_label_consumed") is False, "LS-6E result approval_label_consumed must be false", errors)
    require(ls6e_result.get("wordpress_write_allowed_by_this_phase") is False, "LS-6E result wordpress_write_allowed_by_this_phase must be false", errors)
    require(ls6e_result.get("wordpress_draft_creation_allowed_by_this_phase") is False, "LS-6E result wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(ls6e_approval.get("approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION", "LS-6E approval_status mismatch", errors)
    require(ls6e_approval.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6E approval file label mismatch", errors)
    return bool(ls6e_result.get("actual_approval")), str(ls6e_result.get("approval_label", ""))


def validate_ls6d(ls6d_result: dict[str, Any], ls6d_review: dict[str, Any], errors: list[str]) -> None:
    require(ls6d_result.get("status") == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION", "LS-6D result status mismatch", errors)
    require(ls6d_result.get("manual_publish_allowed") is False, "LS-6D manual_publish_allowed must be false", errors)
    require(ls6d_review.get("review_status") == "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD", "LS-6D review status mismatch", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str, str, str, int]:
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_payload.get("payload_ready") is True, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)

    title = ""
    asin = ""
    post_status = ""
    content_format = ""
    max_items = int(ls6c_payload.get("max_items", 0)) if isinstance(ls6c_payload.get("max_items"), int) else 0
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        post_status = str(item.get("post_status", ""))
        content_format = str(item.get("content_format", ""))
        asin = parse_asin(str(item.get("content", "")))
        require(post_status == "draft", "LS-6C post_status must be draft", errors)
        require(content_format == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
    return bool(ls6c_payload.get("payload_ready")), title, asin, post_status, content_format, max_items


def validate_ls7a(ls7a_result: dict[str, Any], ls7a_review: dict[str, Any], errors: list[str]) -> None:
    require(ls7a_result.get("status") == "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "LS-7A result status mismatch", errors)
    require(ls7a_result.get("publish_decision") == "DO_NOT_PUBLISH", "LS-7A publish_decision mismatch", errors)
    require(ls7a_result.get("requires_payload_rebuild") is True, "LS-7A requires_payload_rebuild must be true", errors)
    require(ls7a_result.get("manual_publish_allowed") is False, "LS-7A manual_publish_allowed must be false", errors)
    require(ls7a_review.get("review_status") == "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "LS-7A review status mismatch", errors)


def validate_ls6b(ls6b_result: dict[str, Any], ls6b_validation: dict[str, Any], ls6b_lock: dict[str, Any], errors: list[str]) -> None:
    require(ls6b_result.get("status") == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN", "LS-6B result status mismatch", errors)
    validation_status = ls6b_validation.get("validation_status") or ls6b_validation.get("status")
    require(validation_status == "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED", "LS-6B validation status mismatch", errors)
    require(ls6b_lock.get("locked") is True, "LS-6B lock.locked must be true", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B lock.rerun_allowed must be false", errors)


def build_result(
    *,
    status: str,
    final_preflight_passed: bool,
    execution_allowed: bool,
    payload_ready: bool,
    payload_title: str,
    payload_asin: str,
    payload_post_status: str,
    payload_content_format: str,
    max_items: int,
    runner_plan_ready: bool,
    runner_execution_allowed: bool,
    actual_approval: bool,
    approval_label: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6G",
        "status": status,
        "execution_mode": "FINAL_PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "final_preflight_passed": final_preflight_passed,
        "execution_allowed": execution_allowed,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "payload_content_format": payload_content_format,
        "max_items": max_items,
        "runner_plan_ready": runner_plan_ready,
        "runner_execution_allowed": runner_execution_allowed,
        "actual_approval": actual_approval,
        "approval_label": approval_label,
        "approval_label_consumed": False,
        "manual_publish_allowed": False,
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
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "runner_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6H",
            "execution_allowed": False,
            "requires_separate_execute_approval": True,
            "requires_final_preflight_pass": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6G Real Payload One-shot Draft Creation Final Preflight Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- final_preflight_passed: {result['final_preflight_passed']}",
        f"- execution_allowed: {result['execution_allowed']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- payload_content_format: {result['payload_content_format']}",
        f"- max_items: {result['max_items']}",
        f"- runner_plan_ready: {result['runner_plan_ready']}",
        f"- runner_execution_allowed: {result['runner_execution_allowed']}",
        f"- actual_approval: {result['actual_approval']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        "- LS-6H: Real Payload One-shot Draft Creation Execute Approval Gate",
        "- execution_allowed: False",
        "- requires_separate_execute_approval: True",
        "- requires_final_preflight_pass: True",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_policy.json")
    parser.add_argument("--ls6f-runner-plan", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_plan.json")
    parser.add_argument("--ls6f-result", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_prep_result.json")
    parser.add_argument("--ls6e-approved-result", default="exchange/logs/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_approved_result.json")
    parser.add_argument("--ls6e-approval", default="exchange/human_review/start_ls6e_real_payload_one_shot_draft_creation_approval.json")
    parser.add_argument("--ls6d-result", default="exchange/logs/start_ls6d_real_payload_human_review_gate_passed_result.json")
    parser.add_argument("--ls6d-review", default="exchange/human_review/start_ls6d_real_payload_human_review.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls7a-result", default="exchange/logs/start_ls7a_human_review_result_evidence_result.json")
    parser.add_argument("--ls7a-review", default="exchange/human_review/start_ls7a_post119_human_review_decision.json")
    parser.add_argument("--ls6b-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6b-validation-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    ls6f_plan = load_json(Path(args.ls6f_runner_plan))
    ls6f_result = load_json(Path(args.ls6f_result))
    ls6e_result = load_json(Path(args.ls6e_approved_result))
    ls6e_approval = load_json(Path(args.ls6e_approval))
    ls6d_result = load_json(Path(args.ls6d_result))
    ls6d_review = load_json(Path(args.ls6d_review))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls7a_result = load_json(Path(args.ls7a_result))
    ls7a_review = load_json(Path(args.ls7a_review))
    ls6b_result = load_json(Path(args.ls6b_result))
    ls6b_validation = load_json(Path(args.ls6b_validation_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []
    validate_policy(policy, errors)
    runner_plan_ready, runner_execution_allowed = validate_ls6f(ls6f_plan, ls6f_result, errors)
    actual_approval, approval_label = validate_ls6e(ls6e_result, ls6e_approval, errors)
    validate_ls6d(ls6d_result, ls6d_review, errors)
    payload_ready, payload_title, payload_asin, payload_post_status, payload_content_format, max_items = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_ls6b(ls6b_result, ls6b_validation, ls6b_lock, errors)

    status = "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION" if not errors else "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_NOT_READY"
    result = build_result(
        status=status,
        final_preflight_passed=not errors,
        execution_allowed=False,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        payload_content_format=payload_content_format,
        max_items=max_items,
        runner_plan_ready=runner_plan_ready,
        runner_execution_allowed=runner_execution_allowed,
        actual_approval=actual_approval,
        approval_label=approval_label,
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
