from __future__ import annotations

import os
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.core_runtime_config import get_retry_max_retry_count
from article_generator.generator import generate_article_content
from article_planner.planner import generate_plan
from core.database.db_setup import run as run_db_setup
from core.database.db_utils import get_db_path, get_intent_analysis_path, get_keywords_path
from core.intent.search_intent_analyzer import run as run_intent_analysis
from core.keyword.keyword_generator import run as run_keyword_generation
from release_calendar_ai.release_change_detector import detect_release_change
from release_calendar_ai.release_collector import fetch_current_release_info
from release_calendar_ai.release_history import create_tables as create_release_tables
from release_calendar_ai.release_history import get_latest_release_record, save_release_snapshot
from release_calendar_ai.release_proposal_generator import build_release_refresh_targets
from price_drop_ai.change_detector import detect_price_change, is_significant_change
from price_drop_ai.price_collector import build_current_price_record
from price_drop_ai.price_history import create_tables as create_price_tables
from price_drop_ai.price_history import get_latest_price, save_price_snapshot
from price_drop_ai.proposal_generator import build_refresh_proposal
from pipelines.enrich_article_with_journey import enrich_article_with_journey
from pipelines.enrich_article_with_links import enrich_article
from monitoring.failure_reporter import report_batch_summary
from pipelines.combined_signal_policy import build_combined_event, evaluate_combined_signal
from pipelines.priority_policy import get_article_priority
from pipelines.sale_refresh_selector import select_processing_items
from pipelines.post_status_store import build_status_record, upsert_status
from pipelines.publish_article_pipeline import publish_article
from pipelines.retry_policy import should_retry
from pipelines.retry_queue_store import build_retry_record, enqueue_failed_item
from pipelines.wp_post_enricher import build_slug


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
ITEMS_DIR = DATA_DIR / "items"


@dataclass
class BatchConfig:
    """バッチ実行設定。"""

    max_items: int | None = None
    only_sale_articles: bool = False
    only_release_changed_articles: bool = False
    save_per_item_files: bool = True
    per_item_dir: Path = ITEMS_DIR


def _to_bool(value: str, default: bool = False) -> bool:
    """環境変数文字列を bool へ変換する。"""
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_max_items(value: str) -> int | None:
    """MAX_ITEMS 文字列を int | None に変換する。"""
    text = (value or "").strip().lower()
    if text in {"", "none", "all", "*"}:
        return None

    parsed = int(text)
    if parsed <= 0:
        raise ValueError("MAX_ITEMS は 1 以上の整数か None/all を指定してください")
    return parsed


def _sanitize_file_component(value: str, fallback: str) -> str:
    """ファイル名コンポーネントとして安全な文字列へ正規化する。"""
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", (value or "").strip())
    normalized = normalized.strip("_")
    return normalized or fallback


def _build_item_prefix(item: dict[str, Any]) -> str:
    """work_id と article_type を含む件別ファイルプレフィックスを作る。"""
    work_id = _sanitize_file_component(str(item.get("work_id", "")), "unknown_work")
    article_type = _sanitize_file_component(str(item.get("article_type", "")), "work_article")
    return f"{work_id}_{article_type}"


def _save_json(path: Path, data: dict[str, Any]) -> None:
    """UTF-8 JSON で保存する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def _print_step_header(step: int, total: int, title: str) -> None:
    """ステップ開始ログを表示する。"""
    print(f"[{step}/{total}] {title} 開始")


def load_intent_items(path: Path) -> list[dict[str, Any]]:
    """intent_analysis.json から配列データを読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"intent_analysis.json のJSON形式が不正です: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"intent_analysis.json の読み込みに失敗しました: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("intent_analysis.json は配列形式である必要があります")

    return [item for item in data if isinstance(item, dict)]


def limit_items(items: list[dict[str, Any]], max_items: int | None) -> list[dict[str, Any]]:
    """上位 N 件に絞り込む。None の場合は全件対象。"""
    if max_items is None:
        return items
    return items[:max_items]


