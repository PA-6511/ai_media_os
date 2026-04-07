from __future__ import annotations

# release_journey_adapter.py
# release_changed を起点に Buyer Journey 結果を新刊向けに補正する。

import re
from typing import Any


def adapt_stage_for_release(article_output: dict[str, Any], stage: str) -> str:
    """release 情報に応じて stage を補正する。"""
    article_type = str(article_output.get("article_type", "")).strip().lower()
    release_changed = bool(article_output.get("release_changed", False))
    availability = str(article_output.get("current_availability_status", "")).strip().lower()

    if not release_changed:
        return stage

    if article_type == "latest_volume":
        return "purchase_ready"
    if article_type == "volume_guide":
        return "comparison"
    if article_type == "summary":
        if availability == "available":
            return "purchase_ready"
        return "comparison"

    return stage


def _fallback_url_from_title(title: str) -> str:
    text = title.replace("　", " ").strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return f"/related/{text or 'next-article'}"


def _classify_release_link(title: str) -> str:
    normalized = (title or "").strip().lower()

    # 日本語タイトルでは単語境界 \b が期待通りに働かないケースがあるため、単純な巻数検知を使う。
    if re.search(r"\d+巻", normalized) or "前巻" in title:
        return "prev_volume"
    if "何巻まで" in title or "巻数" in title or "ガイド" in title:
        return "volume_guide"
    if "全巻" in title or "まとめ買い" in title:
        return "all_volumes"
    if "セール" in title or "割引" in title or "安い" in title:
        return "sale"
    if "最新巻" in title or "新刊" in title:
        return "latest"
    return "other"


def _release_rank(category: str) -> int:
    ranks = {
        "prev_volume": 400,
        "volume_guide": 300,
        "all_volumes": 200,
        "sale": 100,
        "latest": 90,
        "other": 0,
    }
    return ranks.get(category, 0)


def adapt_next_articles_for_release(
    article_output: dict[str, Any],
    next_articles: list[dict[str, str]],
) -> list[dict[str, str]]:
    """新刊記事向けに next_articles の並びと候補を補正する。"""
    article_type = str(article_output.get("article_type", "")).strip().lower()
    release_changed = bool(article_output.get("release_changed", False))

    if not release_changed:
        return next_articles

    # latest_volume は最短導線を最優先で補正する。
    aggressive_mode = article_type == "latest_volume"

    pool: list[dict[str, str]] = []
    pool.extend(next_articles)

    related_links = article_output.get("related_links", [])
    if isinstance(related_links, list):
        for row in related_links:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            if title and url:
                pool.append({"title": title, "url": url})

    hints = article_output.get("internal_link_hints", [])
    if isinstance(hints, list):
        for hint in hints:
            title = str(hint).strip()
            if not title:
                continue
            pool.append({"title": title, "url": _fallback_url_from_title(title)})

    # スコアリングして並べ替え
    scored: list[tuple[int, dict[str, str]]] = []
    for row in pool:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        if not title or not url:
            continue

        category = _classify_release_link(title)
        score = _release_rank(category)

        # release_changed の場合は "最新巻" 系も一定優遇
        if "最新巻" in title:
            score += 25

        # aggressive_mode では優先カテゴリ差をさらに広げる
        if aggressive_mode:
            score *= 2

        scored.append((score, {"title": title, "url": url}))

    scored.sort(key=lambda x: x[0], reverse=True)

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _, row in scored:
        key = (row["title"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    # latest_volume + release_changed は 4件まで強化、それ以外は 3件
    max_items = 4 if aggressive_mode else 3
    return deduped[:max_items]


def adapt_cta_for_release(article_output: dict[str, Any], cta_text: str) -> str:
    """release 情報に応じて CTA 文言を補正する。"""
    article_type = str(article_output.get("article_type", "")).strip().lower()
    release_changed = bool(article_output.get("release_changed", False))
    availability = str(article_output.get("current_availability_status", "")).strip().lower()

    if article_type == "latest_volume":
        if availability == "available":
            base = (
                "最新巻はすぐ読める可能性があるため、ストアで配信状況を確認してください。"
                "続きを今すぐ読みたい方は最新巻ページをチェックしてください。"
            )
        elif availability == "preorder":
            base = (
                "最新巻の予約受付状況を確認してください。"
                "配信開始前に予約できる場合があります。"
            )
        else:
            base = cta_text
    else:
        base = cta_text

    if release_changed:
        prefix = "新刊情報が更新されたため、最新情報を優先して確認してください。"
        return f"{prefix}{base}"

    return base


def build_release_journey_title(article_output: dict[str, Any]) -> str:
    """release 情報に応じた journey-box タイトルを返す。"""
    release_changed = bool(article_output.get("release_changed", False))
    if release_changed:
        return "新刊をチェックするならこちら"
    return "次に読むならこちら"


def adapt_journey_for_release(article_output: dict[str, Any], journey: dict[str, Any]) -> dict[str, Any]:
    """journey 全体を release シナリオ向けに補正する。"""
    try:
        if not isinstance(journey, dict):
            raise ValueError("journey が dict ではありません")

        release_changed = bool(article_output.get("release_changed", False))

        current_stage = str(journey.get("stage", "information_gathering"))
        stage = adapt_stage_for_release(article_output, current_stage)

        current_next = journey.get("next_articles", [])
        if not isinstance(current_next, list):
            current_next = []
        next_articles = adapt_next_articles_for_release(article_output, current_next)

        current_cta = str(journey.get("cta_text", "")).strip()
        cta_text = adapt_cta_for_release(article_output, current_cta)

        release_title = build_release_journey_title(article_output)

        mode = "release_optimized" if release_changed else "standard"
        adapted = dict(journey)
        adapted.update(
            {
                "stage": stage,
                "cta_text": cta_text,
                "next_articles": next_articles,
                "journey_mode": mode,
                "is_release_optimized": release_changed,
                "release_journey_title": release_title,
            }
        )

        # release メタデータも journey 内へ集約
        if release_changed:
            adapted["release_changed"] = True
            adapted["release_change_reason"] = article_output.get("release_change_reason", "")
            adapted["current_latest_volume_number"] = article_output.get("current_latest_volume_number")
            adapted["current_latest_release_date"] = article_output.get("current_latest_release_date")
            adapted["current_availability_status"] = article_output.get("current_availability_status")

        return adapted
    except Exception as exc:
        # Adapter の失敗で本体処理を止めないため、安全側で元データを返す。
        fallback = dict(journey) if isinstance(journey, dict) else {}
        fallback["journey_mode"] = "standard"
        fallback["is_release_optimized"] = False
        fallback["release_adapter_error"] = str(exc)
        return fallback
