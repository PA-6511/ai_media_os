#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHECKLIST_KEYS = [
    "ls6c_payload_ready_checked",
    "ls6d_human_review_pass_checked",
    "target_title_checked",
    "target_asin_checked",
    "target_purchase_url_checked",
    "post_status_draft_checked",
    "max_items_one_checked",
    "no_existing_post_update_checked",
    "post119_not_target_checked",
    "publish_not_allowed_checked",
    "wordpress_write_not_allowed_in_this_phase_checked",
    "approval_label_not_consumed_in_this_phase_checked",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6E", "policy phase must be LS-6E", errors)
    require(policy.get("execution_mode") == "APPROVAL_GATE_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    ap = policy.get("approval_policy", {})
    require(ap.get("human_approval_required") is True, "policy human_approval_required must be true", errors)
    require(ap.get("auto_approval_allowed") is False, "policy auto_approval_allowed must be false", errors)
    require(ap.get("approval_label_consumed_by_this_phase") is False, "policy approval_label_consumed_by_this_phase must be false", errors)
    require(ap.get("wordpress_write_allowed_by_this_phase") is False, "policy wordpress_write_allowed_by_this_phase must be false", errors)
    require(ap.get("wordpress_draft_creation_allowed_by_this_phase") is False, "policy wordpress_draft_creation_allowed_by_this_phase must be false", errors)

    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6d(ls6d_result: dict[str, Any], ls6d_review: dict[str, Any], errors: list[str]) -> None:
    require(ls6d_result.get("status") == "LS6D_REAL_PAYLOAD_HUMAN_REVIEW_PASSED_NO_EXECUTION", "LS-6D result status mismatch", errors)
    require(ls6d_result.get("actual_review") is True, "LS-6D result actual_review must be true", errors)
    require(ls6d_result.get("payload_ready") is True, "LS-6D result payload_ready must be true", errors)
    require(ls6d_result.get("manual_publish_allowed") is False, "LS-6D result manual_publish_allowed must be false", errors)
    require(ls6d_result.get("wordpress_write_allowed_by_this_phase") is False, "LS-6D result wordpress_write_allowed_by_this_phase must be false", errors)

    require(ls6d_review.get("review_status") == "HUMAN_REVIEW_PASSED_FOR_REAL_DRAFT_PAYLOAD", "LS-6D review status mismatch", errors)
    for key in [
        "title_checked",
        "author_checked",
        "volume_checked",
        "release_date_checked",
        "asin_and_purchase_url_checked",
        "affiliate_tag_checked",
        "japanese_pr_disclosure_checked",
        "html_link_checked",
        "markdown_link_absent_checked",
        "category_and_tags_checked",
        "summary_not_raw_copy_checked",
        "no_sample_content_checked",
        "wordpress_write_not_allowed_in_this_phase_checked",
    ]:
        require(ls6d_review.get("review_checklist", {}).get(key) is True, f"LS-6D review checklist {key} must be true", errors)

    decision = ls6d_review.get("decision", {})
    require(decision.get("human_review_passed") is True, "LS-6D decision.human_review_passed must be true", errors)
    require(decision.get("manual_publish_allowed") is False, "LS-6D decision.manual_publish_allowed must be false", errors)
    require(decision.get("wordpress_write_allowed_next_phase") is False, "LS-6D decision.wordpress_write_allowed_next_phase must be false", errors)
    require(decision.get("requires_payload_fix") is False, "LS-6D decision.requires_payload_fix must be false", errors)


def validate_ls6c(ls6c_payload: dict[str, Any], ls6c_result: dict[str, Any], errors: list[str]) -> tuple[bool, str, str, str]:
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)

    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_payload.get("payload_ready") is True, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)

    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)

    payload_title = ""
    payload_asin = ""
    payload_post_status = ""

    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        payload_title = str(item.get("title", ""))
        payload_post_status = str(item.get("post_status", ""))
        payload_asin = ""
        content = str(item.get("content", ""))
        if "amazon.co.jp/dp/" in content:
            payload_asin = content.split("amazon.co.jp/dp/")[1].split("?")[0].split('"')[0]

        require(item.get("post_status") == "draft", "LS-6C post_status must be draft", errors)
        require(item.get("content_format") == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)
        require(item.get("title") == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(payload_asin == "B07X2G67B4", "LS-6C asin mismatch", errors)

    for key in [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "wordpress_existing_post_update_executed",
        "post119_update_executed",
        "publish_executed",
        "approval_token_consumed",
        "ls6b_rerun_executed",
    ]:
        if key in ls6c_payload:
            require(ls6c_payload.get(key) is False, f"LS-6C payload {key} must be false", errors)

    return (ls6c_payload.get("payload_ready") is True, payload_title, payload_asin, payload_post_status)


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


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("approval_status") == "TEMPLATE_NOT_ACTUAL_APPROVAL", "template approval_status mismatch", errors)