def _attach_release_change_for_item(item: dict[str, Any]) -> dict[str, Any]:
    """新刊イベント情報を item に付与する。"""
    work_id = str(item.get("work_id", "")).strip()
    article_type = str(item.get("article_type", "")).strip()

    current_release = fetch_current_release_info(item)
    previous_release = get_latest_release_record(work_id)
    release_event = detect_release_change(previous_release, current_release)
    target_info = build_release_refresh_targets(item, release_event)

    save_release_snapshot(current_release)

    print("[新刊検知]")
    print(f"work_id: {work_id}")
    print(f"title: {current_release.get('title', '')}")
    print(f"previous_latest_volume_number: {release_event.get('previous_latest_volume_number')}")
    print(f"current_latest_volume_number: {release_event.get('current_latest_volume_number')}")
    print(f"release_change_reason: {release_event.get('release_change_reason')}")
    print(f"release_changed: {release_event.get('release_changed')}")

    return {
        **item,
        "title": str(current_release.get("title", "")).strip(),
        "release_changed": bool(release_event.get("release_changed", False)) and bool(
            target_info.get("release_target", False)
        ),
        "release_event_detected": bool(release_event.get("release_changed", False)),
        "release_change_reason": release_event.get("release_change_reason", "no_change"),
        "release_target_reason": target_info.get("target_reason", "release_not_changed"),
        "previous_latest_volume_number": release_event.get("previous_latest_volume_number"),
        "current_latest_volume_number": release_event.get("current_latest_volume_number"),
        "previous_latest_release_date": release_event.get("previous_latest_release_date"),
        "current_latest_release_date": release_event.get("current_latest_release_date"),
        "previous_availability_status": release_event.get("previous_availability_status"),
        "current_availability_status": release_event.get("current_availability_status"),
        "latest_release_date": current_release.get("latest_release_date"),
        "availability_status": current_release.get("availability_status"),
        "release_change_event": release_event,
        "release_refresh_target": bool(target_info.get("release_target", False)),
    }


def attach_release_changes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """item 一覧に新刊イベント情報を付与する。"""
    create_release_tables()

    enriched: list[dict[str, Any]] = []
    for item in items:
        try:
            enriched_item = _attach_release_change_for_item(item)
        except Exception as exc:
            enriched_item = {
                **item,
                "release_changed": False,
                "release_event_detected": False,
                "release_change_reason": f"release_check_error:{exc}",
                "release_target_reason": "release_check_error",
                "title": str(item.get("title", "")).strip(),
                "previous_latest_volume_number": None,
                "current_latest_volume_number": None,
                "previous_latest_release_date": None,
                "current_latest_release_date": None,
                "previous_availability_status": None,
                "current_availability_status": None,
                "latest_release_date": None,
                "availability_status": None,
                "release_refresh_target": False,
            }
        enriched.append(enriched_item)
    return enriched


def _attach_price_change_for_sale_item(item: dict[str, Any]) -> dict[str, Any]:
    """sale_article の価格変動情報を付与する。"""
    article_type = str(item.get("article_type", "")).strip()
    if article_type != "sale_article":
        return {
            **item,
            "price_changed": False,
            "previous_price": None,
            "current_price": None,
            "discount_rate": None,
            "price_diff": None,
            "change_reason": "not_sale_article",
        }

    work_id = str(item.get("work_id", "")).strip()
    keyword = str(item.get("keyword", "")).strip()

    previous = get_latest_price(work_id=work_id, article_type=article_type, keyword=keyword)
    current = build_current_price_record(item)
    change = detect_price_change(previous, current)
    proposal = build_refresh_proposal(change)

    save_price_snapshot(current)

    # 要件に合わせて検知ログを標準出力へ明示する。
    print("[価格変動検知]")
    print(f"work_id: {work_id}")
    print(f"keyword: {keyword}")
    print(f"previous_price: {change.get('previous_price')}")
    print(f"current_price: {change.get('current_price')}")
    print(f"price_diff: {change.get('price_diff')}")
    print(f"change_reason: {change.get('change_reason')}")
    print(f"price_changed: {change.get('price_changed')}")

    return {
        **item,
        "price_changed": bool(change.get("price_changed", False)),
        "previous_price": change.get("previous_price"),
        "current_price": change.get("current_price"),
        "discount_rate": change.get("discount_rate"),
        "discount_rate_diff": change.get("discount_rate_diff"),
        "price_diff": change.get("price_diff"),
        "change_reason": change.get("change_reason", "no_change"),
        "price_change_event": change,
        "price_change_proposal": proposal,
        "price_change_significant": is_significant_change(change),
    }


