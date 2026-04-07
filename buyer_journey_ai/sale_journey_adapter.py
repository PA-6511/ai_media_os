from __future__ import annotations

# sale_journey_adapter.py
# price_changed / article_type / discount_rate / price_diff を参照して
# Buyer Journey の結果をセール向けに補正するアダプタ。
# release_journey_adapter と並列に動作し、既存コードを破壊しない。

import re
from typing import Any


# ------------------------------------------------------------------ #
# 内部ユーティリティ
# ------------------------------------------------------------------ #

def _fallback_url_from_title(title: str) -> str:
    """リンク URL が無いときにタイトルから簡易 URL を生成する。"""
    text = title.replace("　", " ").strip()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return f"/related/{text or 'next-article'}"


def _is_sale_active(article_output: dict[str, Any]) -> bool:
    """セール補正を適用すべき記事かどうかを判定する。"""
    price_changed = bool(article_output.get("price_changed", False))
    article_type = str(article_output.get("article_type", "")).strip().lower()
    # price_changed が True か、article_type が sale_article であれば対象
    return price_changed or article_type == "sale_article"


def _get_discount_rate(article_output: dict[str, Any]) -> float:
    """discount_rate を安全に取得する（失敗時は 0.0）。"""
    try:
        return float(article_output.get("discount_rate", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _get_price_diff(article_output: dict[str, Any]) -> float:
    """price_diff を安全に取得する（失敗時は 0.0）。"""
    try:
        return float(article_output.get("price_diff", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _classify_sale_link(title: str) -> str:
    """リンクタイトルをセール導線カテゴリに分類する。"""
    normalized = (title or "").strip()

    if "全巻" in normalized or "まとめ買い" in normalized:
        return "all_volumes"
    if "最新巻" in normalized or "新刊" in normalized:
        return "latest_volume"
    if "何巻まで" in normalized or "巻数" in normalized or "ガイド" in normalized:
        return "volume_guide"
    if "作品" in normalized or "紹介" in normalized or "評価" in normalized or "感想" in normalized:
        return "work_info"
    if "セール" in normalized or "割引" in normalized or "安い" in normalized:
        return "sale"
    return "other"


def _sale_rank(category: str) -> int:
    """セール導線カテゴリに対応する優先度スコアを返す。"""
    ranks = {
        "all_volumes": 400,   # 1位: 全巻まとめ買い
        "latest_volume": 300, # 2位: 最新巻
        "volume_guide": 200,  # 3位: 巻数ガイド
        "work_info": 100,     # 4位: 作品情報
        "sale": 90,           # セール関連
        "other": 0,
    }
    return ranks.get(category, 0)


# ------------------------------------------------------------------ #
# stage の補正
# ------------------------------------------------------------------ #

def adapt_stage_for_sale(article_output: dict[str, Any], stage: str) -> str:
    """セール / 価格変動情報に応じて stage を補正する。

    Args:
        article_output: 記事データ辞書。
        stage: 現在の stage 文字列。

    Returns:
        補正後の stage 文字列。
    """
    if not _is_sale_active(article_output):
        # セール対象外なら何もしない
        return stage

    article_type = str(article_output.get("article_type", "")).strip().lower()
    price_changed = bool(article_output.get("price_changed", False))
    discount_rate = _get_discount_rate(article_output)

    # sale_article + price_changed → purchase_ready に強制
    if article_type == "sale_article" and price_changed:
        return "purchase_ready"

    # sale_article + 高割引率（20% 以上）→ purchase_ready
    if article_type == "sale_article" and discount_rate >= 20.0:
        return "purchase_ready"

    # sale_article（通常） → comparison 以上
    if article_type == "sale_article":
        if stage == "information_gathering":
            return "comparison"

    # summary + セール情報あり → comparison 寄り
    if article_type == "summary" and _is_sale_active(article_output):
        if stage == "information_gathering":
            return "comparison"

    # latest_volume + price_changed → comparison 以上
    if article_type == "latest_volume" and price_changed:
        if stage == "information_gathering":
            return "comparison"

    return stage


# ------------------------------------------------------------------ #
# next_articles の補正
# ------------------------------------------------------------------ #

def adapt_next_articles_for_sale(
    article_output: dict[str, Any],
    next_articles: list[dict[str, str]],
) -> list[dict[str, str]]:
    """セール記事向けに next_articles の優先順位を補正する。

    優先順:
        1. 全巻まとめ買い
        2. 最新巻
        3. 巻数ガイド
        4. 作品紹介 / 評価記事

    Args:
        article_output: 記事データ辞書。
        next_articles: 現在の next_articles リスト。

    Returns:
        補正後の next_articles リスト（最大 4件）。
    """
    if not _is_sale_active(article_output):
        return next_articles

    # related_links / internal_link_hints / 既存 next_articles をプールに合算
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

    # スコアリング
    scored: list[tuple[int, dict[str, str]]] = []
    for row in pool:
        title = str(row.get("title", "")).strip()
        url = str(row.get("url", "")).strip()
        if not title or not url:
            continue
        category = _classify_sale_link(title)
        score = _sale_rank(category)
        scored.append((score, {"title": title, "url": url}))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 重複除去して最大 4件返す
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _, row in scored:
        key = (row["title"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= 4:
            break

    return deduped


# ------------------------------------------------------------------ #
# CTA 文言の補正
# ------------------------------------------------------------------ #

def adapt_cta_for_sale(
    article_output: dict[str, Any],
    cta_text: str,
) -> str:
    """セール / 価格変動情報に応じて CTA 文言を補正する。

    補正ルール:
        - price_changed = True → 「値下げ確認 + 最新価格チェック」文言
        - discount_rate が高い（20% 以上） → 「早めに確認」追加
        - price_diff が大きい負値（-100 円以上の値下げ） → 「前回より値下がり」追加

    Args:
        article_output: 記事データ辞書。
        cta_text: 現在の CTA 文言。

    Returns:
        補正後の CTA 文言。
    """
    if not _is_sale_active(article_output):
        return cta_text

    price_changed = bool(article_output.get("price_changed", False))
    discount_rate = _get_discount_rate(article_output)
    price_diff = _get_price_diff(article_output)

    sentences: list[str] = []

    if price_changed:
        sentences.append(
            "値下げが確認できたため、まずは最新価格をストアで確認してください。"
        )
        sentences.append(
            "価格が戻る前に対象巻や全巻情報もあわせて確認するのがおすすめです。"
        )

    # 割引率が高い場合（20% 以上）
    if discount_rate >= 20.0:
        sentences.append(
            "割引率が高いため、購入候補なら早めに確認しておくのがおすすめです。"
        )

    # 値下がり幅が大きい場合（-100 円以上の値下がり）
    if price_diff <= -100:
        sentences.append(
            "前回より値下がりしているため、今の価格状況を優先して確認してください。"
        )

    # 補正文言が一切なければ元の CTA をそのまま返す
    if not sentences:
        return cta_text

    return "".join(sentences)


# ------------------------------------------------------------------ #
# journey-box タイトルの生成
# ------------------------------------------------------------------ #

def build_sale_journey_title(article_output: dict[str, Any]) -> str:
    """セール向け journey-box タイトルを返す。

    Args:
        article_output: 記事データ辞書。

    Returns:
        セール向けタイトル文字列。
    """
    if not _is_sale_active(article_output):
        return "次に読むならこちら"

    price_changed = bool(article_output.get("price_changed", False))
    discount_rate = _get_discount_rate(article_output)

    if price_changed and discount_rate >= 20.0:
        return "お得な今の価格をチェックするならこちら"
    if price_changed:
        return "今の価格をチェックするならこちら"
    return "セール中の作品をチェックするならこちら"


# ------------------------------------------------------------------ #
# journey 全体の補正
# ------------------------------------------------------------------ #

def adapt_journey_for_sale(
    article_output: dict[str, Any],
    journey: dict[str, Any],
) -> dict[str, Any]:
    """journey 全体をセールシナリオ向けに補正する。

    既存の journey を破壊せず、セール情報がある場合のみ上書きする。
    release_journey_adapter と直列に使用することを想定しており、
    本関数は release adapter の後に呼び出す。

    Args:
        article_output: 記事データ辞書。
        journey: 既存の journey 辞書（build_journey / release_adapter 後）。

    Returns:
        補正後の journey 辞書。
    """
    try:
        if not isinstance(journey, dict):
            raise ValueError("journey が dict ではありません")

        # セール補正が不要なら元データをそのまま返す
        if not _is_sale_active(article_output):
            return journey

        price_changed = bool(article_output.get("price_changed", False))

        # --- stage の補正 ---
        current_stage = str(journey.get("stage", "information_gathering"))
        stage = adapt_stage_for_sale(article_output, current_stage)

        # --- next_articles の補正 ---
        current_next = journey.get("next_articles", [])
        if not isinstance(current_next, list):
            current_next = []
        next_articles = adapt_next_articles_for_sale(article_output, current_next)

        # --- CTA の補正 ---
        current_cta = str(journey.get("cta_text", "")).strip()
        cta_text = adapt_cta_for_sale(article_output, current_cta)

        # --- journey-box タイトルの生成 ---
        sale_title = build_sale_journey_title(article_output)

        adapted = dict(journey)
        adapted.update(
            {
                "stage": stage,
                "cta_text": cta_text,
                "next_articles": next_articles,
                "journey_mode": "sale_optimized",
                "is_sale_optimized": True,
                "sale_journey_title": sale_title,
            }
        )

        # セール価格メタデータを journey 内に集約
        if price_changed:
            adapted["price_changed"] = True
            adapted["change_reason"] = article_output.get("change_reason", "")
            adapted["previous_price"] = article_output.get("previous_price")
            adapted["current_price"] = article_output.get("current_price")
            adapted["price_diff"] = article_output.get("price_diff")
            adapted["discount_rate"] = article_output.get("discount_rate")
            adapted["discount_rate_diff"] = article_output.get("discount_rate_diff")

        return adapted

    except Exception as exc:
        # Adapter の失敗で本体処理を止めないため、安全側で元データを返す
        fallback = dict(journey) if isinstance(journey, dict) else {}
        fallback["journey_mode"] = fallback.get("journey_mode", "standard")
        fallback["is_sale_optimized"] = False
        fallback["sale_adapter_error"] = str(exc)
        return fallback
