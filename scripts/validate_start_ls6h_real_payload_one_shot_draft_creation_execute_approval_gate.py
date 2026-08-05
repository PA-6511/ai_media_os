#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHECKLIST_KEYS = [
    "ls6g_final_preflight_pass_checked",
    "ls6f_runner_prep_ready_checked",
    "ls6e_approval_pass_checked",
    "ls6d_human_review_pass_checked",
    "ls6c_payload_ready_checked",
    "target_title_checked",
    "target_asin_checked",
    "target_purchase_url_checked",
    "post_status_draft_checked",
    "max_items_one_checked",
    "create_new_draft_only_checked",
    "no_existing_post_update_checked",
    "post119_not_target_checked",
    "publish_not_allowed_checked",
    "schedule_not_allowed_checked",
    "approval_label_not_consumed_in_this_phase_checked",
    "wordpress_write_not_allowed_in_this_phase_checked",
]


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
    require(policy.get("phase") == "LS-6H", "policy phase must be LS-6H", errors)
    require(policy.get("execution_mode") == "EXECUTE_APPROVAL_GATE_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)
    approval_policy = policy.get("execute_approval_policy", {})
    require(approval_policy.get("human_execute_approval_required") is True, "policy human_execute_approval_required must be true", errors)
    require(approval_policy.get("auto_execute_approval_allowed") is False, "policy auto_execute_approval_allowed must be false", errors)
    require(approval_policy.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(approval_policy.get("wordpress_draft_creation_allowed_by_this_phase") is False, "policy wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(approval_policy.get("runner_execution_allowed_by_this_phase") is False, "policy runner_execution_allowed_by_this_phase must be false", errors)
    require(approval_policy.get("credential_env_read_allowed_by_this_phase") is False, "policy credential_env_read_allowed_by_this_phase must be false", errors)
    require(approval_policy.get("execute_approval_label_consumed_by_this_phase") is False, "policy execute_approval_label_consumed_by_this_phase must be false", errors)
    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6g(ls6g_result: dict[str, Any], errors: list[str]) -> bool:
    require(ls6g_result.get("status") == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6G result status mismatch", errors)
    require(ls6g_result.get("final_preflight_passed") is True, "LS-6G final_preflight_passed must be true", errors)
    require(ls6g_result.get("execution_allowed") is False, "LS-6G execution_allowed must be false", errors)
    return bool(ls6g_result.get("final_preflight_passed"))


def validate_ls6f(ls6f_plan: dict[str, Any], ls6f_result: dict[str, Any], errors: list[str]) -> None:
    require(ls6f_plan.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F runner plan status mismatch", errors)
    require(ls6f_result.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F result status mismatch", errors)
    require(ls6f_plan.get("runner_plan_ready") is True, "LS-6F plan runner_plan_ready must be true", errors)
    require(ls6f_result.get("runner_plan_ready") is True, "LS-6F result runner_plan_ready must be true", errors)
    require(ls6f_plan.get("runner_execution_allowed") is False, "LS-6F plan runner_execution_allowed must be false", errors)
    require(ls6f_result.get("runner_execution_allowed") is False, "LS-6F result runner_execution_allowed must be false", errors)
    require(ls6f_plan.get("runner_executed") is False, "LS-6F plan runner_executed must be false", errors)
    require(ls6f_result.get("runner_executed") is False, "LS-6F result runner_executed must be false", errors)


def validate_ls6e(ls6e_result: dict[str, Any], ls6e_approval: dict[str, Any], errors: list[str]) -> tuple[bool, str]:
    require(ls6e_result.get("status") == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION", "LS-6E approved result status mismatch", errors)
    require(ls6e_result.get("actual_approval") is True, "LS-6E actual_approval must be true", errors)
    require(ls6e_result.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6E approval_label mismatch", errors)
    require(ls6e_result.get("approval_label_consumed") is False, "LS-6E approval_label_consumed must be false", errors)
    require(ls6e_approval.get("approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION", "LS-6E approval status mismatch", errors)
    return bool(ls6e_result.get("actual_approval")), str(ls6e_result.get("approval_label", ""))


def validate_ls6d(ls6d_result: dict[str, Any], ls6d_review: dict[str, Any], errors: list[str]) -> None:
    require(ls6d_result.get("status") == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION", "LS-6D result status mismatch", errors)
    require(ls6d_result.get("manual_publish_allowed") is False, "LS-6D manual_publish_allowed must be false", errors)
    require(ls6d_review.get("review_status") == "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD", "LS-6D review status mismatch", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str, str]:
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
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        asin = parse_asin(str(item.get("content", "")))
        post_status = str(item.get("post_status", ""))
        require(post_status == "draft", "LS-6C post_status must be draft", errors)
        require(item.get("content_format") == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
    return bool(ls6c_payload.get("payload_ready")), title, asin, post_status


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


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("execute_approval_status") == "TEMPLATE_NOT_ACTUAL_EXECUTE_APPROVAL", "template execute_approval_status mismatch", errors)


def validate_actual_execute_approval(approval: dict[str, Any], errors: list[str]) -> str:
    status = str(approval.get("execute_approval_status", ""))
    if status == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE":
        require(approval.get("execute_approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY", "execute_approval_label mismatch", errors)
        for key in CHECKLIST_KEYS:
            require(approval.get("execute_approval_checklist", {}).get(key) is True, f"execute_approval_checklist.{key} must be true", errors)
        decision = approval.get("decision", {})
        require(decision.get("human_execute_approval_granted") is True, "decision.human_execute_approval_granted must be true", errors)
        require(decision.get("execute_approval_label_consumed") is False, "decision.execute_approval_label_consumed must be false", errors)
        require(decision.get("wordpress_write_allowed_by_this_phase") is False, "decision.wordpress_write_allowed_by_this_phase must be false", errors)
        require(decision.get("wordpress_draft_creation_allowed_by_this_phase") is False, "decision.wordpress_draft_creation_allowed_by_this_phase must be false", errors)
        require(decision.get("runner_execution_allowed_by_this_phase") is False, "decision.runner_execution_allowed_by_this_phase must be false", errors)
        require(decision.get("credential_env_read_allowed_by_this_phase") is False, "decision.credential_env_read_allowed_by_this_phase must be false", errors)
        require(decision.get("manual_publish_allowed") is False, "decision.manual_publish_allowed must be false", errors)
        require(decision.get("requires_separate_execution_command") is True, "decision.requires_separate_execution_command must be true", errors)
        require(
            approval.get("human_confirmation_text")
            == "I explicitly approve the reviewed, approved, and final-preflight-passed LS-6C real payload for one future WordPress draft creation execution only. This does not authorize publish, update, schedule, deletion, or any repeated execution.",
            "human_confirmation_text mismatch",
            errors,
        )
    elif status == "HUMAN_DENIED_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE":
        pass
    else:
        errors.append("execute_approval_status must be HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE or HUMAN_DENIED_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE")

    for key, value in approval.get("current_phase_execution", {}).items():
        require(value is False, f"approval current_phase_execution.{key} must be false", errors)
    return status


def build_result(*, status: str, actual_execute_approval: bool, payload_ready: bool, payload_title: str, payload_asin: str, payload_post_status: str, final_preflight_passed: bool, execute_approval_label: str, errors: list[str]) -> dict[str, Any]:
    next_phase = {
        "phase": "LS-6I",
        "execution_allowed": False,
        "requires_execute_approval": True,
        "requires_separate_execution_command": True,
    }
    if status == "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION":
        next_phase["requires_one_shot_execution_runner"] = True
    return {
        "phase": "LS-6H",
        "status": status,
        "execution_mode": "EXECUTE_APPROVAL_GATE_ONLY",
        "production_status": "NO_GO",
        "actual_execute_approval": actual_execute_approval,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "final_preflight_passed": final_preflight_passed,
        "execute_approval_label": execute_approval_label,
        "execute_approval_label_consumed": False,
        "manual_publish_allowed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "runner_execution_allowed_by_this_phase": False,
        "credential_env_read_allowed_by_this_phase": False,
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
        "approval_label_consumed": False,
        "runner_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": next_phase,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6H Real Payload One-shot Draft Creation Execute Approval Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- actual_execute_approval: {result['actual_execute_approval']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- final_preflight_passed: {result['final_preflight_passed']}",
        f"- execute_approval_label: {result['execute_approval_label']}",
        f"- execute_approval_label_consumed: {result['execute_approval_label_consumed']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- runner_execution_allowed_by_this_phase: {result['runner_execution_allowed_by_this_phase']}",
        f"- credential_env_read_allowed_by_this_phase: {result['credential_env_read_allowed_by_this_phase']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_execute_approval: {result['next_phase'].get('requires_execute_approval')}",
        f"- requires_separate_execution_command: {result['next_phase'].get('requires_separate_execution_command')}",
        f"- requires_one_shot_execution_runner: {result['next_phase'].get('requires_one_shot_execution_runner')}",
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
    parser.add_argument("--policy", default="config/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_policy.json")
    parser.add_argument("--execute-approval", default="exchange/human_review/start_ls6h_real_payload_one_shot_draft_creation_execute_approval.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6h_real_payload_one_shot_draft_creation_execute_approval.template.json")
    parser.add_argument("--ls6g-result", default="exchange/logs/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_result.json")
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
    parser.add_argument("--output", default="exchange/logs/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    policy = load_json(Path(args.policy))
    template = load_json(Path(args.template))
    ls6g_result = load_json(Path(args.ls6g_result))
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
    final_preflight_passed = validate_ls6g(ls6g_result, errors)
    validate_ls6f(ls6f_plan, ls6f_result, errors)
    actual_approval, _approval_label = validate_ls6e(ls6e_result, ls6e_approval, errors)
    validate_ls6d(ls6d_result, ls6d_review, errors)
    payload_ready, payload_title, payload_asin, payload_post_status = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_ls6b(ls6b_result, ls6b_validation, ls6b_lock, errors)
    validate_template(template, errors)

    execute_approval_path = Path(args.execute_approval)
    if args.allow_template:
        status = "LS6H_EXECUTE_APPROVAL_TEMPLATE_PASS_NO_ACTUAL_APPROVAL" if not errors else "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVAL_GATE_NOT_READY"
        result = build_result(
            status=status,
            actual_execute_approval=False,
            payload_ready=payload_ready,
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            final_preflight_passed=final_preflight_passed,
            execute_approval_label="NOT_APPROVED_YET",
            errors=errors,
        )
    else:
        if not execute_approval_path.exists():
            status = "LS6H_ACTUAL_EXECUTE_APPROVAL_NOT_READY" if not errors else "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVAL_GATE_NOT_READY"
            result = build_result(
                status=status,
                actual_execute_approval=False,
                payload_ready=payload_ready,
                payload_title=payload_title,
                payload_asin=payload_asin,
                payload_post_status=payload_post_status,
                final_preflight_passed=final_preflight_passed,
                execute_approval_label="NOT_APPROVED_YET",
                errors=errors,
            )
        else:
            approval = load_json(execute_approval_path)
            eval_errors = list(errors)
            approval_status = validate_actual_execute_approval(approval, eval_errors)
            if eval_errors:
                status = "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVAL_GATE_NOT_READY"
            elif approval_status == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE":
                status = "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION"
            else:
                status = "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_DENIED"
            result = build_result(
                status=status,
                actual_execute_approval=True,
                payload_ready=payload_ready,
                payload_title=payload_title,
                payload_asin=payload_asin,
                payload_post_status=payload_post_status,
                final_preflight_passed=final_preflight_passed,
                execute_approval_label=str(approval.get("execute_approval_label", "NOT_APPROVED_YET")),
                errors=eval_errors,
            )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
