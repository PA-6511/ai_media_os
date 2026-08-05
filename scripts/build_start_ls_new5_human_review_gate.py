#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_READY = "LSNEW5_HUMAN_REVIEW_GATE_READY_NO_EXECUTION"
STATUS_FAILED = "LSNEW5_HUMAN_REVIEW_GATE_FAILED_NO_EXECUTION"
LOCK_STATUS = "LSNEW5_HUMAN_REVIEW_GATE_LOCKED_WAITING_FOR_HUMAN_NO_EXECUTION"
REQUIRED_LS_NEW4_STATUS = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION"
REQUIRED_LS_NEW4_VALIDATION = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION"
REQUIRED_APPROVAL_LABEL = "APPROVED_FOR_LS_NEW_6_WP_DRAFT_PAYLOAD_PREP_ONLY"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new5_human_review_gate_policy.json")
    p.add_argument("--schema", default="config/start_ls_new5_human_review_checklist_schema.json")
    p.add_argument("--ls-new4-result", default="exchange/runtime/start_ls_new4_purchase_navigation_payload_dry_run_result.json")
    p.add_argument("--ls-new4-validation-result", default="exchange/logs/start_ls_new4_purchase_navigation_payload_dry_run_validation_result.json")
    p.add_argument("--wp-payload", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_dry_run.json")
    p.add_argument("--wp-preview", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_preview.md")
    p.add_argument("--x-payload", default="exchange/new_release/start_ls_new4_x_post_payload_dry_run.json")
    p.add_argument("--payload-validation-summary", default="exchange/new_release/start_ls_new4_payload_validation_summary.json")

    p.add_argument("--output-review-request", default="exchange/new_release/start_ls_new5_human_review_request.json")
    p.add_argument("--output-checklist-template", default="exchange/new_release/start_ls_new5_human_review_checklist.template.json")
    p.add_argument("--output-decision-template", default="exchange/new_release/start_ls_new5_human_review_decision.template.json")
    p.add_argument("--output-decision-record", default="exchange/new_release/start_ls_new5_human_review_decision.json")
    p.add_argument("--output-wp-review-snapshot", default="exchange/new_release/start_ls_new5_wp_payload_review_snapshot.md")
    p.add_argument("--output-x-review-snapshot", default="exchange/new_release/start_ls_new5_x_payload_review_snapshot.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new5_human_review_gate_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new5_human_review_gate.lock.json")
    p.add_argument("--report", default="reports/start_ls_new5_human_review_gate_report.md")

    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
    p.add_argument("--require-no-auto-approval", action="store_true")
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
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-x-post": args.require_no_x_post,
        "--require-no-auto-approval": args.require_no_auto_approval,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in required.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _candidate_from_ls4(ls4_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "content_item_id": str(ls4_result.get("content_item_id", "")),
        "title": str(ls4_result.get("title", "")),
        "volume": str(ls4_result.get("volume", "")),
        "author": str(ls4_result.get("author", "")),
        "publisher": str(ls4_result.get("publisher", "")),
        "release_date": str(ls4_result.get("release_date", "")),
        "asin": str(ls4_result.get("asin", "")),
        "isbn": str(ls4_result.get("isbn", "")),
    }


def _review_request(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_REQUEST",
        "status": "LSNEW5_HUMAN_REVIEW_REQUEST_CREATED_NO_EXECUTION",
        "production_status": "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION",
        "review_required": True,
        "review_completed": False,
        "human_approved": False,
        "approval_label_consumed": False,
        "approval_label_required_for_next": REQUIRED_APPROVAL_LABEL,
        "target_candidate": dict(candidate),
        "review_targets": {
            "wp_payload": "exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_dry_run.json",
            "wp_preview": "exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_preview.md",
            "x_payload": "exchange/new_release/start_ls_new4_x_post_payload_dry_run.json",
            "payload_validation_summary": "exchange/new_release/start_ls_new4_payload_validation_summary.json",
        },
        "review_points": [
            "作品名・巻数・作者・出版社・発売日の確認",
            "ASIN・ISBNの人間入力値確認",
            "購入ナビ型であり、作品解説メディアになっていないこと",
            "公式あらすじ・ストア説明・レビューのコピーが含まれていないこと",
            "PR表記があること",
            "外部取得未実行の注意書きがあること",
            "X投稿文が280文字以内であること",
            "X投稿文に #PR が含まれること",
            "WordPress下書き作成はまだ行わないこと",
            "X投稿はまだ行わないこと"
        ],
        "execution_allowed": False,
    }


def _checklist_template() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_CHECKLIST_TEMPLATE",
        "candidate_identity_review": {
            "title_checked": False,
            "volume_checked": False,
            "author_checked": False,
            "publisher_checked": False,
            "release_date_checked": False,
            "asin_checked": False,
            "isbn_checked": False,
        },
        "wordpress_payload_review": {
            "post_title_checked": False,
            "body_markdown_checked": False,
            "purchase_navigation_media_checked": False,
            "affiliate_disclosure_checked": False,
            "external_fetch_notice_checked": False,
            "no_synopsis_copy_checked": False,
            "no_review_copy_checked": False,
            "no_long_work_explanation_checked": False,
        },
        "x_payload_review": {
            "post_text_checked": False,
            "under_280_checked": False,
            "contains_pr_checked": False,
            "contains_title_checked": False,
            "contains_author_hashtag_checked": False,
            "contains_url_placeholder_checked": False,
        },
        "safety_review": {
            "wordpress_api_not_executed_checked": False,
            "wordpress_write_not_executed_checked": False,
            "x_api_not_executed_checked": False,
            "x_post_not_executed_checked": False,
            "external_fetch_not_executed_checked": False,
            "credential_env_not_read_checked": False,
            "secret_not_output_checked": False,
            "post119_not_updated_checked": False,
            "post183_not_updated_checked": False,
        },
        "human_decision": {
            "human_review_completed": False,
            "human_approved": False,
            "approval_label": "",
            "reviewer_notes": "",
        },
    }


def _decision_template() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_TEMPLATE",
        "instructions": "Human reviewer must fill this manually. AI must not auto-approve.",
        "allowed_approval_label": REQUIRED_APPROVAL_LABEL,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "reviewer_notes": "",
        "execution_allowed": False,
    }