def attach_price_changes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """item 一覧に価格変動情報を付与する。"""
    create_price_tables()
    enriched: list[dict[str, Any]] = []
    for item in items:
        try:
            enriched_item = _attach_price_change_for_sale_item(item)
        except Exception as exc:
            # 価格取得失敗時も本体処理は継続する。
            enriched_item = {
                **item,
                "price_changed": False,
                "previous_price": None,
                "current_price": None,
                "discount_rate": None,
                "discount_rate_diff": None,
                "price_diff": None,
                "change_reason": f"price_check_error:{exc}",
            }
        enriched.append(enriched_item)
    return enriched


def attach_combined_signal_result(items: list[dict[str, Any]], *, dry_run: bool) -> list[dict[str, Any]]:
    """item 一覧に複合シグナル判定結果を付与する。"""
    enriched: list[dict[str, Any]] = []
    for item in items:
        try:
            combined = evaluate_combined_signal(item, dry_run=dry_run)
            merged = {
                **item,
                "priority": combined.priority,
                "decision": combined.decision,
                "reason": combined.reason,
                "sub_reasons": combined.sub_reasons,
            }
        except Exception as exc:
            # 複合判定失敗時は既存優先度へフォールバックして処理継続する。
            merged = {
                **item,
                "priority": get_article_priority(
                    str(item.get("article_type", "")),
                    price_changed=bool(item.get("price_changed", False)),
                    release_changed=bool(item.get("release_changed", False)),
                ),
                "decision": "would_skip_policy_blocked" if dry_run else "skip_policy_blocked",
                "reason": f"combined_policy_error:{exc}",
                "sub_reasons": [],
            }
        enriched.append(merged)
    return enriched


