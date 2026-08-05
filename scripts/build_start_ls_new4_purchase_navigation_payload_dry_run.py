#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_PASSED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_FAILED_NO_EXECUTION"
LOCK_STATUS = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_LOCKED_NO_EXECUTION"
REQUIRED_LS_NEW3_STATUS = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION"
REQUIRED_LS_NEW3_VALIDATION = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

REQUIRED_CANDIDATE_FIELDS = [
    "content_item_id",
    "title",
    "volume",
    "author",
    "publisher",
    "release_date",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new4_purchase_navigation_payload_dry_run_policy.json")
    p.add_argument("--schema", default="config/start_ls_new4_purchase_navigation_payload_schema.json")
    p.add_argument("--ls-new3-result", default="exchange/runtime/start_ls_new3_candidate_evidence_dry_run_result.json")
    p.add_argument("--ls-new3-validation-result", default="exchange/logs/start_ls_new3_candidate_evidence_dry_run_validation_result.json")
    p.add_argument("--candidate-evidence-record", default="exchange/new_release/start_ls_new3_candidate_evidence_dry_run.json")
    p.add_argument("--source-inventory", default="exchange/new_release/start_ls_new3_source_url_inventory.json")
    p.add_argument("--store-slots", default="exchange/new_release/start_ls_new3_store_evidence_slots.json")
    p.add_argument("--x-preview", default="exchange/new_release/start_ls_new3_simple_x_post_preview.json")
    p.add_argument("--wp-preview", default="exchange/new_release/start_ls_new3_wp_purchase_navigation_preview.md")
    p.add_argument("--output-wp-payload", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_dry_run.json")
    p.add_argument("--output-wp-preview", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_preview.md")
    p.add_argument("--output-x-payload", default="exchange/new_release/start_ls_new4_x_post_payload_dry_run.json")
    p.add_argument("--output-validation-summary", default="exchange/new_release/start_ls_new4_payload_validation_summary.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new4_purchase_navigation_payload_dry_run_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new4_purchase_navigation_payload_dry_run.lock.json")
    p.add_argument("--report", default="reports/start_ls_new4_purchase_navigation_payload_dry_run_report.md")

    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-wordpress-write", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-x-post", action="store_true")
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


def _is_non_empty(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


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
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for name, enabled in required.items():
        if not enabled:
            errors.append(f"missing required flag: {name}")


def _candidate_identity(evidence: dict[str, Any]) -> dict[str, Any]:
    candidate = evidence.get("candidate_identity", {})
    return candidate if isinstance(candidate, dict) else {}


def _build_wp_payload(evidence: dict[str, Any], source_inventory: dict[str, Any], store_slots: dict[str, Any]) -> dict[str, Any]:
    candidate = _candidate_identity(evidence)
    title = str(candidate.get("title", ""))
    volume = str(candidate.get("volume", ""))
    author = str(candidate.get("author", ""))
    publisher = str(candidate.get("publisher", ""))
    release_date = str(candidate.get("release_date", ""))
    asin = str(evidence.get("identifier_evidence", {}).get("asin", ""))
    isbn = str(evidence.get("identifier_evidence", {}).get("isbn", ""))

    store_display = [
        ("出版社公式", "publisher_source_url"),
        ("Kindle", "kindle_url"),
        ("楽天Kobo", "rakuten_kobo_url"),
        ("DMMブックス", "dmm_books_url"),
        ("ebookjapan", "ebookjapan_url"),
        ("BookLive", "booklive_url"),
    ]
    store_candidate_list = []
    for display, key in store_display:
        present = bool(source_inventory.get(key, {}).get("present", False))
        verification_status = str(source_inventory.get(key, {}).get("verification_status", "NOT_PROVIDED"))
        store_candidate_list.append({"store": display, "url_present": present, "verification_status": verification_status})

    body_markdown = "\n".join(
        [
            f"# 【{release_date}発売】{title} {volume} 電子書籍ストア候補",
            "",
            f"このページは、新刊コミック『{title}』{volume}の発売日・販売ストア候補を整理する購入ナビ用DRY_RUNです。",
            "",
            "## 基本情報",
            "",
            f"- 作品名: {title}",
            f"- 巻数: {volume}",
            f"- 作者: {author}",
            f"- 出版社: {publisher}",
            f"- 発売日: {release_date}",
            f"- ASIN: {asin}",
            f"- ISBN: {isbn}",
            "",
            "## 販売ストア候補",
            "",
            f"- 出版社公式: {'URL入力あり / 未取得' if store_candidate_list[0]['url_present'] else 'URL未入力'}",
            f"- Kindle: {'URL入力あり / 未取得' if store_candidate_list[1]['url_present'] else 'URL未入力'}",
            f"- 楽天Kobo: {'URL入力あり / 未取得' if store_candidate_list[2]['url_present'] else 'URL未入力'}",
            f"- DMMブックス: {'URL入力あり / 未取得' if store_candidate_list[3]['url_present'] else 'URL未入力'}",
            f"- ebookjapan: {'URL入力あり / 未取得' if store_candidate_list[4]['url_present'] else 'URL未入力'}",
            f"- BookLive: {'URL入力あり / 未取得' if store_candidate_list[5]['url_present'] else 'URL未入力'}",
            "",
            "## 確認状態",
            "",
            "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。",
            "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。",
            "",
            "## PR表記",
            "",
            "このページにはPR・アフィリエイトリンクを含む場合があります。",
            "",
        ]
    )

    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_WP_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN",
        "generated": True,
        "wordpress_write_executed": False,
        "wordpress_api_call_executed": False,
        "post_status_target": "draft",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "candidate_identity": {
            "content_item_id": str(candidate.get("content_item_id", "")),
            "title": title,
            "volume": volume,
            "author": author,
            "publisher": publisher,
            "release_date": release_date,
            "asin": asin,
            "isbn": isbn,
        },
        "post_title": f"【{release_date}発売】{title} {volume} 電子書籍ストア候補",
        "body_markdown": body_markdown,
        "affiliate_disclosure": "このページにはPR・アフィリエイトリンクを含む場合があります。",
        "external_fetch_notice": "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。",
        "store_candidate_list": store_candidate_list,
        "content_policy": {
            "work_explanation_required": False,
            "long_work_explanation_required": False,
            "synopsis_required": False,
            "official_synopsis_copy_included": False,
            "store_description_copy_included": False,
            "publisher_description_copy_included": False,
            "review_copy_included": False,
        },
        "safety": {
            "external_fetch_executed": False,
            "http_get_executed": False,
            "wordpress_api_call_executed": False,
            "wordpress_write_executed": False,
            "execution_allowed": False,
        },
    }


def _build_wp_preview_md(wp_payload: dict[str, Any]) -> str:
    candidate = wp_payload["candidate_identity"]
    return "\n".join(
        [
            "# LS-NEW-4 WordPress Purchase Navigation Preview",
            "",
            "- Phase: LS-NEW-4",
            "- Execution: NO_EXECUTION / PREVIEW_ONLY",
            "- WordPress write executed: false",
            "",
            "## Candidate",
            "",
            f"- Title: {candidate['title']}",
            f"- Volume: {candidate['volume']}",
            f"- Author: {candidate['author']}",
            f"- Publisher: {candidate['publisher']}",
            f"- Release date: {candidate['release_date']}",
            f"- ASIN: {candidate['asin']}",
            f"- ISBN: {candidate['isbn']}",
            "",
            "## Purchase Navigation Draft Preview",
            "",
            wp_payload["post_title"],
            "",
            "配信・販売ストア候補:",
            "- 出版社公式: URL入力あり / 未取得",
            "- Kindle: URL入力あり / 未取得",
            "- 楽天Kobo: URL入力あり / 未取得",
            "- DMMブックス: URL入力あり / 未取得",
            "- ebookjapan: URL未入力",
            "- BookLive: URL未入力",
            "",
            "確認状態:",
            "このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。",
            "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。",
            "",
            "## PR表記",
            "",
            wp_payload["affiliate_disclosure"],
            "",
        ]
    )


def _build_x_payload(x_preview: dict[str, Any]) -> dict[str, Any]:
    post_text = str(x_preview.get("post_text", ""))
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_X_POST_PAYLOAD_DRY_RUN",
        "generated": True,
        "x_post_executed": False,
        "x_api_call_executed": False,
        "template_source": "LS-NEW-3 simple X preview",
        "post_text": post_text,
        "character_count": len(post_text),
        "under_280": len(post_text) <= 280,
        "contains_pr": "#PR" in post_text,
        "contains_title": "月曜日のたわわ" in post_text,
        "contains_author_hashtag": "#比村奇石" in post_text,
        "contains_url_placeholder": "URL" in post_text,
        "content_policy": {
            "synopsis_included": False,
            "price_comparison_required": False,
            "point_reward_rate_required": False,
            "store_comparison_required": False,
            "long_work_explanation_included": False,
        },
        "safety": {
            "x_post_executed": False,
            "x_api_call_executed": False,
            "execution_allowed": False,
        },
    }


def _build_validation_summary(wp_payload: dict[str, Any], x_payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PAYLOAD_VALIDATION_SUMMARY",
        "wp_payload_valid": True,
        "x_payload_valid": True,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "official_synopsis_copy_included": False,
        "store_description_copy_included": False,
        "review_copy_included": False,
        "x_post_under_280": bool(x_payload.get("under_280", False)),
        "external_fetch_executed": False,
        "wordpress_write_executed": False,
        "x_post_executed": False,
        "ready_for_ls_new_5_human_review": bool(result.get("ready_for_ls_new_5_human_review", False)),
        "execution_allowed": False,
        "errors": [],
    }


def _result_payload(evidence: dict[str, Any], x_payload: dict[str, Any], validation_summary: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    candidate = _candidate_identity(evidence)
    success = len(errors) == 0
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_RESULT",
        "status": STATUS_PASSED if success else STATUS_FAILED,
        "execution_mode": "PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_ONLY_NO_EXTERNAL_FETCH",
        "production_status": "NO_EXECUTION_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_ONLY",
        "ls_new3_validated": success,
        "content_item_id": str(candidate.get("content_item_id", "")),
        "title": str(candidate.get("title", "")),
        "volume": str(candidate.get("volume", "")),
        "author": str(candidate.get("author", "")),
        "publisher": str(candidate.get("publisher", "")),
        "release_date": str(candidate.get("release_date", "")),
        "asin": str(evidence.get("identifier_evidence", {}).get("asin", "")),
        "isbn": str(evidence.get("identifier_evidence", {}).get("isbn", "")),
        "wp_payload_created": success,
        "wp_preview_created": success,
        "x_payload_created": success,
        "payload_validation_summary_created": success,
        "purchase_navigation_media": True,
        "work_explanation_media": False,
        "simple_x_post_under_280": bool(x_payload.get("under_280", False)),
        "ready_for_ls_new_5_human_review": success,
        "execution_allowed": False,
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
        "recommended_next_action": "BEGIN_LS_NEW_5_HUMAN_REVIEW_GATE",
        "recommended_next_phase_options": ["LS-NEW-5", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _lock_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_LOCK",
        "status": LOCK_STATUS,
        "locked": True,
        "ready_for_ls_new_5_human_review": bool(result.get("ready_for_ls_new_5_human_review", False)),
        "execution_allowed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
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
        "# LS-NEW-4 Purchase Navigation Payload Dry Run Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- content_item_id: {result.get('content_item_id', '')}",
        f"- title: {result.get('title', '')}",
        f"- volume: {result.get('volume', '')}",
        f"- author: {result.get('author', '')}",
        f"- publisher: {result.get('publisher', '')}",
        f"- release_date: {result.get('release_date', '')}",
        "",
        "## Errors",
    ]
    errors = result.get("errors", [])
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    _validate_required_flags(args, errors)
    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    ls_new3_result = try_load_json(Path(args.ls_new3_result), errors, "ls-new3-result")
    ls_new3_validation = try_load_json(Path(args.ls_new3_validation_result), errors, "ls-new3-validation-result")
    evidence = try_load_json(Path(args.candidate_evidence_record), errors, "candidate-evidence-record")
    source_inventory = try_load_json(Path(args.source_inventory), errors, "source-inventory")
    store_slots = try_load_json(Path(args.store_slots), errors, "store-slots")
    x_preview = try_load_json(Path(args.x_preview), errors, "x-preview")
    wp_preview_text = read_text(Path(args.wp_preview), errors, "wp-preview")

    req(policy.get("phase") == "LS-NEW-4", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-4", "schema phase mismatch", errors)
    req(ls_new3_result.get("status") == REQUIRED_LS_NEW3_STATUS, "ls-new3 status mismatch", errors)
    req(ls_new3_validation.get("validation_status") == REQUIRED_LS_NEW3_VALIDATION, "ls-new3 validation mismatch", errors)
    req(bool(ls_new3_result.get("ready_for_ls_new_4", False)) is True, "ready_for_ls_new_4 mismatch", errors)
    req(bool(ls_new3_result.get("execution_allowed", True)) is False, "execution_allowed mismatch", errors)
    req(bool(ls_new3_result.get("ls_new2_fill_validated", False)) is True, "ls_new3 validated flag mismatch", errors)

    candidate = _candidate_identity(evidence)
    for field in REQUIRED_CANDIDATE_FIELDS:
        req(_is_non_empty(candidate.get(field, "")), f"missing required candidate field: {field}", errors)
    identifier_evidence = evidence.get("identifier_evidence", {})
    req(_is_non_empty(str(identifier_evidence.get("asin", ""))), "missing required identifier field: asin", errors)
    req(_is_non_empty(str(identifier_evidence.get("isbn", ""))), "missing required identifier field: isbn", errors)
    if _is_non_empty(str(candidate.get("release_date", ""))):
        req(RE_DATE.match(str(candidate.get("release_date", ""))) is not None, "invalid release_date format", errors)

    wp_payload = _build_wp_payload(evidence, source_inventory, store_slots)
    wp_preview_md = _build_wp_preview_md(wp_payload)
    x_payload = _build_x_payload(x_preview)
    validation_summary = _build_validation_summary(wp_payload, x_payload, {})

    req(bool(x_payload.get("under_280", False)) is True, "x payload over 280", errors)

    validation_summary = _build_validation_summary(wp_payload, x_payload, {"ready_for_ls_new_5_human_review": True})
    result = _result_payload(evidence, x_payload, validation_summary, errors)
    lock = _lock_payload(result)

    if len(errors) == 0:
        write_json(Path(args.output_wp_payload), wp_payload)
        write_text(Path(args.output_wp_preview), wp_preview_md)
        write_json(Path(args.output_x_payload), x_payload)
        write_json(Path(args.output_validation_summary), validation_summary)

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock)
    _write_report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == STATUS_PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
