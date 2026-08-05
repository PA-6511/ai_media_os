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
    if "amazon.co.jp/dp/" not in content:
        return ""
    return content.split("amazon.co.jp/dp/")[1].split("?")[0].split('"')[0]


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6F", "policy phase must be LS-6F", errors)
    require(policy.get("execution_mode") == "PREP_ONLY", "policy execution_mode must be PREP_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    prep = policy.get("runner_prep_policy", {})
    require(prep.get("runner_plan_only") is True, "policy runner_plan_only must be true", errors)
    require(prep.get("runner_execution_allowed_by_this_phase") is False, "policy runner_execution_allowed_by_this_phase must be false", errors)
    require(prep.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(prep.get("wordpress_draft_creation_allowed_by_this_phase") is False, "policy wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(prep.get("credential_env_read_allowed_by_this_phase") is False, "policy credential_env_read_allowed_by_this_phase must be false", errors)
    require(prep.get("approval_label_consumed_by_this_phase") is False, "policy approval_label_consumed_by_this_phase must be false", errors)

    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str]:
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_payload.get("payload_ready") is True, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)

    title = ""
    asin = ""
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        asin = parse_asin(str(item.get("content", "")))
        require(item.get("post_status") == "draft", "LS-6C post_status must be draft", errors)
        require(item.get("content_format") == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)
    return (ls6c_payload.get("payload_ready") is True, title, asin)


def validate_ls6d(ls6d_result: dict[str, Any], ls6d_review: dict[str, Any], errors: list[str]) -> None:
    require(ls6d_result.get("status") == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION", "LS-6D result status mismatch", errors)
    require(ls6d_review.get("review_status") == "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD", "LS-6D review status mismatch", errors)


def validate_ls7a(ls7a_result: dict[str, Any], ls7a_review: dict[str, Any], errors: list[str]) -> None:
    require(ls7a_result.get("status") == "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "LS-7A result status mismatch", errors)
    require(ls7a_result.get("publish_decision") == "DO_NOT_PUBLISH", "LS-7A publish_decision mismatch", errors)
    require(ls7a_result.get("requires_payload_rebuild") is True, "LS-7A requires_payload_rebuild must be true", errors)
    require(ls7a_review.get("review_status") == "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "LS-7A review status mismatch", errors)


def validate_ls6b(ls6b_result: dict[str, Any], ls6b_validation: dict[str, Any], ls6b_lock: dict[str, Any], errors: list[str]) -> None:
    require(ls6b_result.get("status") == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN", "LS-6B result status mismatch", errors)
    validation_status = ls6b_validation.get("validation_status") or ls6b_validation.get("status")
    require(validation_status == "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED", "LS-6B validation status mismatch", errors)
    require(ls6b_lock.get("locked") is True, "LS-6B lock.locked must be true", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B lock.rerun_allowed must be false", errors)


def validate_runner_plan_common(plan: dict[str, Any], errors: list[str]) -> None:
    require(plan.get("phase") == "LS-6F", "runner plan phase must be LS-6F", errors)
    require(plan.get("execution_mode") == "PREP_ONLY", "runner plan execution_mode must be PREP_ONLY", errors)
    require(plan.get("production_status") == "NO_GO", "runner plan production_status must be NO_GO", errors)

    for key in [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "post119_update_executed",
        "publish_executed",
        "credential_env_read_executed",
        "approval_token_consumed",
        "approval_label_consumed",
        "runner_executed",
    ]:
        require(plan.get(key) is False, f"runner plan {key} must be false", errors)


def validate_ls6e_ready(ls6e_approved: dict[str, Any], ls6e_approval: dict[str, Any], errors: list[str]) -> None:
    require(ls6e_approved.get("status") == "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION", "LS-6E approved result status mismatch", errors)
    require(ls6e_approval.get("approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION", "LS-6E approval_status mismatch", errors)
    require(ls6e_approval.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "LS-6E approval_label mismatch", errors)
    require(ls6e_approved.get("approval_label_consumed") is False, "LS-6E approved result approval_label_consumed must be false", errors)


def build_result(status: str, runner_plan: dict[str, Any], payload_ready: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6F",
        "status": status,
        "execution_mode": "PREP_ONLY",
        "production_status": "NO_GO",
        "runner_plan_ready": runner_plan.get("runner_plan_ready", False),
        "runner_execution_allowed": runner_plan.get("runner_execution_allowed", False),
        "payload_ready": payload_ready,
        "payload_title": runner_plan.get("payload_title", ""),
        "payload_asin": runner_plan.get("payload_asin", ""),
        "payload_post_status": runner_plan.get("payload_post_status", ""),
        "payload_content_format": runner_plan.get("payload_content_format", ""),
        "approval_label_consumed": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "credential_env_read_executed": False,
        "approval_token_consumed": False,
        "runner_executed": False,
        "next_phase": {
            "phase": "LS-6G",
            "execution_allowed": False,
            "requires_ls6e_actual_approval": True,
            "requires_final_preflight": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6F Real Payload One-shot Draft Runner PREP Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- runner_plan_ready: {result['runner_plan_ready']}",
        f"- runner_execution_allowed: {result['runner_execution_allowed']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result.get('payload_title', '')}",
        f"- payload_asin: {result.get('payload_asin', '')}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- runner_executed: {result['runner_executed']}",
        "",
        "## Next Phase",
        "- LS-6G: Real Payload One-shot Draft Creation Final Preflight Gate",
        "- execution_allowed: False",
        "- requires_ls6e_actual_approval: True",
        "- requires_final_preflight: True",
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
    parser.add_argument("--policy", default="config/start_ls6f_real_payload_one_shot_draft_runner_prep_policy.json")
    parser.add_argument("--runner-plan", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_plan.json")
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
    parser.add_argument("--output", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_prep_result.json")
    parser.add_argument("--report", default="reports/start_ls6f_real_payload_one_shot_draft_runner_prep_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    runner_plan = load_json(Path(args.runner_plan))
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
    payload_ready, payload_title, payload_asin = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls6d(ls6d_result, ls6d_review, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_ls6b(ls6b_result, ls6b_validation, ls6b_lock, errors)
    validate_runner_plan_common(runner_plan, errors)

    status = str(runner_plan.get("status", ""))
    if status == "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY":
        require(runner_plan.get("runner_plan_ready") is False, "blocked runner_plan_ready must be false", errors)
        require(runner_plan.get("runner_execution_allowed") is False, "blocked runner_execution_allowed must be false", errors)
        final_status = "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY_RECORDED"
    elif status == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION":
        ls6e_approved_path = Path(args.ls6e_approved_result)
        ls6e_approval_path = Path(args.ls6e_approval)
        if not ls6e_approved_path.exists() or not ls6e_approval_path.exists():
            errors.append("LS-6E ready artifacts are missing for READY runner plan")
        else:
            ls6e_approved = load_json(ls6e_approved_path)
            ls6e_approval = load_json(ls6e_approval_path)
            validate_ls6e_ready(ls6e_approved, ls6e_approval, errors)
        require(runner_plan.get("runner_plan_ready") is True, "ready runner_plan_ready must be true", errors)
        require(runner_plan.get("runner_execution_allowed") is False, "ready runner_execution_allowed must be false", errors)
        require(runner_plan.get("payload_title") == payload_title, "ready payload_title mismatch", errors)
        require(runner_plan.get("payload_asin") == payload_asin, "ready payload_asin mismatch", errors)
        final_status = "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION"
    else:
        errors.append("runner plan status must be BLOCKED or READY")
        final_status = "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"

    if errors:
        final_status = "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY" if status != "LS6F_BLOCKED_LS6E_ACTUAL_APPROVAL_NOT_READY" else "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_NOT_READY"

    result = build_result(final_status, runner_plan, payload_ready, errors)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
