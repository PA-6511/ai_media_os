#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_PASSED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_FAILED_NO_EXECUTION"
LOCK_STATUS = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_LOCKED_NO_EXECUTION"
REQUIRED_LS_NEW2_STATUS = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION"
REQUIRED_LS_NEW2_VALIDATION = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SOURCE_FIELD_BY_STORE = {
    "publisher_official": "publisher_source_url",
    "kindle": "kindle_url",
    "rakuten_kobo": "rakuten_kobo_url",
    "dmm_books": "dmm_books_url",
    "ebookjapan": "ebookjapan_url",
    "booklive": "booklive_url",
    "manual_source": "manual_source_url",
}

SOURCE_URL_FIELDS = [
    "publisher_source_url",
    "kindle_url",
    "rakuten_kobo_url",
    "dmm_books_url",
    "ebookjapan_url",
    "booklive_url",
    "manual_source_url",
]

REQUIRED_CANDIDATE_FIELDS = [
    "content_item_id",
    "title",
    "volume",
    "author",
    "publisher",
    "release_date",
    "candidate_source_type",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new3_candidate_evidence_dry_run_policy.json")
    p.add_argument("--schema", default="config/start_ls_new3_candidate_evidence_schema.json")
    p.add_argument("--ls-new2-fill-result", default="exchange/runtime/start_ls_new2_fill_human_new_release_comic_candidate_result.json")
    p.add_argument("--ls-new2-fill-validation-result", default="exchange/logs/start_ls_new2_fill_human_new_release_comic_candidate_validation_result.json")
    p.add_argument("--filled-candidate-record", default="exchange/new_release/start_ls_new2_filled_new_release_comic_candidate_intake.json")
    p.add_argument("--output-evidence", default="exchange/new_release/start_ls_new3_candidate_evidence_dry_run.json")
    p.add_argument("--output-source-inventory", default="exchange/new_release/start_ls_new3_source_url_inventory.json")
    p.add_argument("--output-store-slots", default="exchange/new_release/start_ls_new3_store_evidence_slots.json")
    p.add_argument("--output-x-preview", default="exchange/new_release/start_ls_new3_simple_x_post_preview.json")
    p.add_argument("--output-wp-preview", default="exchange/new_release/start_ls_new3_wp_purchase_navigation_preview.md")
    p.add_argument("--output", default="exchange/runtime/start_ls_new3_candidate_evidence_dry_run_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new3_candidate_evidence_dry_run.lock.json")
    p.add_argument("--report", default="reports/start_ls_new3_candidate_evidence_dry_run_report.md")

    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-http-get", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
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


def _build_source_inventory(filled: dict[str, Any]) -> dict[str, Any]:
    inventory: dict[str, Any] = {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_SOURCE_URL_INVENTORY",
    }
    for field in SOURCE_URL_FIELDS:
        url = str(filled.get(field, ""))
        present = _is_non_empty(url)
        inventory[field] = {
            "present": present,
            "url": url if present else "",
            "fetch_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED" if present else "NOT_PROVIDED",
        }
    return inventory


def _build_store_slots(filled: dict[str, Any]) -> dict[str, Any]:
    slots: dict[str, Any] = {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_STORE_EVIDENCE_SLOTS",
        "slots": [],
    }
    for store, source_field in SOURCE_FIELD_BY_STORE.items():
        url = str(filled.get(source_field, ""))
        present = _is_non_empty(url)
        slots["slots"].append(
            {
                "store": store,
                "url_present": present,
                "url": url if present else "",
                "price": None,
                "point_reward_rate": None,
                "reservation_status": "UNKNOWN_NOT_FETCHED",
                "delivery_status": "UNKNOWN_NOT_FETCHED",
                "fetch_executed": False,
                "api_call_executed": False,
                "verification_status": "DRY_RUN_NOT_FETCHED" if present else "NOT_PROVIDED",
            }
        )
    return slots


def _build_simple_x_preview(filled: dict[str, Any]) -> dict[str, Any]:
    title = str(filled.get("title", "")).strip()
    volume = str(filled.get("volume", "")).strip()
    author = str(filled.get("author", "")).strip()
    author_hashtag = f"#{author}" if author else "#作者名"
    post_text = "\n".join(
        [
            "配信開始です",
            f"#PR #Amazonmanga #Kindle {author_hashtag}",
            f"『{title}』{volume}",
            "",
            "URL",
        ]
    )
    count = len(post_text)
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_SIMPLE_X_POST_PREVIEW",
        "generated": True,
        "x_post_executed": False,
        "template_source": "LS-NEW-2 simple template",
        "post_text": post_text,
        "character_count": count,
        "under_280": count <= 280,
        "contains_pr": "#PR" in post_text,
        "contains_title": title in post_text if title else False,
        "contains_author_hashtag": author_hashtag in post_text,
        "contains_url_placeholder": "URL" in post_text,
    }


