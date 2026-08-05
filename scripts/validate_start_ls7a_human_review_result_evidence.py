#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_ISSUES = {
    "sample_title",
    "sample_author",
    "sample_asin_or_example_tag",
    "markdown_link_not_converted_to_html",
    "not_ready_as_real_product_article",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-7A", "policy phase must be LS-7A", errors)
    require(policy.get("status") == "HUMAN_REVIEW_EVIDENCE_ONLY", "policy status mismatch", errors)
    require(policy.get("execution_mode") == "REVIEW_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)
    require(policy.get("target_post", {}).get("post_id") == 119, "policy target_post.post_id must be 119", errors)
    require(policy.get("target_post", {}).get("expected_post_status") == "draft", "policy target_post.expected_post_status must be draft", errors)

    hr = policy.get("human_review_policy", {})
    require(hr.get("auto_publish_allowed") is False, "policy human_review_policy.auto_publish_allowed must be false", errors)
    require(hr.get("ai_publish_allowed") is False, "policy human_review_policy.ai_publish_allowed must be false", errors)
    require(hr.get("publish_on_failed_review_allowed") is False, "policy human_review_policy.publish_on_failed_review_allowed must be false", errors)

    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls6b_result(result: dict[str, Any], errors: list[str]) -> None:
    require(result.get("status") == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN", "LS-6B result status mismatch", errors)
    require(result.get("post_id") == 119, "LS-6B result post_id must be 119", errors)
    require(result.get("post_status") == "draft", "LS-6B result post_status must be draft", errors)
    require(result.get("payload_count") == 1, "LS-6B result payload_count must be 1", errors)
    require(result.get("max_items") == 1, "LS-6B result max_items must be 1", errors)
    require(result.get("publish_executed") is False, "LS-6B result publish_executed must be false", errors)
    require(result.get("future_schedule_executed") is False, "LS-6B result future_schedule_executed must be false", errors)
    require(result.get("existing_post_update_executed") is False, "LS-6B result existing_post_update_executed must be false", errors)
    require(result.get("delete_executed") is False, "LS-6B result delete_executed must be false", errors)


def validate_ls6b_validation(validation: dict[str, Any], errors: list[str]) -> None:
    vstatus = validation.get("validation_status") or validation.get("status")
    require(vstatus == "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED", "LS-6B validation status mismatch", errors)


def validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    require(lock.get("locked") is True, "lock locked must be true", errors)
    require(lock.get("post_id") == 119, "lock post_id must be 119", errors)
    require(lock.get("post_status") == "draft", "lock post_status must be draft", errors)
    require(lock.get("rerun_allowed") is False, "lock rerun_allowed must be false", errors)


def validate_review(review: dict[str, Any], errors: list[str]) -> None:
    require(review.get("phase") == "LS-7A", "review phase must be LS-7A", errors)
    require(review.get("review_status") == "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "review review_status mismatch", errors)
    require(review.get("technical_creation_result") == "PASS", "review technical_creation_result must be PASS", errors)
    require(review.get("publish_decision") == "DO_NOT_PUBLISH", "review publish_decision must be DO_NOT_PUBLISH", errors)
    require(review.get("manual_publish_allowed") is False, "review manual_publish_allowed must be false", errors)

    target = review.get("target_post", {})
    require(target.get("post_id") == 119, "review target_post.post_id must be 119", errors)
    require(target.get("post_status") == "draft", "review target_post.post_status must be draft", errors)

    observed = set(review.get("observed_issues", []))
    for item in REQUIRED_ISSUES:
        require(item in observed, f"review observed_issues missing: {item}", errors)

    fix = review.get("required_next_fix", {})
    require(fix.get("replace_sample_data_with_real_manual_data") is True, "review required_next_fix.replace_sample_data_with_real_manual_data must be true", errors)
    require(fix.get("convert_markdown_to_html") is True, "review required_next_fix.convert_markdown_to_html must be true", errors)
    require(fix.get("fix_affiliate_disclosure_japanese") is True, "review required_next_fix.fix_affiliate_disclosure_japanese must be true", errors)
    require(fix.get("fix_affiliate_link_format") is True, "review required_next_fix.fix_affiliate_link_format must be true", errors)
    require(fix.get("fix_category_and_tags") is True, "review required_next_fix.fix_category_and_tags must be true", errors)
    require(fix.get("regenerate_payload_preview_before_next_wordpress_write") is True, "review required_next_fix.regenerate_payload_preview_before_next_wordpress_write must be true", errors)

    for key, value in review.get("current_phase_execution", {}).items():
        require(value is False, f"review current_phase_execution.{key} must be false", errors)


def build_result(policy: dict[str, Any], review: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    ok = not errors
    return {
        "phase": "LS-7A",
        "status": "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED" if ok else "LS7A_HUMAN_REVIEW_EVIDENCE_NOT_READY",
        "execution_mode": "REVIEW_ONLY",
        "production_status": "NO_GO",
        "post_id": 119,
        "post_status": "draft",
        "technical_creation_result": review.get("technical_creation_result"),
        "review_status": review.get("review_status"),
        "publish_decision": review.get("publish_decision"),
        "manual_publish_allowed": review.get("manual_publish_allowed"),
        "requires_payload_rebuild": policy.get("expected_review_decision", {}).get("requires_payload_rebuild", True),
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "publish_executed": False,
        "delete_executed": False,
        "approval_token_consumed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6C",
            "execution_allowed": False,
            "purpose": "Real Draft Payload Rebuild DRY_RUN",
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-7A Human Review Result Evidence Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- post_status: {result['post_status']}",
        f"- technical_creation_result: {result['technical_creation_result']}",
        f"- review_status: {result['review_status']}",
        f"- publish_decision: {result['publish_decision']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- requires_payload_rebuild: {result['requires_payload_rebuild']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- wordpress_existing_post_update_executed: {result['wordpress_existing_post_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- delete_executed: {result['delete_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        "- LS-6C: Real Draft Payload Rebuild DRY_RUN",
        "- execution_allowed: False",
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
    parser.add_argument("--policy", default="config/start_ls7a_human_review_result_evidence_policy.json")
    parser.add_argument("--review", default="exchange/human_review/start_ls7a_post119_human_review_decision.json")
    parser.add_argument("--ls6b-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--ls6b-validation-result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_validation_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls7a_human_review_result_evidence_result.json")
    parser.add_argument("--report", default="reports/start_ls7a_human_review_result_evidence_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    review = load_json(Path(args.review))
    ls6b_result = load_json(Path(args.ls6b_result))
    ls6b_validation = load_json(Path(args.ls6b_validation_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []
    validate_policy(policy, errors)
    validate_ls6b_result(ls6b_result, errors)
    validate_ls6b_validation(ls6b_validation, errors)
    validate_lock(ls6b_lock, errors)
    validate_review(review, errors)

    result = build_result(policy, review, errors)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