def process_one_item(item: dict[str, Any], config: BatchConfig) -> dict[str, Any]:
    """1件分の planner->generator->links->journey->publish を実行する。"""
    prefix = _build_item_prefix(item)
    current_stage = "planner"

    result_base: dict[str, Any] = {
        "work_id": str(item.get("work_id", "")).strip(),
        "keyword": str(item.get("keyword", "")).strip(),
        "article_type": str(item.get("article_type", "")).strip(),
        "priority": int(
            item.get(
                "priority",
                get_article_priority(
                    str(item.get("article_type", "")),
                    price_changed=bool(item.get("price_changed", False)),
                    release_changed=bool(item.get("release_changed", False)),
                ),
            )
        ),
        "price_changed": bool(item.get("price_changed", False)),
        "previous_price": item.get("previous_price"),
        "current_price": item.get("current_price"),
        "discount_rate": item.get("discount_rate"),
        "discount_rate_diff": item.get("discount_rate_diff"),
        "price_diff": item.get("price_diff"),
        "change_reason": item.get("change_reason", "no_change"),
        "release_changed": bool(item.get("release_changed", False)),
        "release_change_reason": item.get("release_change_reason", "no_change"),
        "decision": str(item.get("decision", "")),
        "reason": str(item.get("reason", "")),
        "sub_reasons": list(item.get("sub_reasons", [])) if isinstance(item.get("sub_reasons"), list) else [],
        "event_type": str(build_combined_event(item).get("event_type", "none")),
        "title": item.get("title", ""),
        "previous_latest_volume_number": item.get("previous_latest_volume_number"),
        "current_latest_volume_number": item.get("current_latest_volume_number"),
        "previous_latest_release_date": item.get("previous_latest_release_date"),
        "current_latest_release_date": item.get("current_latest_release_date"),
        "previous_availability_status": item.get("previous_availability_status"),
        "current_availability_status": item.get("current_availability_status"),
        "slug": build_slug(item),
    }

    try:
        plan = generate_plan(item)
        print("- planner 完了")
        if config.save_per_item_files:
            _save_json(config.per_item_dir / f"{prefix}_article_plan.json", plan)

        current_stage = "generator"
        article_output = generate_article_content(plan)
        print("- generator 完了")
        if config.save_per_item_files:
            _save_json(config.per_item_dir / f"{prefix}_article_output.json", article_output)

        current_stage = "links"
        with_links = enrich_article(article_output)
        print("- links 完了")
        if config.save_per_item_files:
            _save_json(config.per_item_dir / f"{prefix}_article_output_with_links.json", with_links)

        current_stage = "journey"
        with_journey = enrich_article_with_journey(with_links)
        # publish 判定に価格変動情報を渡すため、最終出力に注入する。
        with_journey["price_changed"] = bool(item.get("price_changed", False))
        with_journey["previous_price"] = item.get("previous_price")
        with_journey["current_price"] = item.get("current_price")
        with_journey["discount_rate"] = item.get("discount_rate")
        with_journey["price_diff"] = item.get("price_diff")
        with_journey["change_reason"] = item.get("change_reason", "no_change")
        with_journey["release_changed"] = bool(item.get("release_changed", False))
        with_journey["release_change_reason"] = item.get("release_change_reason", "no_change")
        with_journey["previous_latest_volume_number"] = item.get("previous_latest_volume_number")
        with_journey["current_latest_volume_number"] = item.get("current_latest_volume_number")
        with_journey["previous_latest_release_date"] = item.get("previous_latest_release_date")
        with_journey["current_latest_release_date"] = item.get("current_latest_release_date")
        with_journey["previous_availability_status"] = item.get("previous_availability_status")
        with_journey["current_availability_status"] = item.get("current_availability_status")
        print("- journey 完了")
        if config.save_per_item_files:
            _save_json(config.per_item_dir / f"{prefix}_article_output_with_journey.json", with_journey)

        current_stage = "publish"
        publish_result = publish_article(with_journey)
        print(f"- publish_guard: {publish_result.get('decision', 'unknown')}")
        print(f"  reason: {publish_result.get('reason', '')}")

        if publish_result.get("skipped"):
            print("- publish スキップ")
            print(f"  existing_post_id: {publish_result.get('existing_post_id')}")
            print(f"  existing_link: {publish_result.get('existing_link')}")
            return {
                **result_base,
                "slug": publish_result.get("slug", result_base["slug"]),
                "success": True,
                "skipped": True,
                "decision": publish_result.get("decision", "skip_policy_blocked"),
                "reason": publish_result.get("reason", "already_published"),
                "sub_reasons": list(item.get("sub_reasons", [])) if isinstance(item.get("sub_reasons"), list) else [],
                "existing_post_id": publish_result.get("existing_post_id"),
                "existing_link": publish_result.get("existing_link"),
            }

        print("- publish 完了")

        if publish_result.get("dry_run"):
            print("  dry_run: true")
            return {
                **result_base,
                "slug": publish_result.get("slug", result_base["slug"]),
                "success": True,
                "skipped": False,
                "dry_run": True,
                "decision": publish_result.get("decision", "would_publish_new"),
                "reason": publish_result.get("reason", "would_publish"),
                "sub_reasons": list(item.get("sub_reasons", [])) if isinstance(item.get("sub_reasons"), list) else [],
            }

        print(f"  post_id: {publish_result.get('post_id')}")
        print(f"  status: {publish_result.get('status')}")
        print(f"  link: {publish_result.get('link')}")
        return {
            **result_base,
            "slug": publish_result.get("slug", result_base["slug"]),
            "success": True,
            "skipped": False,
            "republished": bool(publish_result.get("republished", False)),
            "decision": publish_result.get("decision", "publish_new"),
            "reason": publish_result.get("reason", "not_found"),
            "sub_reasons": list(item.get("sub_reasons", [])) if isinstance(item.get("sub_reasons"), list) else [],
            "post_id": publish_result.get("post_id"),
            "status": publish_result.get("status"),
            "link": publish_result.get("link"),
        }
    except Exception as exc:
        # publish より前の失敗は main 側で failed ステータスに反映する。
        if current_stage in {"planner", "generator", "links", "journey"}:
            error_text = f"{current_stage} 失敗: {exc}"
            failed_record = build_status_record(
                slug=result_base["slug"],
                work_id=result_base["work_id"],
                keyword=result_base["keyword"],
                article_type=result_base["article_type"],
                title=str(item.get("title", "")).strip(),
                status="failed",
                post_id=None,
                link=None,
                error_message=error_text,
            )
            upsert_status(failed_record)

            # 本投稿時のみ retry queue へ積む。
            if not _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True):
                default_max_retry_count = get_retry_max_retry_count()
                retry_decision = should_retry(error_text, retry_count=0, max_retry_count=default_max_retry_count)
                if retry_decision.get("retryable"):
                    retry_record = build_retry_record(
                        slug=result_base["slug"],
                        work_id=result_base["work_id"],
                        keyword=result_base["keyword"],
                        article_type=result_base["article_type"],
                        title=str(item.get("title", "")).strip(),
                        last_error=error_text,
                        retry_count=0,
                        max_retry_count=int(retry_decision.get("max_retry_count", default_max_retry_count) or default_max_retry_count),
                        retry_status="queued",
                        next_retry_at=str(retry_decision.get("next_retry_at", "")) or None,
                    )
                    enqueue_failed_item(retry_record)

        return {
            **result_base,
            "success": False,
            "error": str(exc),
        }