def validate_actual_approval(approval: dict[str, Any], errors: list[str]) -> str:
    status = str(approval.get("approval_status", ""))
    if status == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION":
        require(approval.get("approval_label") == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_ONLY", "approval_label mismatch", errors)
        for key in CHECKLIST_KEYS:
            require(approval.get("approval_checklist", {}).get(key) is True, f"approval_checklist.{key} must be true", errors)
        decision = approval.get("decision", {})
        require(decision.get("human_approval_granted") is True, "decision.human_approval_granted must be true", errors)
        require(decision.get("approval_label_consumed") is False, "decision.approval_label_consumed must be false", errors)
        require(decision.get("wordpress_write_allowed_by_this_phase") is False, "decision.wordpress_write_allowed_by_this_phase must be false", errors)
        require(decision.get("wordpress_draft_creation_allowed_by_this_phase") is False, "decision.wordpress_draft_creation_allowed_by_this_phase must be false", errors)
        require(decision.get("manual_publish_allowed") is False, "decision.manual_publish_allowed must be false", errors)
        require(decision.get("requires_runner_preflight") is True, "decision.requires_runner_preflight must be true", errors)
        require(
            approval.get("human_confirmation_text")
            == "I explicitly approve the reviewed LS-6C real payload for the next runner-preparation phase only. This does not authorize WordPress write, publish, update, or deletion in LS-6E.",
            "human_confirmation_text mismatch",
            errors,
        )
    elif status == "HUMAN_DENIED_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION":
        pass
    else:
        errors.append("approval_status must be HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION or HUMAN_DENIED_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION")

    for key, value in approval.get("current_phase_execution", {}).items():
        require(value is False, f"approval current_phase_execution.{key} must be false", errors)
    return status


def build_result(
    *,
    status: str,
    actual_approval: bool,
    payload_ready: bool,
    payload_title: str,
    payload_asin: str,
    payload_post_status: str,
    approval_label: str,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6E",
        "status": status,
        "execution_mode": "APPROVAL_GATE_ONLY",
        "production_status": "NO_GO",
        "actual_approval": actual_approval,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
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
        "approval_token_consumed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6F",
            "execution_allowed": False,
            "requires_actual_human_approval": True,
            "requires_runner_preflight": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6E Real Payload One-shot Draft Creation Approval Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- actual_approval: {result['actual_approval']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        "- LS-6F: Real Payload One-shot Draft Creation Runner PREP",
        "- execution_allowed: False",
        "- requires_actual_human_approval: True",
        "- requires_runner_preflight: True",
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
    parser.add_argument("--policy", default="config/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_policy.json")
    parser.add_argument("--approval", default="exchange/human_review/start_ls6e_real_payload_one_shot_draft_creation_approval.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6e_real_payload_one_shot_draft_creation_approval.template.json")
    parser.add_argument("--ls6d-result", default="exchange/logs/start_ls6d_real_payload_human_review_gate_passed_result.json")
    parser.add_argument("--ls6d-review", default="exchange/human_review/start_ls6d_real_payload_human_review.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls7a-result", default="exchange/logs/start_ls7a_human_review_result_evidence_result.json")
    parser.add_argument("--ls7a-review", default="exchange/human_review/start_ls7a_post119_human_review_decision.json")
    parser.add_argument("--ls6b-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6b-validation-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6e_real_payload_one_shot_draft_creation_approval_gate_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    template = load_json(Path(args.template))
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
    validate_ls6d(ls6d_result, ls6d_review, errors)
    payload_ready, payload_title, payload_asin, payload_post_status = validate_ls6c(ls6c_payload, ls6c_result, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_ls6b(ls6b_result, ls6b_validation, ls6b_lock, errors)
    validate_template(template, errors)

    approval_path = Path(args.approval)

    if args.allow_template:
        status = "LS6E_APPROVAL_TEMPLATE_PASS_NO_ACTUAL_APPROVAL" if not errors else "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"
        result = build_result(
            status=status,
            actual_approval=False,
            payload_ready=payload_ready,
            payload_title=payload_title,
            payload_asin=payload_asin,
            payload_post_status=payload_post_status,
            approval_label="NOT_APPROVED_YET",
            errors=errors,
        )
    else:
        if not approval_path.exists():
            status = "LS6E_ACTUAL_HUMAN_APPROVAL_NOT_READY" if not errors else "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"
            errs = list(errors)
            errs.append(f"actual approval file not found: {approval_path}")
            result = build_result(
                status=status,
                actual_approval=False,
                payload_ready=payload_ready,
                payload_title=payload_title,
                payload_asin=payload_asin,
                payload_post_status=payload_post_status,
                approval_label="NOT_APPROVED_YET",
                errors=errs,
            )
        else:
            approval = load_json(approval_path)
            eval_errors = list(errors)
            approval_status = validate_actual_approval(approval, eval_errors)

            if eval_errors:
                status = "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_GATE_NOT_READY"
            elif approval_status == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION":
                status = "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVED_NO_EXECUTION"
            else:
                status = "LS6E_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_APPROVAL_DENIED"

            result = build_result(
                status=status,
                actual_approval=True,
                payload_ready=payload_ready,
                payload_title=payload_title,
                payload_asin=payload_asin,
                payload_post_status=payload_post_status,
                approval_label=str(approval.get("approval_label", "NOT_APPROVED_YET")),
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
