#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_WAITING = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
STATUS_FAILED = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_FAILED_NO_EXECUTION"
LOCK_STATUS = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_LOCKED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_new2_new_release_comic_candidate_intake_policy.json")
    parser.add_argument("--ls-new1-result", default="exchange/logs/start_ls_new1_new_release_comic_purchase_navigation_result.json")
    parser.add_argument("--ls-new1-policy", default="config/start_ls_new1_new_release_comic_purchase_navigation_policy.json")
    parser.add_argument("--candidate-schema-output", default="config/start_ls_new2_new_release_comic_candidate_intake_schema.json")
    parser.add_argument("--candidate-template-output", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.template.json")
    parser.add_argument("--candidate-record-output", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.json")
    parser.add_argument("--simple-x-template-output", default="exchange/templates/start_ls_new2_simple_x_post_template.md")
    parser.add_argument("--output", default="exchange/runtime/start_ls_new2_new_release_comic_candidate_intake_result.json")
    parser.add_argument("--lock-output", default="exchange/locks/start_ls_new2_new_release_comic_candidate_intake.lock.json")
    parser.add_argument("--report", default="reports/start_ls_new2_new_release_comic_candidate_intake_report.md")

    parser.add_argument("--create-candidate-schema", action="store_true")
    parser.add_argument("--create-candidate-template", action="store_true")
    parser.add_argument("--create-simple-x-template", action="store_true")
    parser.add_argument("--require-human-input", action="store_true")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-external-fetch", action="store_true")
    parser.add_argument("--require-no-amazon-api", action="store_true")
    parser.add_argument("--require-no-x-api", action="store_true")
    parser.add_argument("--require-no-candidate-selection", action="store_true")
    parser.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-post183-update", action="store_true")
    return parser.parse_args()


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _required_flags_ok(args: argparse.Namespace, errors: list[str]) -> None:
    required = {
        "--create-candidate-schema": args.create_candidate_schema,
        "--create-candidate-template": args.create_candidate_template,
        "--create-simple-x-template": args.create_simple_x_template,
        "--require-human-input": args.require_human_input,
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for key, enabled in required.items():
        req(enabled, f"missing required flag: {key}", errors)


def _schema_payload() -> dict[str, Any]:
    return {
        "schema_name": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_SCHEMA",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "required_fields": [
            "content_item_id",
            "title",
            "volume",
            "author",
            "publisher",
            "release_date",
            "candidate_source_type",
            "human_confirmed",
        ],
        "source_requirement": {
            "requires_source_url_or_source_pending": True,
            "source_url_fields": [
                "publisher_source_url",
                "kindle_url",
                "rakuten_kobo_url",
                "dmm_books_url",
                "ebookjapan_url",
                "booklive_url",
                "manual_source_url",
            ],
            "source_pending_allowed": True,
        },
        "field_rules": {
            "content_item_id": {"type": "string", "required": True, "non_empty": True},
            "title": {"type": "string", "required": True, "non_empty": True, "ai_auto_inference_allowed": False},
            "volume": {"type": "string", "required": True, "non_empty": True},
            "author": {"type": "string", "required": True, "non_empty": True},
            "publisher": {"type": "string", "required": True, "non_empty": True},
            "release_date": {"type": "string", "required": True, "format": "YYYY-MM-DD", "ai_auto_inference_allowed": False},
            "human_confirmed": {"type": "boolean", "required": True, "must_be_true_for_ready": True},
        },
        "copy_policy": {
            "official_synopsis_copy_allowed": False,
            "store_description_copy_allowed": False,
            "publisher_description_copy_allowed": False,
            "review_copy_allowed": False,
            "user_comment_copy_allowed": False,
            "catchcopy_copy_allowed": False,
            "short_original_comment_allowed": True,
        },
        "simple_x_post_rule": {
            "enabled": True,
            "max_characters": 280,
            "template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
            "requires_pr_hashtag_when_affiliate_url_present": True,
            "requires_url": True,
            "does_not_require_synopsis": True,
            "does_not_require_price_or_point_rate": True,
            "does_not_require_store_comparison": True,
        },
        "safety": {
            "no_execution": True,
            "wordpress_write_allowed": False,
            "x_post_allowed": False,
            "external_api_call_allowed": False,
            "http_get_allowed": False,
            "scraping_allowed": False,
            "credential_env_read_allowed": False,
            "publish_allowed": False,
        },
    }


def _template_payload() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_TEMPLATE",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": "",
        "title": "",
        "volume": "",
        "author": "",
        "publisher": "",
        "label": "",
        "release_date": "",
        "ebook_release_date": "",
        "paper_release_date": "",
        "candidate_source_type": "",
        "publisher_source_url": "",
        "kindle_url": "",
        "rakuten_kobo_url": "",
        "dmm_books_url": "",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "asin": "",
        "isbn": "",
        "store_product_ids": {},
        "price_notes": "",
        "point_reward_notes": "",
        "reservation_status_notes": "",
        "delivery_status_notes": "",
        "campaign_notes": "",
        "short_original_comment": "",
        "affiliate_url_pending": True,
        "simple_x_post_template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
        "simple_x_post_max_characters": 280,
        "human_filled": False,
        "human_confirmed": False,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "wordpress_write_allowed": False,
        "x_post_allowed": False,
        "external_api_call_allowed": False,
        "scraping_allowed": False,
        "errors": [],
    }


def _record_payload() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2",
        "status": "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": "",
        "title": "",
        "volume": "",
        "author": "",
        "publisher": "",
        "label": "",
        "release_date": "",
        "ebook_release_date": "",
        "paper_release_date": "",
        "candidate_source_type": "",
        "publisher_source_url": "",
        "kindle_url": "",
        "rakuten_kobo_url": "",
        "dmm_books_url": "",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "asin": "",
        "isbn": "",
        "store_product_ids": {},
        "price_notes": "",
        "point_reward_notes": "",
        "reservation_status_notes": "",
        "delivery_status_notes": "",
        "campaign_notes": "",
        "short_original_comment": "",
        "affiliate_url_pending": True,
        "simple_x_post_template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
        "simple_x_post_max_characters": 280,
        "human_filled": False,
        "human_confirmed": False,
        "human_input_required": True,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "missing_required_human_fields": [
            "content_item_id",
            "title",
            "volume",
            "author",
            "publisher",
            "release_date",
            "candidate_source_type",
            "human_confirmed",
        ],
        "missing_source_requirement": False,
        "errors": [],
    }