def build_combined_signal_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """main 実行用の複合シグナル件数サマリーを作る。"""
    checked_rows = [
        row
        for row in results
        if str(row.get("event_type", "")).strip() in {"combined", "price_only", "release_only"}
    ]
    combined_count = sum(1 for row in checked_rows if row.get("event_type") == "combined")
    price_only_count = sum(1 for row in checked_rows if row.get("event_type") == "price_only")
    release_only_count = sum(1 for row in checked_rows if row.get("event_type") == "release_only")
    return {
        "checked_count": len(checked_rows),
        "combined_count": combined_count,
        "price_only_count": price_only_count,
        "release_only_count": release_only_count,
    }


def run_batch() -> list[dict[str, Any]]:
    """intent_analysis.json の複数件を順番に処理する。"""
    return run_batch_with_options(
        max_items=None,
        only_sale_articles=None,
        only_release_changed_articles=None,
        save_per_item_files=None,
    )


def run_batch_with_options(
    max_items: int | None = None,
    only_sale_articles: bool | None = None,
    only_release_changed_articles: bool | None = None,
    save_per_item_files: bool | None = None,
) -> list[dict[str, Any]]:
    """intent_analysis.json の複数件を順番に処理する（設定上書き対応）。"""
    env_max_items = _parse_max_items(os.getenv("MAX_ITEMS", "None"))
    env_only_sale = _to_bool(os.getenv("ONLY_SALE_ARTICLES", "0"), default=False)
    env_only_release = _to_bool(os.getenv("ONLY_RELEASE_CHANGED_ARTICLES", "0"), default=False)
    env_save_files = _to_bool(os.getenv("SAVE_PER_ITEM_FILES", "1"), default=True)

    config = BatchConfig(
        max_items=env_max_items if max_items is None else max_items,
        only_sale_articles=env_only_sale if only_sale_articles is None else only_sale_articles,
        only_release_changed_articles=(
            env_only_release
            if only_release_changed_articles is None
            else only_release_changed_articles
        ),
        save_per_item_files=env_save_files if save_per_item_files is None else save_per_item_files,
        per_item_dir=ITEMS_DIR,
    )

    items = load_intent_items(get_intent_analysis_path())
    dry_run = _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True)
    release_enriched_items = attach_release_changes(items)
    priced_items = attach_price_changes(release_enriched_items)
    combined_items = attach_combined_signal_result(priced_items, dry_run=dry_run)
    selected = select_processing_items(combined_items, only_sale=config.only_sale_articles)
    if config.only_release_changed_articles:
        selected = [item for item in selected if bool(item.get("release_changed", False))]
    targets = limit_items(selected, config.max_items)
    filtered_count = len(items) - len(selected)

    print(f"[全体] 処理対象件数: {len(targets)}")
    print("[全体] priority sort applied")
    print(f"[全体] sale_article 優先モード: {config.only_sale_articles}")
    print(f"[全体] release_changed 優先モード: {config.only_release_changed_articles}")
    if config.only_sale_articles:
        print(f"[全体] sale only 対象外件数: {filtered_count}")
    if config.only_release_changed_articles:
        print(f"[全体] release changed 対象外件数: {filtered_count}")
    if config.save_per_item_files:
        print(f"[全体] 件別保存ディレクトリ: {config.per_item_dir}")

    results: list[dict[str, Any]] = []
    total = len(targets)
    for index, item in enumerate(targets, start=1):
        item_slug = build_slug(item)
        print(f"\n[{index}/{total}] 開始")
        print(f"work_id: {item.get('work_id', '')}")
        print(f"keyword: {item.get('keyword', '')}")
        print(f"article_type: {item.get('article_type', '')}")
        print(
            f"priority: {item.get('priority', get_article_priority(str(item.get('article_type', '')), price_changed=bool(item.get('price_changed', False)), release_changed=bool(item.get('release_changed', False))))}"
        )
        print(f"price_changed: {item.get('price_changed', False)}")
        print(f"change_reason: {item.get('change_reason', 'no_change')}")
        print(f"release_changed: {item.get('release_changed', False)}")
        print(f"release_change_reason: {item.get('release_change_reason', 'no_change')}")
        print("[複合優先制御]")
        print(f"decision: {item.get('decision', '')}")
        print(f"reason: {item.get('reason', '')}")
        print(f"sub_reasons: {item.get('sub_reasons', [])}")
        print(f"slug: {item_slug}")

        item_result = process_one_item(item, config)
        if not item_result.get("success"):
            print(f"- 失敗: {item_result.get('error', 'unknown error')}")
        results.append(item_result)

    success_count = sum(1 for row in results if row.get("success") and not row.get("skipped"))
    skipped_count = sum(1 for row in results if row.get("success") and row.get("skipped"))
    failure_count = len(results) - success_count - skipped_count
    print("\n[全体] 完了")
    print(f"成功件数: {success_count}")
    print(f"スキップ件数: {skipped_count}")
    print(f"失敗件数: {failure_count}")
    combined_summary = build_combined_signal_summary(results)
    print("[COMBINED SIGNAL SUMMARY]")
    print(f"checked_count: {combined_summary.get('checked_count', 0)}")
    print(f"combined_count: {combined_summary.get('combined_count', 0)}")
    print(f"price_only_count: {combined_summary.get('price_only_count', 0)}")
    print(f"release_only_count: {combined_summary.get('release_only_count', 0)}")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    return results


