from __future__ import annotations

# journey_signal_adapter.py
# Buyer Journey 結果を combined signal 通知イベントへ連携するための変換アダプタ。

from typing import Any

from buyer_journey_ai.journey_builder import build_journey


def summarize_next_articles(next_articles: list[dict[str, str]]) -> list[str]:
    """next_articles を通知向けの短い要約配列へ変換する。"""
    if not isinstance(next_articles, list):
        return []

    summaries: list[str] = []
    for row in next_articles:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", "")).strip()
        if not title:
            continue

        if "最新巻" in title or "新刊" in title:
            summaries.append("最新巻を確認")
        elif "前巻" in title or "巻" in title:
            summaries.append("前巻を確認")
        elif "全巻" in title or "まとめ買い" in title:
            summaries.append("全巻情報を見る")
        elif "セール" in title or "割引" in title:
            summaries.append("セール情報を見る")
        else:
            summaries.append(title)

    # 重複除去しつつ順序維持、最大4件
    deduped: list[str] = []
    seen: set[str] = set()
    for text in summaries:
        if text in seen:
            continue
        seen.add(text)
        deduped.append(text)
        if len(deduped) >= 4:
            break

    return deduped


def build_journey_signal_payload(article_output: dict[str, Any]) -> dict[str, Any]:
    """article_output から通知用 journey 情報を作成する。

    article_output に journey が既にある場合はそれを優先し、
    無い場合は build_journey で再計算する。
    """
    try:
        journey_obj = article_output.get("journey")
        if isinstance(journey_obj, dict):
            journey = dict(journey_obj)
        else:
            journey = build_journey(article_output)

        stage = str(journey.get("stage", "")).strip()
        cta_text = str(journey.get("cta_text", "")).strip()
        is_release = bool(journey.get("is_release_optimized", False))
        is_sale = bool(journey.get("is_sale_optimized", False))

        # combined_optimized を明示
        if is_release and is_sale:
            journey_mode = "combined_optimized"
        else:
            journey_mode = str(journey.get("journey_mode", "standard")).strip() or "standard"

        next_articles = journey.get("next_articles", [])
        if not isinstance(next_articles, list):
            next_articles = []

        return {
            "stage": stage,
            "journey_mode": journey_mode,
            "is_release_optimized": is_release,
            "is_sale_optimized": is_sale,
            "cta_text": cta_text,
            "next_articles_summary": summarize_next_articles(next_articles),
            # デバッグ用に raw も残す
            "next_articles": next_articles,
        }
    except Exception as exc:
        return {
            "stage": "",
            "journey_mode": "standard",
            "is_release_optimized": False,
            "is_sale_optimized": False,
            "cta_text": "",
            "next_articles_summary": [],
            "next_articles": [],
            "journey_signal_adapter_error": str(exc),
        }


def merge_journey_into_event(event: dict[str, Any], journey: dict[str, Any]) -> dict[str, Any]:
    """event に journey ペイロードをマージして返す。"""
    merged = dict(event)
    merged.update(
        {
            "stage": journey.get("stage", ""),
            "journey_mode": journey.get("journey_mode", "standard"),
            "is_release_optimized": bool(journey.get("is_release_optimized", False)),
            "is_sale_optimized": bool(journey.get("is_sale_optimized", False)),
            "cta_text": journey.get("cta_text", ""),
            "next_articles_summary": journey.get("next_articles_summary", []),
            "next_articles": journey.get("next_articles", []),
        }
    )

    if "journey_signal_adapter_error" in journey:
        merged["journey_signal_adapter_error"] = journey["journey_signal_adapter_error"]

    return merged