def _wp_status(present: bool) -> str:
    return "URL入力あり / 未取得" if present else "URL未入力"


def _build_wp_preview_text(filled: dict[str, Any], inventory: dict[str, Any]) -> str:
    title = str(filled.get("title", ""))
    volume = str(filled.get("volume", ""))
    author = str(filled.get("author", ""))
    publisher = str(filled.get("publisher", ""))
    release_date = str(filled.get("release_date", ""))
    asin = str(filled.get("asin", ""))
    isbn = str(filled.get("isbn", ""))

    draft_title = f"【{release_date}発売】{title} {volume} 電子書籍ストア候補"

    return "\n".join(
        [
            "# LS-NEW-3 WordPress Purchase Navigation Preview",
            "",
            "- Phase: LS-NEW-3",
            "- Execution: NO_EXECUTION / PREVIEW_ONLY",
            "- WordPress write executed: false",
            "",
            "## Candidate",
            "",
            f"- Title: {title}",
            f"- Volume: {volume}",
            f"- Author: {author}",
            f"- Publisher: {publisher}",
            f"- Release date: {release_date}",
            f"- ASIN: {asin}",
            f"- ISBN: {isbn}",
            "",
            "## Purchase Navigation Draft Preview",
            "",
            draft_title,
            "",
            "配信・販売ストア候補:",
            f"- 出版社公式: {_wp_status(bool(inventory['publisher_source_url']['present']))}",
            f"- Kindle: {_wp_status(bool(inventory['kindle_url']['present']))}",
            f"- 楽天Kobo: {_wp_status(bool(inventory['rakuten_kobo_url']['present']))}",
            f"- DMMブックス: {_wp_status(bool(inventory['dmm_books_url']['present']))}",
            f"- ebookjapan: {_wp_status(bool(inventory['ebookjapan_url']['present']))}",
            f"- BookLive: {_wp_status(bool(inventory['booklive_url']['present']))}",
            "",
            "確認状態:",
            "このプレビューは人間入力値のみを元にしたDRY_RUNです。",
            "外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。",
            "",
        ]
    )


