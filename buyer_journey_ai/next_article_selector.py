from __future__ import annotations

import re
from typing import Any


def _fallback_url_from_title(title: str) -> str:
    text = title.replace("　", " ").strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return f"/related/{text or 'next-article'}"


def _stage_priority_tokens(stage: str) -> list[str]:
    if stage == "purchase_ready":
        return ["最新巻", "全巻", "セール", "購入"]
    if stage == "comparison":
        return ["最新巻", "全巻", "セール", "比較"]
    return ["評価", "レビュー", "人気", "おすすめ"]


def _release_priority_score(title: str, article_type: str) -> int:
    """新刊シナリオ向けの優先度スコアを返す。"""
    text = (title or "").strip()

    # latest_volume + release_changed 向け:
    # 1. 前巻記事 2. 巻数ガイド 3. 全巻記事 4. セール記事
    if re.search(r"\d+巻", text) or "前巻" in text:
        return 400
    if "何巻まで" in text or "巻数" in text or "ガイド" in text:
        return 300
    if "全巻" in text or "まとめ買い" in text:
        return 200
    if "セール" in text or "割引" in text or "安い" in text:
        return 100
    if "最新巻" in text or "新刊" in text:
        return 80

    # volume_guide / summary の軽量補正
    if article_type in {"volume_guide", "summary"}:
        if "全巻" in text:
            return 150
        if "セール" in text:
            return 120

    return 0


def _sale_priority_score(title: str) -> int:
    """セールシナリオ向けの優先度スコアを返す。"""
    text = (title or "").strip()

    # 1位: 全巻まとめ買い
    if "全巻" in text or "まとめ買い" in text:
        return 400
    # 2位: 最新巻
    if "最新巻" in text or "新刊" in text:
        return 300
    # 3位: 巻数ガイド
    if "何巻まで" in text or "巻数" in text or "ガイド" in text:
        return 200
    # 4位: 作品情報 / 評価
    if "作品" in text or "紹介" in text or "評価" in text or "感想" in text:
        return 100
    # セール関連（汎用）
    if "セール" in text or "割引" in text or "安い" in text:
        return 90

    return 0


def select_next_articles(
    article_output: dict[str, Any],
    stage: str,
    release_changed: bool = False,
    price_changed: bool = False,
) -> list[dict[str, str]]:
    """購買段階に応じて次記事候補を優先順位付きで返す。

    price_changed が True の場合はセール向け優先順位（全巻→最新巻→巻数ガイド→作品情報）を適用する。
    release_changed が True の場合は新刊向け優先順位を適用する。
    両方 True の場合は price_changed を優先する。

    Args:
        article_output: 記事データ辞書。
        stage: 購買段階文字列。
        release_changed: 新刊情報が更新されたか。
        price_changed: 価格変動が検知されたか。

    Returns:
        優先順位付き next_articles リスト。
    """
    priority_tokens = _stage_priority_tokens(stage)
    article_type = str(article_output.get("article_type", "")).strip().lower()
    # price_changed が True の場合は sale_article 相当の判定でセール向けスコアを使う
    use_sale_score = price_changed or article_type == "sale_article"
    ranked: list[tuple[int, dict[str, str]]] = []

    # 1) related_links を優先利用
    related = article_output.get("related_links", [])
    if isinstance(related, list):
        for row in related:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            if not title or not url:
                continue

            score = 0
            for idx, token in enumerate(priority_tokens):
                if token in title:
                    score += 100 - idx * 10
            if use_sale_score:
                # price_changed が優先: セール向けスコアを加算
                score += _sale_priority_score(title)
            elif release_changed:
                score += _release_priority_score(title, article_type)
            ranked.append((score, {"title": title, "url": url}))

    # 2) 足りない場合は internal_link_hints から補完
    hints = article_output.get("internal_link_hints", [])
    if isinstance(hints, list):
        for hint in hints:
            title = str(hint).strip()
            if not title:
                continue
            url = _fallback_url_from_title(title)
            score = 0
            for idx, token in enumerate(priority_tokens):
                if token in title:
                    score += 80 - idx * 10
            if use_sale_score:
                score += _sale_priority_score(title)
            elif release_changed:
                score += _release_priority_score(title, article_type)
            ranked.append((score, {"title": title, "url": url}))

    # 重複除去して上位件数を返す
    ranked.sort(key=lambda x: x[0], reverse=True)
    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    # sale_article / price_changed は 4件、latest_volume + release_changed は 4件、それ以外は 3件
    if use_sale_score:
        max_items = 4
    elif release_changed and article_type == "latest_volume":
        max_items = 4
    else:
        max_items = 3

    for _, item in ranked:
        key = (item["title"], item["url"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= max_items:
            break

    return selected


class NextArticleSelector:
    """既存コード互換ラッパー。"""

    def recommend_next_articles(self, keyword: str, current_article: str, stage: str, max_items: int = 3) -> list[str]:
        article_output = {
            "keyword": keyword,
            "title": current_article,
            "related_links": [],
            "internal_link_hints": [
                f"{keyword} 最新巻",
                f"{keyword} 全巻",
                f"{keyword} セール",
            ],
        }
        selected = select_next_articles(
            article_output=article_output,
            stage=stage,
            release_changed=False,
        )
        return [row["title"] for row in selected[:max_items]]
