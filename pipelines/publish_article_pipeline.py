from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from config.core_runtime_config import get_retry_max_retry_count
from monitoring.failure_reporter import report_failed_item, report_retry_enqueued
from pipelines.publish_guard import should_publish
from pipelines.publish_history import build_record, save_publish_record
from pipelines.post_status_store import build_status_record, upsert_status
from pipelines.retry_policy import should_retry
from pipelines.retry_queue_store import build_retry_record, enqueue_failed_item
from pipelines.wp_post_enricher import enrich_wp_post
from wordpress_publisher.publisher import WordPressPublisher


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ARTICLE_OUTPUT_PATH = DATA_DIR / "article_output_with_journey.json"


def _to_bool(value: str, default: bool = False) -> bool:
    """環境変数文字列を bool に変換する。"""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def load_article_output(path: Path) -> dict[str, Any]:
    """article_output_with_journey.json を読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"article_output_with_journey.json のJSON形式が不正です: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"article_output_with_journey.json の読み込みに失敗しました: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("article_output_with_journey.json はオブジェクト形式である必要があります")

    return data


def build_wp_article(article_output: dict[str, Any]) -> dict[str, Any]:
    """article_output から WordPress 投稿用 article dict を生成する。"""
    enriched = enrich_wp_post(article_output)
    return {
        "title": str(enriched.get("title", "")).strip(),
        "content": str(article_output.get("content_html", enriched.get("content", ""))).strip(),
        "slug": str(enriched.get("slug", "")).strip(),
        "category_names": enriched.get("category_names", []),
        "tag_names": enriched.get("tag_names", []),
        # ログ確認用の補助情報
        "work_id": str(article_output.get("work_id", "")).strip(),
        "keyword": str(article_output.get("keyword", "")).strip(),
        "article_type": str(article_output.get("article_type", "")).strip(),
        "price_changed": bool(article_output.get("price_changed", False)),
        "previous_price": article_output.get("previous_price"),
        "current_price": article_output.get("current_price"),
        "discount_rate": article_output.get("discount_rate"),
        "price_diff": article_output.get("price_diff"),
        "change_reason": str(article_output.get("change_reason", "no_change")),
        "release_changed": bool(article_output.get("release_changed", False)),
        "release_change_reason": str(article_output.get("release_change_reason", "no_change")),
        "previous_latest_volume_number": article_output.get("previous_latest_volume_number"),
        "current_latest_volume_number": article_output.get("current_latest_volume_number"),
        "related_links": article_output.get("related_links", []),
        "journey": article_output.get("journey", {}),
    }


def create_publisher_from_env() -> tuple[WordPressPublisher, bool]:
    """環境変数から WordPressPublisher を初期化し dry_run 設定も返す。"""
    base_url = os.getenv("WP_BASE_URL", "").strip()
    username = os.getenv("WP_USERNAME", "").strip()
    app_password = os.getenv("WP_APP_PASSWORD", "").strip()
    dry_run = _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True)

    missing: list[str] = []
    if not base_url:
        missing.append("WP_BASE_URL")
    if not username:
        missing.append("WP_USERNAME")
    if not app_password:
        missing.append("WP_APP_PASSWORD")

    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"必要な環境変数が不足しています: {missing_text}")

    publisher = WordPressPublisher(
        base_url=base_url,
        username=username,
        application_password=app_password,
        default_status="draft",
    )
    return publisher, dry_run


def publish_article(article_output_with_journey: dict[str, Any]) -> dict[str, Any]:
    """1件分の article_output_with_journey を受け取り、WordPressへ投稿する。"""
    wp_article = build_wp_article(article_output_with_journey)
    slug = str(wp_article.get("slug", "")).strip()
    publisher, dry_run = create_publisher_from_env()

    try:
        guard_result = should_publish(wp_article, publisher.client)
        decision = str(guard_result.get("decision", "skip_policy_blocked"))
        reason = str(guard_result.get("reason", "policy_blocked"))
        if not guard_result.get("should_publish"):
            if dry_run:
                dry_decision = "would_skip_policy_blocked"
                if decision == "skip_already_published":
                    dry_decision = "would_skip_already_published"
                return {
                    "dry_run": True,
                    "skipped": True,
                    "decision": dry_decision,
                    "reason": reason,
                    "slug": guard_result.get("slug", ""),
                    "existing_post_id": guard_result.get("existing_post_id"),
                    "existing_link": guard_result.get("existing_link"),
                    "check_source": guard_result.get("source", ""),
                }

            # 本投稿時の skip は現在ステータスへ反映する。
            skipped_record = build_status_record(
                slug=slug,
                work_id=str(article_output_with_journey.get("work_id", "")),
                keyword=str(article_output_with_journey.get("keyword", "")),
                article_type=str(article_output_with_journey.get("article_type", "")),
                title=str(article_output_with_journey.get("title", "")),
                status="skipped",
                post_id=guard_result.get("existing_post_id"),
                link=str(guard_result.get("existing_link", "")),
                error_message=None,
            )
            upsert_status(skipped_record)

            return {
                "dry_run": False,
                "skipped": True,
                "decision": decision,
                "reason": reason,
                "slug": guard_result.get("slug", ""),
                "existing_post_id": guard_result.get("existing_post_id"),
                "existing_link": guard_result.get("existing_link"),
                "check_source": guard_result.get("source", ""),
            }

        result = publisher.publish(wp_article, dry_run=dry_run)
        if result.get("dry_run"):
            dry_decision = "would_publish_new"
            if decision == "republish_allowed":
                dry_decision = "would_republish"
            elif decision == "retry_failed":
                dry_decision = "would_retry_failed"
            elif decision == "republish_allowed_release_changed":
                dry_decision = "would_republish_release_changed"
            elif decision == "republish_allowed_price_changed":
                dry_decision = "would_republish_price_changed"
            elif decision == "republish_allowed_combined_signal":
                dry_decision = "would_republish_combined_signal"
            return {
                "dry_run": True,
                "skipped": False,
                "decision": dry_decision,
                "reason": reason,
                "slug": slug,
                "request_payload": result.get("request_payload", {}),
            }

        # 投稿成功時のみ履歴保存する。dry_run 時は保存しない。
        post_status_raw = str(result.get("status", "")).strip().lower()
        current_status = "published" if post_status_raw == "publish" else (post_status_raw or "draft")

        record = build_record(
            slug=slug,
            article_output_with_journey=article_output_with_journey,
            post_id=result.get("post_id"),
            link=str(result.get("link", "")),
            status=post_status_raw,
        )
        save_publish_record(record)

        status_record = build_status_record(
            slug=slug,
            work_id=str(article_output_with_journey.get("work_id", "")),
            keyword=str(article_output_with_journey.get("keyword", "")),
            article_type=str(article_output_with_journey.get("article_type", "")),
            title=str(article_output_with_journey.get("title", "")),
            status=current_status,
            post_id=result.get("post_id"),
            link=str(result.get("link", "")),
            error_message=None,
        )
        upsert_status(status_record)

        return {
            "dry_run": False,
            "skipped": False,
            "decision": decision,
            "reason": reason,
            "republished": decision in {
                "republish_allowed",
                "retry_failed",
                "republish_allowed_price_changed",
                "republish_allowed_release_changed",
                "republish_allowed_combined_signal",
            },
            "slug": slug,
            "post_id": result.get("post_id"),
            "status": result.get("status"),
            "link": result.get("link"),
        }
    except Exception as exc:
        # 投稿失敗を現在ステータスへ記録する。
        error_text = str(exc)
        failed_record = build_status_record(
            slug=slug,
            work_id=str(article_output_with_journey.get("work_id", "")),
            keyword=str(article_output_with_journey.get("keyword", "")),
            article_type=str(article_output_with_journey.get("article_type", "")),
            title=str(article_output_with_journey.get("title", "")),
            status="failed",
            post_id=None,
            link=None,
            error_message=error_text,
        )
        upsert_status(failed_record)

        # dry_run では副作用を抑えるため retry queue には積まない。
        if not dry_run:
            default_max_retry_count = get_retry_max_retry_count()
            retry_decision = should_retry(error_text, retry_count=0, max_retry_count=default_max_retry_count)
            report_failed_item(
                {
                    "slug": slug,
                    "work_id": str(article_output_with_journey.get("work_id", "")),
                    "keyword": str(article_output_with_journey.get("keyword", "")),
                    "article_type": str(article_output_with_journey.get("article_type", "")),
                    "error_message": error_text,
                    "retryable": bool(retry_decision.get("retryable")),
                    "retry_count": 0,
                    "dry_run": dry_run,
                }
            )
            if retry_decision.get("retryable"):
                retry_record = build_retry_record(
                    slug=slug,
                    work_id=str(article_output_with_journey.get("work_id", "")),
                    keyword=str(article_output_with_journey.get("keyword", "")),
                    article_type=str(article_output_with_journey.get("article_type", "")),
                    title=str(article_output_with_journey.get("title", "")),
                    last_error=error_text,
                    retry_count=0,
                    max_retry_count=int(retry_decision.get("max_retry_count", default_max_retry_count) or default_max_retry_count),
                    retry_status="queued",
                    next_retry_at=str(retry_decision.get("next_retry_at", "")) or None,
                )
                enqueue_failed_item(retry_record)
                report_retry_enqueued(
                    {
                        "slug": slug,
                        "reason": str(retry_decision.get("reason", "")),
                        "retry_count": 0,
                        "max_retry_count": int(retry_decision.get("max_retry_count", default_max_retry_count) or default_max_retry_count),
                        "next_retry_at": str(retry_decision.get("next_retry_at", "")),
                    }
                )
        else:
            report_failed_item(
                {
                    "slug": slug,
                    "work_id": str(article_output_with_journey.get("work_id", "")),
                    "keyword": str(article_output_with_journey.get("keyword", "")),
                    "article_type": str(article_output_with_journey.get("article_type", "")),
                    "error_message": error_text,
                    "retryable": False,
                    "retry_count": 0,
                    "dry_run": dry_run,
                }
            )
        raise


def run() -> dict[str, Any]:
    """article_output_with_journey を読み込み、WordPress へ draft 投稿する。"""
    article_output = load_article_output(ARTICLE_OUTPUT_PATH)
    return publish_article(article_output)


def main() -> None:
    """publish_article_pipeline のCLIエントリ。"""
    try:
        output = run()
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except Exception as exc:
        error_output = {
            "error": str(exc),
            "hint": "WP環境変数・article_output_with_journey.json・WordPress接続設定を確認してください",
        }
        print(json.dumps(error_output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