def _build_evidence_record(
    filled: dict[str, Any],
    source_inventory: dict[str, Any],
    store_slots: dict[str, Any],
    x_preview: dict[str, Any],
) -> dict[str, Any]:
    release_date = str(filled.get("release_date", ""))
    title = str(filled.get("title", ""))
    volume = str(filled.get("volume", ""))

    return {
        "document_type": "START_LS_NEW3_CANDIDATE_EVIDENCE_DRY_RUN_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-3",
        "status": "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_READY_NO_EXECUTION",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "source_of_truth": "exchange/new_release/start_ls_new2_filled_new_release_comic_candidate_intake.json",
        "candidate_identity": {
            "content_item_id": str(filled.get("content_item_id", "")),
            "title": title,
            "volume": volume,
            "author": str(filled.get("author", "")),
            "publisher": str(filled.get("publisher", "")),
            "label": str(filled.get("label", "")),
            "release_date": release_date,
            "ebook_release_date": str(filled.get("ebook_release_date", "")),
            "paper_release_date": str(filled.get("paper_release_date", "")),
        },
        "release_evidence": {
            "release_date": release_date,
            "candidate_source_type": str(filled.get("candidate_source_type", "")),
            "source_pending": bool(filled.get("source_pending", True)),
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "identifier_evidence": {
            "asin": str(filled.get("asin", "")),
            "isbn": str(filled.get("isbn", "")),
            "asin_lookup_executed": False,
            "isbn_lookup_executed": False,
            "verification_status": "DRY_RUN_NOT_FETCHED",
        },
        "source_url_inventory": {
            k: source_inventory[k] for k in SOURCE_URL_FIELDS
        },
        "store_evidence_slots": list(store_slots.get("slots", [])),
        "simple_x_post_preview": {
            "generated": True,
            "post_text": str(x_preview.get("post_text", "")),
            "under_280": bool(x_preview.get("under_280", False)),
            "x_post_executed": False,
        },
        "wordpress_purchase_navigation_preview": {
            "generated": True,
            "title": f"【{release_date}発売】{title} {volume} 電子書籍ストア候補",
            "body_preview_created": True,
            "wordpress_write_executed": False,
        },
        "safety": {
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
            "execution_allowed": False,
        },
    }


def _result_payload(filled: dict[str, Any], x_preview: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    success = len(errors) == 0
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_CANDIDATE_EVIDENCE_DRY_RUN_RESULT",
        "status": STATUS_PASSED if success else STATUS_FAILED,
        "execution_mode": "CANDIDATE_EVIDENCE_DRY_RUN_ONLY_NO_EXTERNAL_FETCH",
        "production_status": "NO_EXECUTION_CANDIDATE_EVIDENCE_DRY_RUN_ONLY",
        "ls_new2_fill_validated": success,
        "content_item_id": str(filled.get("content_item_id", "")),
        "title": str(filled.get("title", "")),
        "volume": str(filled.get("volume", "")),
        "author": str(filled.get("author", "")),
        "publisher": str(filled.get("publisher", "")),
        "release_date": str(filled.get("release_date", "")),
        "asin": str(filled.get("asin", "")),
        "isbn": str(filled.get("isbn", "")),
        "source_url_inventory_created": success,
        "store_evidence_slots_created": success,
        "simple_x_post_preview_created": success,
        "simple_x_post_under_280": bool(x_preview.get("under_280", False)),
        "wp_purchase_navigation_preview_created": success,
        "ready_for_ls_new_4": success,
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
        "recommended_next_action": "BEGIN_LS_NEW_4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN",
        "recommended_next_phase_options": ["LS-NEW-4", "LS-MON-2"],
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _lock_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_CANDIDATE_EVIDENCE_DRY_RUN_LOCK",
        "status": LOCK_STATUS,
        "locked": True,
        "ready_for_ls_new_4": bool(result.get("ready_for_ls_new_4", False)),
        "execution_allowed": False,
        "external_fetch_executed": False,
        "http_get_executed": False,
        "wordpress_api_call_executed": False,
        "x_post_executed": False,
        "credential_env_read_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-3 Candidate Evidence Dry Run Report",
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
    ls_new2_result = try_load_json(Path(args.ls_new2_fill_result), errors, "ls-new2-fill-result")
    ls_new2_validation = try_load_json(Path(args.ls_new2_fill_validation_result), errors, "ls-new2-fill-validation-result")
    filled = try_load_json(Path(args.filled_candidate_record), errors, "filled-candidate-record")

    req(policy.get("phase") == "LS-NEW-3", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-3", "schema phase mismatch", errors)

    req(ls_new2_result.get("status") == REQUIRED_LS_NEW2_STATUS, "ls-new2-fill status mismatch", errors)
    req(ls_new2_validation.get("validation_status") == REQUIRED_LS_NEW2_VALIDATION, "ls-new2-fill validation mismatch", errors)
    req(bool(ls_new2_result.get("ready_for_ls_new_3", False)) is True, "ls-new2-fill ready_for_ls_new_3 mismatch", errors)
    req(bool(ls_new2_result.get("execution_allowed", True)) is False, "ls-new2-fill execution_allowed mismatch", errors)
    req(list(ls_new2_result.get("missing_required_human_fields", ["x"])) == [], "ls-new2-fill missing_required_human_fields mismatch", errors)

    for field in REQUIRED_CANDIDATE_FIELDS:
        req(_is_non_empty(filled.get(field, "")), f"missing required candidate field: {field}", errors)
    if _is_non_empty(filled.get("release_date", "")):
        req(RE_DATE.match(str(filled.get("release_date", ""))) is not None, "invalid release_date format", errors)

    source_inventory = _build_source_inventory(filled)
    store_slots = _build_store_slots(filled)
    x_preview = _build_simple_x_preview(filled)
    wp_preview_text = _build_wp_preview_text(filled, source_inventory)
    evidence = _build_evidence_record(filled, source_inventory, store_slots, x_preview)

    req(bool(x_preview.get("under_280", False)) is True, "simple x post preview exceeds 280", errors)

    result = _result_payload(filled, x_preview, errors)
    lock = _lock_payload(result)

    if len(errors) == 0:
        write_json(Path(args.output_evidence), evidence)
        write_json(Path(args.output_source_inventory), source_inventory)
        write_json(Path(args.output_store_slots), store_slots)
        write_json(Path(args.output_x_preview), x_preview)
        write_text(Path(args.output_wp_preview), wp_preview_text)

    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock)
    _write_report(Path(args.report), result)

    print(result["status"])
    return 0 if result["status"] == STATUS_PASSED else 1


if __name__ == "__main__":
    raise SystemExit(main())