def _simple_x_template_markdown() -> str:
    return (
        "# START-LS LS-NEW-2 Simple X Post Template\n\n"
        "## Purpose\n\n"
        "新刊コミックのX投稿は、作品解説ではなく配信開始・購入導線の簡易告知として扱う。\n\n"
        "## Standard Template\n\n"
        "```text\n"
        "配信開始です\n"
        "#PR #Amazonmanga #Kindle #作者名\n"
        "『タイトル』第○巻\n\n"
        "URL\n"
        "```\n\n"
        "## Rules\n\n"
        "- 280文字以内にする。\n"
        "- アフィリエイトURLを含む場合は `#PR` を必須にする。\n"
        "- 作品あらすじは入れない。\n"
        "- 公式説明文・商品説明文・レビュー文を転載しない。\n"
        "- 価格比較・ポイント還元率比較はX本文では必須にしない。\n"
        "- 詳細比較はWordPress記事側に寄せる。\n"
        "- X投稿はこのフェーズでは実行しない。\n"
    )


def _result_payload(policy: dict[str, Any], errors: list[str], ls_new1_validated: bool) -> dict[str, Any]:
    status = STATUS_WAITING if not errors else STATUS_FAILED
    policy_next = policy.get("next_phase", {}) if isinstance(policy, dict) else {}
    return {
        "phase": "LS-NEW-2",
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RESULT",
        "status": status,
        "execution_mode": "CANDIDATE_INTAKE_SCHEMA_AND_TEMPLATE_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEW_RELEASE_CANDIDATE_INTAKE_ONLY",
        "ls_new1_validated": bool(ls_new1_validated),
        "candidate_intake_schema_created": not errors,
        "candidate_intake_template_created": not errors,
        "candidate_intake_record_exists": not errors,
        "simple_x_post_template_created": not errors,
        "simple_x_post_max_characters": 280,
        "simple_x_template_under_280": True,
        "human_input_required": True,
        "human_filled": False,
        "human_confirmed": False,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "work_explanation_required": False,
        "long_work_explanation_required": False,
        "synopsis_required": False,
        "price_comparison_required_in_x_post": False,
        "point_reward_rate_required_in_x_post": False,
        "store_comparison_required_in_x_post": False,
        "execution_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_created": False,
        "publish_executed_by_this_phase": False,
        "x_post_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "ls_next1_fill_updated": False,
        "ls_next2_started": False,
        "ls_sale_route_started": False,
        "asin_auto_inferred": False,
        "title_auto_inferred": False,
        "release_date_auto_inferred": False,
        "price_auto_inferred": False,
        "point_reward_rate_auto_inferred": False,
        "candidate_ranking_executed": False,
        "candidate_selected": False,
        "locked": not errors,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": str(policy_next.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(policy_next.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _lock_payload(policy: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    policy_next = policy.get("next_phase", {}) if isinstance(policy, dict) else {}
    return {
        "phase": "LS-NEW-2",
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_LOCK",
        "status": LOCK_STATUS if not errors else "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_LOCK_FAILED_NO_EXECUTION",
        "locked": not errors,
        "candidate_intake_schema_created": not errors,
        "candidate_intake_template_created": not errors,
        "candidate_intake_record_exists": not errors,
        "simple_x_post_template_created": not errors,
        "human_input_required": True,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": str(policy_next.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(policy_next.get("recommended_next_phase_options", [])),
    }


def _write_report(path: Path, result_payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-2 New Release Comic Candidate Intake Report",
        "",
        f"- generated_at: {result_payload.get('generated_at', '')}",
        f"- phase: {result_payload.get('phase', '')}",
        f"- status: {result_payload.get('status', '')}",
        f"- production_status: {result_payload.get('production_status', '')}",
        f"- ls_new1_validated: {result_payload.get('ls_new1_validated', False)}",
        f"- candidate_intake_schema_created: {result_payload.get('candidate_intake_schema_created', False)}",
        f"- candidate_intake_template_created: {result_payload.get('candidate_intake_template_created', False)}",
        f"- candidate_intake_record_exists: {result_payload.get('candidate_intake_record_exists', False)}",
        f"- simple_x_post_template_created: {result_payload.get('simple_x_post_template_created', False)}",
        f"- simple_x_template_under_280: {result_payload.get('simple_x_template_under_280', False)}",
        f"- recommended_next_action: {result_payload.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if result_payload.get("errors"):
        lines.extend(f"- {e}" for e in result_payload["errors"])
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    ls_new1_result = try_load_json(Path(args.ls_new1_result), errors, "ls-new1-result")
    ls_new1_policy = try_load_json(Path(args.ls_new1_policy), errors, "ls-new1-policy")

    _required_flags_ok(args, errors)

    req(ls_new1_policy.get("phase") == "LS-NEW-1", "ls-new1-policy phase mismatch", errors)

    required_prev = policy.get("required_previous_phase", {}).get("ls_new1", {}) if isinstance(policy, dict) else {}
    req(
        ls_new1_result.get("validation_status") == required_prev.get("required_validation_status"),
        "ls-new1 validation mismatch",
        errors,
    )
    req(ls_new1_result.get("status") == required_prev.get("required_status"), "ls-new1 status mismatch", errors)
    req(
        ls_new1_result.get("production_status") == required_prev.get("required_production_status"),
        "ls-new1 production_status mismatch",
        errors,
    )
    req(
        ls_new1_result.get("sale_route_status") == required_prev.get("required_sale_route_status"),
        "ls-new1 sale_route_status mismatch",
        errors,
    )
    req(
        ls_new1_result.get("new_release_comic_route_status") == required_prev.get("required_new_release_comic_route_status"),
        "ls-new1 new_release_comic_route_status mismatch",
        errors,
    )
    req(ls_new1_result.get("media_type") == required_prev.get("required_media_type"), "ls-new1 media_type mismatch", errors)
    req(
        ls_new1_result.get("not_media_type") == required_prev.get("required_not_media_type"),
        "ls-new1 not_media_type mismatch",
        errors,
    )

    ls_new1_validated = not any(msg.startswith("ls-new1") for msg in errors)

    if not errors:
        if args.create_candidate_schema:
            write_json(Path(args.candidate_schema_output), _schema_payload())
        if args.create_candidate_template:
            write_json(Path(args.candidate_template_output), _template_payload())
        write_json(Path(args.candidate_record_output), _record_payload())
        if args.create_simple_x_template:
            write_text(Path(args.simple_x_template_output), _simple_x_template_markdown())

    result_payload = _result_payload(policy, errors, ls_new1_validated)
    lock_payload = _lock_payload(policy, errors)

    write_json(Path(args.output), result_payload)
    write_json(Path(args.lock_output), lock_payload)
    _write_report(Path(args.report), result_payload)

    print(result_payload["status"])
    return 0 if result_payload["status"] == STATUS_WAITING else 1


if __name__ == "__main__":
    raise SystemExit(main())