def _decision_record() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_DECISION_RECORD",
        "status": "LSNEW5_HUMAN_REVIEW_DECISION_WAITING_FOR_HUMAN_NO_EXECUTION",
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "reviewer_notes": "",
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
    }


def _wp_snapshot(wp_preview_text: str) -> str:
    header = "\n".join([
        "# LS-NEW-5 WordPress Payload Review Snapshot",
        "",
        "- Phase: LS-NEW-5",
        "- Review status: WAITING_FOR_HUMAN_REVIEW",
        "- WordPress API executed: false",
        "- WordPress write executed: false",
        "- Human approval: false",
        "",
    ])
    return header + wp_preview_text.strip() + "\n"


def _x_snapshot(x_payload: dict[str, Any]) -> str:
    post_text = str(x_payload.get("post_text", ""))
    count = int(x_payload.get("character_count", len(post_text)))
    under_280 = bool(x_payload.get("under_280", False))
    return "\n".join([
        "# LS-NEW-5 X Payload Review Snapshot",
        "",
        "- Phase: LS-NEW-5",
        "- Review status: WAITING_FOR_HUMAN_REVIEW",
        "- X API executed: false",
        "- X post executed: false",
        "- Human approval: false",
        "",
        "```text",
        post_text,
        "```",
        "",
        f"- character_count: {count}",
        f"- under_280: {'true' if under_280 else 'false'}",
        "",
    ])


