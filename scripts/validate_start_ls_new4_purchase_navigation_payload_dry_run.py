#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_NOT_VALIDATED"
RUN_STATUS = "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_PASSED_NO_EXECUTION"
PRODUCTION_STATUS = "NO_EXECUTION_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_ONLY"
REQUIRED_LS_NEW3_VALIDATION = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new4_purchase_navigation_payload_dry_run_policy.json")
    p.add_argument("--schema", default="config/start_ls_new4_purchase_navigation_payload_schema.json")
    p.add_argument("--wp-payload", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_dry_run.json")
    p.add_argument("--wp-preview", default="exchange/new_release/start_ls_new4_wp_purchase_navigation_payload_preview.md")
    p.add_argument("--x-payload", default="exchange/new_release/start_ls_new4_x_post_payload_dry_run.json")
    p.add_argument("--validation-summary", default="exchange/new_release/start_ls_new4_payload_validation_summary.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new4_purchase_navigation_payload_dry_run_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new4_purchase_navigation_payload_dry_run.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new4_purchase_navigation_payload_dry_run_result.json")
    p.add_argument("--ls-new3-validation-result", default="exchange/logs/start_ls_new3_candidate_evidence_dry_run_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new4_purchase_navigation_payload_dry_run_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new4_purchase_navigation_payload_dry_run_validation_report.md")
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


def _validate_wp_payload(wp_payload: dict[str, Any], errors: list[str]) -> None:
    req(wp_payload.get("phase") == "LS-NEW-4", "wp payload phase mismatch", errors)
    req(wp_payload.get("document_type") == "START_LS_NEW4_WP_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN", "wp payload document_type mismatch", errors)
    req(bool(wp_payload.get("generated", False)) is True, "wp payload generated mismatch", errors)
    req(bool(wp_payload.get("wordpress_write_executed", True)) is False, "wordpress_write_executed=true", errors)
    req(bool(wp_payload.get("wordpress_api_call_executed", True)) is False, "wordpress_api_call_executed=true", errors)
    req(wp_payload.get("post_status_target") == "draft", "post_status_target mismatch", errors)
    candidate = wp_payload.get("candidate_identity", {})
    req(isinstance(candidate, dict), "candidate_identity missing", errors)
    if isinstance(candidate, dict):
        req(_text_contains(wp_payload.get("post_title", ""), candidate.get("title", "")), "wp post_title missing title", errors)
        req(_text_contains(wp_payload.get("post_title", ""), candidate.get("volume", "")), "wp post_title missing volume", errors)
        req(_text_contains(wp_payload.get("post_title", ""), candidate.get("release_date", "")), "wp post_title missing release_date", errors)
    req("このページにはPR・アフィリエイトリンクを含む場合があります。" in str(wp_payload.get("affiliate_disclosure", "")), "affiliate disclosure mismatch", errors)
    req("外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。" in str(wp_payload.get("external_fetch_notice", "")), "external fetch notice mismatch", errors)
    body = str(wp_payload.get("body_markdown", ""))
    req("# 【" in body, "wp body missing heading", errors)
    req("## 基本情報" in body, "wp body missing basic info section", errors)
    req("## 販売ストア候補" in body, "wp body missing store section", errors)
    req("## 確認状態" in body, "wp body missing confirmation section", errors)
    req("## PR表記" in body, "wp body missing PR section", errors)
    req("月曜日のたわわ" in body, "wp body missing title", errors)
    req("第15巻" in body, "wp body missing volume", errors)
    req("2026-07-06" in body, "wp body missing release date", errors)
    req("このページにはPR・アフィリエイトリンクを含む場合があります。" in body, "wp body missing PR disclosure", errors)
    req("外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。" in body, "wp body missing external fetch notice", errors)
    req("月曜日のたわわの発売日・販売ストア候補" not in body, "wp body includes synopsis-like phrasing", errors)
    req("あらすじ" not in body, "wp body includes synopsis copy", errors)
    req("レビュー" not in body, "wp body includes review copy", errors)
    req("作品解説" not in body, "wp body includes work explanation", errors)


def _text_contains(text: Any, fragment: Any) -> bool:
    return str(fragment) != "" and str(fragment) in str(text)


def _validate_x_payload(x_payload: dict[str, Any], errors: list[str]) -> None:
    post_text = str(x_payload.get("post_text", ""))
    req(x_payload.get("phase") == "LS-NEW-4", "x payload phase mismatch", errors)
    req(x_payload.get("document_type") == "START_LS_NEW4_X_POST_PAYLOAD_DRY_RUN", "x payload document_type mismatch", errors)
    req(bool(x_payload.get("generated", False)) is True, "x payload generated mismatch", errors)
    req(bool(x_payload.get("x_post_executed", True)) is False, "x_post_executed=true", errors)
    req(bool(x_payload.get("x_api_call_executed", True)) is False, "x_api_call_executed=true", errors)
    req(bool(x_payload.get("under_280", False)) is True, "x payload over 280", errors)
    req(int(x_payload.get("character_count", 0)) <= 280, "x payload character_count over 280", errors)
    req("#PR" in post_text, "x payload missing #PR", errors)
    req("#Amazonmanga" in post_text, "x payload missing #Amazonmanga", errors)
    req("#Kindle" in post_text, "x payload missing #Kindle", errors)
    req("#比村奇石" in post_text, "x payload missing author hashtag", errors)
    req("月曜日のたわわ" in post_text, "x payload missing title", errors)
    req("URL" in post_text, "x payload missing URL placeholder", errors)
    req(bool(x_payload.get("contains_pr", False)) is True, "contains_pr mismatch", errors)
    req(bool(x_payload.get("contains_title", False)) is True, "contains_title mismatch", errors)
    req(bool(x_payload.get("contains_author_hashtag", False)) is True, "contains_author_hashtag mismatch", errors)
    req(bool(x_payload.get("contains_url_placeholder", False)) is True, "contains_url_placeholder mismatch", errors)
    content_policy = x_payload.get("content_policy", {})
    req(isinstance(content_policy, dict), "x content_policy missing", errors)
    if isinstance(content_policy, dict):
        req(bool(content_policy.get("synopsis_included", False)) is False, "synopsis_included=true", errors)
        req(bool(content_policy.get("price_comparison_required", False)) is False, "price_comparison_required=true", errors)
        req(bool(content_policy.get("point_reward_rate_required", False)) is False, "point_reward_rate_required=true", errors)
        req(bool(content_policy.get("store_comparison_required", False)) is False, "store_comparison_required=true", errors)
        req(bool(content_policy.get("long_work_explanation_included", False)) is False, "long_work_explanation_included=true", errors)


def _validate_validation_summary(summary: dict[str, Any], errors: list[str]) -> None:
    req(summary.get("phase") == "LS-NEW-4", "validation summary phase mismatch", errors)
    req(summary.get("document_type") == "START_LS_NEW4_PAYLOAD_VALIDATION_SUMMARY", "validation summary document_type mismatch", errors)
    req(bool(summary.get("wp_payload_valid", False)) is True, "wp_payload_valid mismatch", errors)
    req(bool(summary.get("x_payload_valid", False)) is True, "x_payload_valid mismatch", errors)
    req(bool(summary.get("purchase_navigation_media", False)) is True, "purchase_navigation_media mismatch", errors)
    req(bool(summary.get("work_explanation_media", True)) is False, "work_explanation_media mismatch", errors)
    req(bool(summary.get("official_synopsis_copy_included", True)) is False, "official_synopsis_copy_included mismatch", errors)
    req(bool(summary.get("store_description_copy_included", True)) is False, "store_description_copy_included mismatch", errors)
    req(bool(summary.get("review_copy_included", True)) is False, "review_copy_included mismatch", errors)
    req(bool(summary.get("x_post_under_280", False)) is True, "x_post_under_280 mismatch", errors)
    req(bool(summary.get("external_fetch_executed", True)) is False, "external_fetch_executed mismatch", errors)
    req(bool(summary.get("wordpress_write_executed", True)) is False, "wordpress_write_executed mismatch", errors)
    req(bool(summary.get("x_post_executed", True)) is False, "x_post_executed mismatch", errors)
    req(bool(summary.get("ready_for_ls_new_5_human_review", False)) is True, "ready_for_ls_new_5_human_review mismatch", errors)
    req(bool(summary.get("execution_allowed", True)) is False, "execution_allowed=true", errors)


def _validate_result(result: dict[str, Any], errors: list[str]) -> None:
    req(result.get("phase") == "LS-NEW-4", "result phase mismatch", errors)
    req(result.get("status") == RUN_STATUS, "result status mismatch", errors)
    req(result.get("production_status") == PRODUCTION_STATUS, "result production_status mismatch", errors)
    req(bool(result.get("ls_new3_validated", False)) is True, "ls_new3_validated mismatch", errors)
    req(bool(result.get("wp_payload_created", False)) is True, "wp_payload_created mismatch", errors)
    req(bool(result.get("wp_preview_created", False)) is True, "wp_preview_created mismatch", errors)
    req(bool(result.get("x_payload_created", False)) is True, "x_payload_created mismatch", errors)
    req(bool(result.get("payload_validation_summary_created", False)) is True, "payload_validation_summary_created mismatch", errors)
    req(bool(result.get("purchase_navigation_media", False)) is True, "purchase_navigation_media mismatch", errors)
    req(bool(result.get("work_explanation_media", True)) is False, "work_explanation_media mismatch", errors)
    req(bool(result.get("simple_x_post_under_280", False)) is True, "simple_x_post_under_280 mismatch", errors)
    req(bool(result.get("ready_for_ls_new_5_human_review", False)) is True, "ready_for_ls_new_5_human_review mismatch", errors)
    req(bool(result.get("execution_allowed", True)) is False, "execution_allowed=true", errors)
    must_false = [
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(bool(result.get(key, False)) is False, f"{key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-4", "lock phase mismatch", errors)
    req(lock.get("status") == "LSNEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(lock.get("locked", False)) is True, "lock locked mismatch", errors)
    req(bool(lock.get("ready_for_ls_new_5_human_review", False)) is True, "lock ready_for_ls_new_5_human_review mismatch", errors)
    req(bool(lock.get("execution_allowed", True)) is False, "lock execution_allowed=true", errors)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-4 Purchase Navigation Payload Dry Run Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        "",
        "## Errors",
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    wp_payload = try_load_json(Path(args.wp_payload), errors, "wp-payload")
    wp_preview = read_text(Path(args.wp_preview), errors, "wp-preview")
    x_payload = try_load_json(Path(args.x_payload), errors, "x-payload")
    validation_summary = try_load_json(Path(args.validation_summary), errors, "validation-summary")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls_new3_validation = try_load_json(Path(args.ls_new3_validation_result), errors, "ls-new3-validation-result")

    req(policy.get("phase") == "LS-NEW-4", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-4", "schema phase mismatch", errors)
    req(ls_new3_validation.get("validation_status") == REQUIRED_LS_NEW3_VALIDATION, "ls-new3 validation mismatch", errors)
    req(result == run_result, "result and run_result mismatch", errors)

    _validate_wp_payload(wp_payload, errors)
    _validate_x_payload(x_payload, errors)
    _validate_validation_summary(validation_summary, errors)
    _validate_result(result, errors)
    _validate_lock(lock, errors)

    req(str(wp_payload.get("post_title", "")) in wp_preview, "wp preview missing post title", errors)
    req("WordPress write executed: false" in wp_preview, "wp preview missing wordpress write marker", errors)
    req("このpayloadは人間入力値とLS-NEW-3証跡のみを元にしたDRY_RUNです。" in wp_preview, "wp preview missing dry run notice", errors)

    validation_status = VALIDATED if len(errors) == 0 else NOT_VALIDATED
    payload = {
        "phase": "LS-NEW-4",
        "document_type": "START_LS_NEW4_PURCHASE_NAVIGATION_PAYLOAD_DRY_RUN_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), payload)
    _write_report(Path(args.report), payload)
    print(validation_status)
    return 0 if validation_status == VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
