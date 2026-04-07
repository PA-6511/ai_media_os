from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from main import run_pipeline
from monitoring.combined_signal_reporter import (
    build_combined_signal_batch_summary,
    report_combined_signal,
    report_combined_signal_batch_summary,
)


def _to_bool(value: str, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_max_items(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"", "none", "all", "*"}:
        return None

    parsed = int(text)
    if parsed <= 0:
        raise ValueError("MAX_ITEMS は 1 以上の整数か None/all を指定してください")
    return parsed


def _normalize_event(row: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    """run_pipeline の1件結果を新刊イベント形式に揃える。"""
    decision = str(row.get("decision", "")).strip()
    if not decision and not row.get("success"):
        decision = "failed_before_decision"
    if not decision:
        decision = "unknown"

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "work_id": row.get("work_id", ""),
        "title": row.get("title", ""),
        "keyword": row.get("keyword", ""),
        "article_type": row.get("article_type", ""),
        "slug": row.get("slug", ""),
        "previous_latest_volume_number": row.get("previous_latest_volume_number"),
        "current_latest_volume_number": row.get("current_latest_volume_number"),
        "previous_latest_release_date": row.get("previous_latest_release_date"),
        "current_latest_release_date": row.get("current_latest_release_date"),
        "previous_availability_status": row.get("previous_availability_status"),
        "current_availability_status": row.get("current_availability_status"),
        "availability_status": row.get("current_availability_status", row.get("availability_status", "")),
        "release_change_reason": row.get("release_change_reason", "no_change"),
        "release_changed": bool(row.get("release_changed", False)),
        "price_changed": bool(row.get("price_changed", False)),
        "change_reason": row.get("change_reason", "no_change"),
        "priority": row.get("priority", ""),
        "decision": decision,
        "reason": row.get("reason", ""),
        "related_links": row.get("related_links", []),
        "internal_link_hints": row.get("internal_link_hints", []),
        "journey": row.get("journey"),
        "sub_reasons": row.get("sub_reasons", []),
        "dry_run": dry_run,
        "skipped": bool(row.get("skipped", False)),
    }


def main() -> None:
    """新刊イベント対象の記事を優先再生成する。"""
    max_items = _parse_max_items(os.getenv("MAX_ITEMS", "None"))
    save_per_item_files = _to_bool(os.getenv("SAVE_PER_ITEM_FILES", "1"), default=True)
    dry_run = _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True)

    result = run_pipeline(
        max_items=max_items,
        only_sale_articles=False,
        only_release_changed_articles=True,
        save_per_item_files=save_per_item_files,
    )

    raw_results = result.get("results", [])
    normalized_results: list[dict[str, Any]] = []
    if isinstance(raw_results, list):
        for row in raw_results:
            if not isinstance(row, dict):
                continue
            event = _normalize_event(row, dry_run=dry_run)
            normalized_results.append(event)
            report_combined_signal(event)

    summary = build_combined_signal_batch_summary(
        normalized_results,
        dry_run=dry_run,
        failed_count=int(result.get("failed_count", 0) or 0),
    )
    report_combined_signal_batch_summary(summary)

    print("release refresh finished")
    print(f"success_count: {result.get('success_count', 0)}")
    print(f"skipped_count: {result.get('skipped_count', 0)}")
    print(f"failed_count: {result.get('failed_count', 0)}")
    print(f"checked_count: {summary.get('checked_count', 0)}")
    print(f"combined_count: {summary.get('combined_count', 0)}")
    print(f"price_only_count: {summary.get('price_only_count', 0)}")
    print(f"release_only_count: {summary.get('release_only_count', 0)}")
    print(f"refresh_target_count: {summary.get('refresh_target_count', 0)}")


if __name__ == "__main__":
    main()
