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


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6C", "policy phase must be LS-6C", errors)
    require(policy.get("execution_mode") == "DRY_RUN_ONLY", "policy execution_mode must be DRY_RUN_ONLY", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status must be NO_GO", errors)
    for key, value in policy.get("current_phase_safety_flags", {}).items():
        require(value is False, f"policy current_phase_safety_flags.{key} must be false", errors)


def validate_ls7a(ls7a_result: dict[str, Any], ls7a_review: dict[str, Any], errors: list[str]) -> None:
    require(ls7a_result.get("status") == "LS7A_HUMAN_REVIEW_DO_NOT_PUBLISH_EVIDENCE_RECORDED", "LS-7A result status mismatch", errors)
    require(ls7a_result.get("publish_decision") == "DO_NOT_PUBLISH", "LS-7A publish_decision mismatch", errors)
    require(ls7a_result.get("requires_payload_rebuild") is True, "LS-7A requires_payload_rebuild must be true", errors)
    require(ls7a_review.get("review_status") == "DO_NOT_PUBLISH_SAMPLE_PAYLOAD", "LS-7A review_status mismatch", errors)
    require(ls7a_review.get("manual_publish_allowed") is False, "LS-7A manual_publish_allowed must be false", errors)


def validate_payload_ready(payload: dict[str, Any], errors: list[str]) -> None:
    require(payload.get("payload_ready") is True, "payload_ready must be true", errors)
    require(payload.get("max_items") == 1, "max_items must be 1", errors)
    require(payload.get("payload_count") == 1, "payload_count must be 1", errors)

    payloads = payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "payloads must contain exactly one item", errors)
    if not (isinstance(payloads, list) and len(payloads) == 1):
        return

    item = payloads[0]
    require(item.get("post_status") == "draft", "post_status must be draft", errors)
    require(item.get("content_format") == "html", "content_format must be html", errors)
    require(item.get("affiliate_disclosure_present") is True, "affiliate_disclosure_present must be true", errors)
    require(item.get("affiliate_link_present") is True, "affiliate_link_present must be true", errors)
    require(item.get("html_link_present") is True, "html_link_present must be true", errors)
    require(item.get("markdown_link_present") is False, "markdown_link_present must be false", errors)
    require(item.get("category_or_tag_present") is True, "category_or_tag_present must be true", errors)
    require(item.get("category") != "未分類", "category must not be 未分類", errors)
    tags = item.get("tags")
    require(isinstance(tags, list) and len(tags) > 0, "tags must be non-empty list", errors)
    require(item.get("sample_content_detected") is False, "sample_content_detected must be false", errors)

    content = str(item.get("content", ""))
    require("[Amazon" not in content and "](https://" not in content, "markdown link pattern must not remain", errors)
    require("<a href=" in content, "html anchor link is required", errors)


def validate_no_execution_flags(payload: dict[str, Any], errors: list[str]) -> None:
    for key in [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "wordpress_existing_post_update_executed",
        "post119_update_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "amazon_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "credential_env_read_executed",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "approval_token_consumed",
        "ls6b_rerun_executed",
    ]:
        if key in payload:
            require(payload.get(key) is False, f"payload {key} must be false", errors)


def build_result(status: str, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6C",
        "status": status,
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6C Real Draft Payload Rebuild DRY_RUN Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
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
    parser.add_argument("--policy", default="config/start_ls6c_real_draft_payload_rebuild_dry_run_policy.json")
    parser.add_argument("--payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls7a-result", default="exchange/logs/start_ls7a_human_review_result_evidence_result.json")
    parser.add_argument("--ls7a-review", default="exchange/human_review/start_ls7a_post119_human_review_decision.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--report", default="reports/start_ls6c_real_draft_payload_rebuild_dry_run_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    payload = load_json(Path(args.payload))
    ls7a_result = load_json(Path(args.ls7a_result))
    ls7a_review = load_json(Path(args.ls7a_review))

    errors: list[str] = []
    validate_policy(policy, errors)
    validate_ls7a(ls7a_result, ls7a_review, errors)
    validate_no_execution_flags(payload, errors)

    payload_status = payload.get("status")
    if payload_status == "LS6C_REAL_INPUT_NOT_READY":
        status = "LS6C_REAL_INPUT_NOT_READY_RECORDED" if not errors else "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"
    elif payload_status == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY":
        validate_payload_ready(payload, errors)
        status = "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY" if not errors else "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"
    else:
        errors.append("unsupported payload status")
        status = "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_NOT_READY"

    result = build_result(status, errors)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