def run_pipeline(
    max_items: int | None = None,
    only_sale_articles: bool | None = None,
    only_release_changed_articles: bool | None = None,
    save_per_item_files: bool | None = None,
) -> dict[str, Any]:
    """DB から publish までの一連処理を実行し、集計結果を返す。"""
    _print_step_header(1, 4, "DBセットアップ")
    works = run_db_setup()
    print(f"[1/4] DBセットアップ完了: {get_db_path()}")
    print(f"      works件数: {len(works)}")

    _print_step_header(2, 4, "キーワード生成")
    keywords = run_keyword_generation()
    print(f"[2/4] キーワード生成完了: {get_keywords_path()}")
    print(f"      キーワード対象作品数: {len(keywords)}")

    _print_step_header(3, 4, "検索意図解析")
    analyses = run_intent_analysis()
    print(f"[3/4] 検索意図解析完了: {get_intent_analysis_path()}")
    print(f"      解析件数: {len(analyses)}")

    _print_step_header(4, 4, "Batch Planner/Generator/Publish")
    results = run_batch_with_options(
        max_items=max_items,
        only_sale_articles=only_sale_articles,
        only_release_changed_articles=only_release_changed_articles,
        save_per_item_files=save_per_item_files,
    )

    success_count = sum(1 for row in results if row.get("success") and not row.get("skipped"))
    skipped_count = sum(1 for row in results if row.get("success") and row.get("skipped"))
    failed_count = len(results) - success_count - skipped_count

    failed_slugs = [str(row.get("slug", "")) for row in results if not row.get("success") and row.get("slug")]
    report_batch_summary(
        {
            "success_count": success_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "failed_slugs": failed_slugs,
            "dry_run": _to_bool(os.getenv("WP_DRY_RUN", "1"), default=True),
        }
    )

    return {
        "success_count": success_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "results": results,
    }


def main() -> None:
    """フルライン: DB -> Keyword -> Intent -> Batch Planner..Publish。"""
    try:
        _ = run_pipeline()
    except Exception as exc:
        print(f"実行エラー: {exc}")


if __name__ == "__main__":
    main()
