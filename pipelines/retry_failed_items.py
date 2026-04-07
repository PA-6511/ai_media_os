from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from article_generator.generator import generate_article_content
from article_planner.planner import generate_plan
from monitoring.failure_reporter import report_failed_item, report_give_up
from pipelines.enrich_article_with_journey import enrich_article_with_journey
from pipelines.enrich_article_with_links import enrich_article
from pipelines.publish_article_pipeline import publish_article
from pipelines.retry_policy import should_retry
from pipelines.retry_queue_store import (
    get_retry_candidates,
    increment_retry_count,
    mark_give_up,
    mark_resolved,
    mark_retrying,
)


def _to_bool(value: str, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def retry_one_item(queue_item: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    """キュー1件を再試行する。"""
    slug = str(queue_item.get("slug", "")).strip()
    retry_count = int(queue_item.get("retry_count", 0) or 0)
    max_retry_count = int(queue_item.get("max_retry_count", 3) or 3)

    print(f"slug: {slug}")
    print(f"retry_count: {retry_count}")

    item = {
        "work_id": str(queue_item.get("work_id", "")).strip(),
        "keyword": str(queue_item.get("keyword", "")).strip(),
        "article_type": str(queue_item.get("article_type", "")).strip(),
        "title": str(queue_item.get("title", "")).strip(),
    }

    if dry_run:
        print("- dry_run: would retry")
        return {
            "slug": slug,
            "success": True,
            "dry_run": True,
            "decision": "would_retry",
        }

    mark_retrying(slug)
    try:
        plan = generate_plan(item)
        article_output = generate_article_content(plan)
        with_links = enrich_article(article_output)
        with_journey = enrich_article_with_journey(with_links)
        result = publish_article(with_journey)

        if result.get("skipped"):
            print("- retry publish skipped")
            mark_resolved(slug)
            return {
                "slug": slug,
                "success": True,
                "skipped": True,
                "decision": result.get("decision", "skip_policy_blocked"),
                "reason": result.get("reason", ""),
            }

        if result.get("dry_run"):
            print("- retry dry_run")
            return {
                "slug": slug,
                "success": True,
                "dry_run": True,
                "decision": result.get("decision", "would_retry"),
                "reason": result.get("reason", ""),
            }

        print("- retry publish success")
        print(f"  post_id: {result.get('post_id')}")
        print(f"  link: {result.get('link')}")
        mark_resolved(slug)
        return {
            "slug": slug,
            "success": True,
            "post_id": result.get("post_id"),
            "link": result.get("link"),
            "decision": result.get("decision", "publish_new"),
            "reason": result.get("reason", ""),
        }
    except Exception as exc:
        error_text = str(exc)
        retry_decision = should_retry(
            error_message=error_text,
            retry_count=retry_count + 1,
            max_retry_count=max_retry_count,
        )

        if retry_decision.get("retryable"):
            next_retry_at = retry_decision.get("next_retry_at")
            increment_retry_count(slug, error_text, str(next_retry_at) if next_retry_at else None)
            report_failed_item(
                {
                    "slug": slug,
                    "work_id": item.get("work_id", ""),
                    "keyword": item.get("keyword", ""),
                    "article_type": item.get("article_type", ""),
                    "error_message": error_text,
                    "retryable": True,
                    "retry_count": retry_count + 1,
                    "dry_run": dry_run,
                }
            )
            print("- retry publish failed")
            print(f"  error: {error_text}")
            print(f"  next_retry_at: {next_retry_at}")
            return {
                "slug": slug,
                "success": False,
                "give_up": False,
                "error": error_text,
                "next_retry_at": next_retry_at,
                "reason": retry_decision.get("reason", ""),
            }

        mark_give_up(slug, error_text)
        report_give_up(
            {
                "slug": slug,
                "keyword": item.get("keyword", ""),
                "retry_count": retry_count + 1,
                "error_message": error_text,
            }
        )
        print("- give up")
        print(f"  reason: {retry_decision.get('reason', 'max_retry_exceeded')}")
        return {
            "slug": slug,
            "success": False,
            "give_up": True,
            "error": error_text,
            "reason": retry_decision.get("reason", "max_retry_exceeded"),
        }


def run_retry_batch(limit: int | None = None) -> dict[str, Any]:
    """retry_queue から再試行対象を取り出して処理する。"""
    dry_run = _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True)
    now_iso = datetime.now(timezone.utc).isoformat()
    candidates = get_retry_candidates(now_iso, limit=limit)

    total = len(candidates)
    print(f"retry candidates: {total}")

    results: list[dict[str, Any]] = []
    for index, queue_item in enumerate(candidates, start=1):
        print(f"\n[{index}/{total}] retry start")
        result = retry_one_item(queue_item, dry_run=dry_run)
        results.append(result)

    resolved_count = sum(1 for row in results if row.get("success") and not row.get("dry_run"))
    give_up_count = sum(1 for row in results if row.get("give_up"))
    failed_count = sum(1 for row in results if not row.get("success"))
    return {
        "total": total,
        "resolved_count": resolved_count,
        "failed_count": failed_count,
        "give_up_count": give_up_count,
        "results": results,
    }


def main() -> None:
    """CLI エントリ。"""
    limit_env = os.getenv("RETRY_BATCH_LIMIT", "").strip()
    limit = int(limit_env) if limit_env else None

    output = run_retry_batch(limit=limit)
    print("\nretry batch finished")
    print(f"total: {output.get('total', 0)}")
    print(f"resolved_count: {output.get('resolved_count', 0)}")
    print(f"failed_count: {output.get('failed_count', 0)}")
    print(f"give_up_count: {output.get('give_up_count', 0)}")


if __name__ == "__main__":
    main()