def _result_payload(candidate: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    success = len(errors) == 0
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_GATE_RESULT",
        "status": STATUS_READY if success else STATUS_FAILED,
        "execution_mode": "HUMAN_REVIEW_GATE_ONLY_NO_EXECUTION",
        "production_status": "WAITING_FOR_HUMAN_REVIEW_NO_EXECUTION",
        "ls_new4_validated": success,
        **candidate,
        "review_request_created": success,
        "checklist_template_created": success,
        "decision_template_created": success,
        "decision_record_created": success,
        "wp_review_snapshot_created": success,
        "x_review_snapshot_created": success,
        "human_review_required": True,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label": "",
        "approval_label_consumed": False,
        "required_approval_label_for_next": REQUIRED_APPROVAL_LABEL,
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": "WAIT_FOR_HUMAN_REVIEW_DECISION",
        "recommended_next_phase_options": ["LS-NEW-5-DECISION", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _lock_payload() -> dict[str, Any]:
    return {
        "phase": "LS-NEW-5",
        "document_type": "START_LS_NEW5_HUMAN_REVIEW_GATE_LOCK",
        "status": LOCK_STATUS,
        "locked": True,
        "human_review_required": True,
        "human_review_completed": False,
        "human_approved": False,
        "approval_label_consumed": False,
        "ready_for_ls_new_6": False,
        "execution_allowed": False,
        "auto_approval_executed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-5 Human Review Gate Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- content_item_id: {result.get('content_item_id', '')}",
        f"- title: {result.get('title', '')}",
        "",
        "## Errors",
    ]
    errs = result.get("errors", [])
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
    ls4_result = try_load_json(Path(args.ls_new4_result), errors, "ls-new4-result")
    ls4_validation = try_load_json(Path(args.ls_new4_validation_result), errors, "ls-new4-validation-result")
    wp_payload = try_load_json(Path(args.wp_payload), errors, "wp-payload")
    wp_preview = read_text(Path(args.wp_preview), errors, "wp-preview")
    x_payload = try_load_json(Path(args.x_payload), errors, "x-payload")
    payload_validation_summary = try_load_json(Path(args.payload_validation_summary), errors, "payload-validation-summary")

    req(policy.get("phase") == "LS-NEW-5", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-5", "schema phase mismatch", errors)
    req(ls4_result.get("status") == REQUIRED_LS_NEW4_STATUS, "ls-new4 status mismatch", errors)
    req(ls4_validation.get("validation_status") == REQUIRED_LS_NEW4_VALIDATION, "ls-new4 validation mismatch", errors)
    req(bool(ls4_result.get("ready_for_ls_new_5_human_review", False)) is True, "ready_for_ls_new_5_human_review mismatch", errors)
    req(bool(ls4_result.get("execution_allowed", True)) is False, "execution_allowed mismatch", errors)

    candidate = _candidate_from_ls4(ls4_result)
    for key in ["content_item_id", "title", "volume", "author", "publisher", "release_date", "asin", "isbn"]:
        req(str(candidate.get(key, "")).strip() != "", f"missing required candidate field: {key}", errors)

    req(bool(payload_validation_summary.get("purchase_navigation_media", False)) is True, "payload summary purchase_navigation_media mismatch", errors)
    req(bool(payload_validation_summary.get("work_explanation_media", True)) is False, "payload summary work_explanation_media mismatch", errors)
    req(bool(payload_validation_summary.get("x_post_under_280", False)) is True, "payload summary x_post_under_280 mismatch", errors)

    req(bool(wp_payload.get("wordpress_api_call_executed", True)) is False, "wp payload wordpress_api_call_executed=true", errors)
    req(bool(wp_payload.get("wordpress_write_executed", True)) is False, "wp payload wordpress_write_executed=true", errors)
    req(bool(x_payload.get("x_api_call_executed", True)) is False, "x payload x_api_call_executed=true", errors)
    req(bool(x_payload.get("x_post_executed", True)) is False, "x payload x_post_executed=true", errors)

    review_request = _review_request(candidate)
    checklist_template = _checklist_template()
    decision_template = _decision_template()
    decision_record = _decision_record()
    wp_snapshot = _wp_snapshot(wp_preview)
    x_snapshot = _x_snapshot(x_payload)

    result = _result_payload(candidate, errors)
    lock = _lock_payload()

    if len(errors) == 0:
        write_json(Path(args.output_review_request), review_request)
        write_json(Path(args.output_checklist_template), checklist_template)
        write_json(Path(args.output_decision_template), decision_template)
        write_json(Path(args.output_decision_record), decision_record)
        write_text(Path(args.output_wp_review_snapshot), wp_snapshot)
        write_text(Path(args.output_x_review_snapshot), x_snapshot)

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock)
    _write_report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == STATUS_READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
