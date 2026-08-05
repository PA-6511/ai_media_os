#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_READY = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_READY_NO_EXECUTION"
STATUS_FAILED = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_FAILED_NO_EXECUTION"
LOCK_STATUS = "LSNEW6_WP_DRAFT_PAYLOAD_PREP_LOCKED_NO_EXECUTION"
REQ_NEW5_STATUS = "LSNEW5_HUMAN_REVIEW_DECISION_HUMAN_APPROVED_NO_EXECUTION"
REQ_NEW5_VALID = "LSNEW5_DECISION_VALIDATED_NO_EXECUTION"
REQ_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new6_wp_draft_payload_prep_policy.json")
    p.add_argument("--schema", default="config/start_ls_new6_wp_draft_payload_schema.json")
    p.add_argument("--ls-new4-wp-payload", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_dry_run.json")
    p.add_argument("--ls-new4-wp-preview", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_preview.md")
    p.add_argument("--ls-new4-validation-summary", default="exchange/new_release/start_ls_new4_payload_validation_summary.json")
    p.add_argument("--ls-new5-decision-result", default="exchange/runtime/start_ls_new5_decision_result.json")
    p.add_argument("--ls-new5-decision-validation-result", default="exchange/logs/start_ls_new5_decision_validation_result.json")
    p.add_argument("--ls-new5-decision-record", default="exchange/new_release/start_ls_new5_decision_result_record.json")
    p.add_argument("--output-payload", default="exchange/new_release/start_ls_new6_wp_draft_payload_prep.json")
    p.add_argument("--output-preview", default="exchange/new_release/start_ls_new6_wp_draft_payload_preview.md")
    p.add_argument("--output-safety-summary", default="exchange/new_release/start_ls_new6_wp_draft_payload_safety_summary.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new6_wp_draft_payload_prep_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new6_wp_draft_payload_prep.lock.json")
    p.add_argument("--report", default="reports/start_ls_new6_wp_draft_payload_prep_report.md")

    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-wordpress-draft", action="store_true")
    p.add_argument("--require-no-wordpress-publish", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
    p.add_argument("--require-no-approval-label-consumption", action="store_true")
    p.add_argument("--require-no-target-post-id-allocation", action="store_true")
    p.add_argument("--require-no-candidate-selection", action="store_true")
    p.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    p.add_argument("--forbid-post119-update", action="store_true")
    p.add_argument("--forbid-post183-update", action="store_true")
    return p.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json {label}: {path}")
        return {}


def read_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        errors.append(f"failed to read {label}: {path}")
        return ""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _validate_required_flags(args: argparse.Namespace, errors: list[str]) -> None:
    required = {
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-http-get": args.require_no_http_get,
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-wordpress-write": args.require_no_wordpress_write,
        "--require-no-wordpress-draft": args.require_no_wordpress_draft,
        "--require-no-wordpress-publish": args.require_no_wordpress_publish,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-approval-label-consumption": args.require_no_approval_label_consumption,
        "--require-no-target-post-id-allocation": args.require_no_target_post_id_allocation,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in required.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _payload_preview(post_title: str, post_content_markdown: str) -> str:
    return "\n".join(
        [
            "# LS-NEW-6 WordPress Draft Payload Prep Preview",
            "",
            "- Phase: LS-NEW-6",
            "- Status: READY_NO_EXECUTION",
            "- WordPress API executed: false",
            "- WordPress write executed: false",
            "- WordPress draft created: false",
            "- Target post ID allocated: false",
            "- Execution allowed: false",
            "- Source approval: APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY",
            "- Approval label consumed: false",
            "",
            "## post_title",
            "",
            post_title,
            "",
            "## post_content_markdown",
            "",
            "```markdown",
            post_content_markdown,
            "```",
            "",
        ]
    )


def _safety_summary() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_SAFETY_SUMMARY",
        "status": "LSNEW6_SAFETY_SUMMARY_READY_NO_EXECUTION",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "target_post_id_allocated": False,
        "approval_label_consumed": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": True,
    }


def _lock_payload() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_LOCK",
        "status": LOCK_STATUS,
        "locked": True,
        "execution_allowed": False,
        "approval_label_consumed": False,
        "target_post_id_allocated": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-6 WP Draft Payload Prep Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- content_item_id: {result.get('content_item_id', '')}",
        f"- title: {result.get('title', '')}",
        "",
        "## Errors",
    ]
    errs = list(result.get("errors", []))
    if errs:
        lines.extend(f"- {e}" for e in errs)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    _validate_required_flags(args, errors)

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    ls4_payload = try_load_json(Path(args.ls_new4_wp_payload), errors, "ls-new4-wp-payload")
    ls4_preview = read_text(Path(args.ls_new4_wp_preview), errors, "ls-new4-wp-preview")
    ls4_validation_summary = try_load_json(Path(args.ls_new4_validation_summary), errors, "ls-new4-validation-summary")
    ls5_result = try_load_json(Path(args.ls_new5_decision_result), errors, "ls-new5-decision-result")
    ls5_validation = try_load_json(Path(args.ls_new5_decision_validation_result), errors, "ls-new5-decision-validation-result")
    ls5_record = try_load_json(Path(args.ls_new5_decision_record), errors, "ls-new5-decision-record")

    req(policy.get("phase") == "LS-NEW-6", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-6", "schema phase mismatch", errors)

    req(ls5_result.get("status") == REQ_NEW5_STATUS, "ls-new5 decision status mismatch", errors)
    req(ls5_validation.get("validation_status") == REQ_NEW5_VALID, "ls-new5 decision validation mismatch", errors)
    req(ls5_record.get("status") == REQ_NEW5_STATUS, "ls-new5 decision record status mismatch", errors)
    req(ls5_result.get("ready_for_ls_new_6") is True, "ls-new5 ready_for_ls_new_6 mismatch", errors)
    req(ls5_result.get("execution_allowed") is False, "ls-new5 execution_allowed mismatch", errors)
    req(str(ls5_result.get("approval_label", "")) == REQ_LABEL, "ls-new5 approval_label mismatch", errors)

    req(ls4_payload.get("document_type") == "START_LS_NEW4_WP_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN", "ls-new4 payload document_type mismatch", errors)
    req(ls4_payload.get("wordpress_api_call_executed") is False, "ls-new4 payload wordpress_api_call_executed=true", errors)
    req(ls4_payload.get("wordpress_write_executed") is False, "ls-new4 payload wordpress_write_executed=true", errors)
    req(ls4_payload.get("post_status_target") == "draft", "ls-new4 payload post_status_target mismatch", errors)
    req(ls4_validation_summary.get("purchase_navigation_media") is True, "ls-new4 purchase_navigation_media mismatch", errors)
    req(ls4_validation_summary.get("work_explanation_media") is False, "ls-new4 work_explanation_media mismatch", errors)
    req(ls4_validation_summary.get("external_fetch_executed") is False, "ls-new4 external_fetch_executed=true", errors)
    req(ls4_validation_summary.get("wordpress_write_executed") is False, "ls-new4 wordpress_write_executed=true", errors)

    identity = dict(ls4_payload.get("candidate_identity", {}))
    for key in ["content_item_id", "title", "volume", "author", "publisher", "release_date", "asin", "isbn"]:
        req(str(identity.get(key, "")).strip() != "", f"missing candidate field: {key}", errors)

    post_title = str(ls4_payload.get("post_title", ""))
    post_content_markdown = str(ls4_payload.get("body_markdown", ""))
    req(post_title != "", "missing post_title", errors)
    req(post_content_markdown != "", "missing body_markdown", errors)

    affiliate_disclosure_included = str(ls4_payload.get("affiliate_disclosure", "")).strip() != ""
    external_fetch_notice_included = str(ls4_payload.get("external_fetch_notice", "")).strip() != ""
    source_unverified_notice_included = (
        "未取得" in post_content_markdown
        or "実行していません" in post_content_markdown
        or "DRY_RUN" in post_content_markdown
    )

    payload = {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP",
        "status": STATUS_READY if len(errors) == 0 else STATUS_FAILED,
        "execution_mode": "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "ls_new5_decision_validated": len(errors) == 0,
        "ls_new5_decision_approved": len(errors) == 0,
        "source_approval_label": str(ls5_result.get("approval_label", "")),
        "approval_label_consumed": False,
        "content_item_id": str(identity.get("content_item_id", "")),
        "title": str(identity.get("title", "")),
        "volume": str(identity.get("volume", "")),
        "author": str(identity.get("author", "")),
        "publisher": str(identity.get("publisher", "")),
        "release_date": str(identity.get("release_date", "")),
        "asin": str(identity.get("asin", "")),
        "isbn": str(identity.get("isbn", "")),
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "post_title": post_title,
        "post_content_markdown": post_content_markdown,
        "post_content_source": "LS-NEW-4 WP purchase navigation payload dry run",
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "affiliate_disclosure_included": affiliate_disclosure_included,
        "external_fetch_notice_included": external_fetch_notice_included,
        "source_unverified_notice_included": source_unverified_notice_included,
        "official_synopsis_copy_included": False,
        "store_description_copy_included": False,
        "review_copy_included": False,
        "long_work_explanation_included": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": len(errors) == 0,
        "recommended_next_action": "BEGIN_LS_NEW_7_WP_DRAFT_RUNNER_PREP_NO_EXECUTION" if len(errors) == 0 else "WAIT_OR_REVIEW_REWORK",
        "recommended_next_phase_options": ["LS-NEW-7", "LS-MON-2"],
        "errors": list(errors),
    }

    safety = _safety_summary()
    preview = _payload_preview(post_title, post_content_markdown)

    result = {
        "phase": "LS-NEW-6",
        "document_type": "START_LS_NEW6_WP_DRAFT_PAYLOAD_PREP_RESULT",
        "status": payload["status"],
        "execution_mode": "WP_DRAFT_PAYLOAD_PREP_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_WP_DRAFT_PAYLOAD_PREP_ONLY",
        "ls_new5_decision_validated": payload["ls_new5_decision_validated"],
        "ls_new5_decision_approved": payload["ls_new5_decision_approved"],
        "source_approval_label": payload["source_approval_label"],
        "approval_label_consumed": False,
        "wp_draft_payload_created": len(errors) == 0,
        "wp_draft_payload_preview_created": len(errors) == 0,
        "safety_summary_created": len(errors) == 0,
        "content_item_id": payload["content_item_id"],
        "title": payload["title"],
        "volume": payload["volume"],
        "author": payload["author"],
        "publisher": payload["publisher"],
        "release_date": payload["release_date"],
        "post_status_target": "draft",
        "target_post_id": None,
        "target_post_id_allocated": False,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "affiliate_disclosure_included": payload["affiliate_disclosure_included"],
        "external_fetch_notice_included": payload["external_fetch_notice_included"],
        "source_unverified_notice_included": payload["source_unverified_notice_included"],
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "execution_allowed": False,
        "ready_for_ls_new_7": payload["ready_for_ls_new_7"],
        "recommended_next_action": payload["recommended_next_action"],
        "recommended_next_phase_options": ["LS-NEW-7", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    lock = _lock_payload()

    if len(errors) == 0:
        write_json(Path(args.output_payload), payload)
        write_text(Path(args.output_preview), preview)
        write_json(Path(args.output_safety_summary), safety)

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock)
    _write_report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == STATUS_READY else 1


if __name__ == "__main__":
    raise SystemExit(main())