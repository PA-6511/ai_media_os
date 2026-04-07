from __future__ import annotations

import html
from typing import Any

from buyer_journey_ai.cta_optimizer import build_cta_text
from buyer_journey_ai.next_article_selector import select_next_articles
from buyer_journey_ai.release_journey_adapter import adapt_journey_for_release
from buyer_journey_ai.sale_journey_adapter import adapt_journey_for_sale
from buyer_journey_ai.stage_classifier import classify_stage


def build_journey(article_output: dict[str, Any]) -> dict[str, Any]:
    """記事データから buyer journey 情報を組み立てる。

    処理順:
        1. stage / next_articles / cta_text を基本ルールで生成
        2. release_journey_adapter で新刊補正
        3. sale_journey_adapter でセール補正（price_changed が True の場合のみ）
    """
    keyword = str(article_output.get("keyword", "")).strip()
    article_type = str(article_output.get("article_type", "")).strip()
    release_changed = bool(article_output.get("release_changed", False))
    price_changed = bool(article_output.get("price_changed", False))
    availability = str(article_output.get("current_availability_status", "")).strip()

    try:
        discount_rate = float(article_output.get("discount_rate", 0.0) or 0.0)
    except (TypeError, ValueError):
        discount_rate = 0.0

    try:
        price_diff = float(article_output.get("price_diff", 0.0) or 0.0)
    except (TypeError, ValueError):
        price_diff = 0.0

    stage = classify_stage(
        keyword=keyword,
        article_type=article_type,
        release_changed=release_changed,
        availability_status=availability,
        price_changed=price_changed,
        discount_rate=discount_rate,
    )
    next_articles = select_next_articles(
        article_output=article_output,
        stage=stage,
        release_changed=release_changed,
        price_changed=price_changed,
    )
    cta_text = build_cta_text(
        stage=stage,
        release_changed=release_changed,
        availability_status=availability,
        article_type=article_type,
        price_changed=price_changed,
        discount_rate=discount_rate,
        price_diff=price_diff,
    )

    journey: dict[str, Any] = {
        "stage": stage,
        "cta_text": cta_text,
        "next_articles": next_articles,
        "journey_mode": "standard",
        "is_release_optimized": False,
        "is_sale_optimized": False,
        "release_journey_title": "次に読むならこちら",
        "sale_journey_title": "次に読むならこちら",
    }

    # release_changed があれば release adapter で補正
    journey = adapt_journey_for_release(article_output, journey)

    # price_changed があれば sale adapter で追加補正（release より優先度が高い）
    journey = adapt_journey_for_sale(article_output, journey)

    # release と sale の両最適化が有効な場合は combined_optimized を明示
    is_release = bool(journey.get("is_release_optimized", False))
    is_sale = bool(journey.get("is_sale_optimized", False))
    if is_release and is_sale:
        journey["journey_mode"] = "combined_optimized"

    return journey


def build_journey_html(journey: dict[str, Any]) -> str:
    """journey データを記事下挿入用 HTML へ変換する。

    セール最適化（is_sale_optimized）が True の場合は
    sale-journey-box クラスを付与し、セール向けタイトル・価格情報を表示する。
    """
    cta_text = html.escape(str(journey.get("cta_text", "")).strip())
    is_sale_optimized = bool(journey.get("is_sale_optimized", False))
    is_release_optimized = bool(journey.get("is_release_optimized", False))

    # タイトルを決定（セール優先 → 新刊 → デフォルト）
    if is_sale_optimized:
        heading = html.escape(
            str(journey.get("sale_journey_title", "今の価格をチェックするならこちら")).strip()
        )
    else:
        heading = html.escape(
            str(journey.get("release_journey_title", "次に読むならこちら")).strip()
        )

    # セール価格メタ情報（price_changed のとき表示）
    price_meta = ""
    if is_sale_optimized and bool(journey.get("price_changed", False)):
        previous_price = journey.get("previous_price")
        current_price = journey.get("current_price")
        discount_rate = journey.get("discount_rate")
        price_diff = journey.get("price_diff")

        parts: list[str] = []
        if previous_price is not None:
            parts.append(f"変更前: {int(previous_price)}円")
        if current_price is not None:
            parts.append(f"現在価格: {int(current_price)}円")
        if discount_rate is not None:
            parts.append(f"割引率: {float(discount_rate):.0f}%")
        if price_diff is not None and float(price_diff) < 0:
            parts.append(f"値下げ幅: {abs(int(float(price_diff)))}円")

        if parts:
            price_meta = (
                '<p class="sale-journey-price-meta">'
                + html.escape(" / ".join(parts))
                + "</p>"
            )

    # 新刊メタ情報（release_changed のとき表示）
    release_meta = ""
    if is_release_optimized and not is_sale_optimized:
        release_volume = journey.get("current_latest_volume_number")
        release_date = str(journey.get("current_latest_release_date", "")).strip()
        release_status = str(journey.get("current_availability_status", "")).strip()
        if release_volume is not None or release_date or release_status:
            volume_text = f"{release_volume}巻" if release_volume is not None else "最新巻"
            status_text = html.escape(release_status or "不明")
            date_text = html.escape(release_date or "未定")
            release_meta = (
                '<p class="release-journey-meta">'
                f"最新巻: {html.escape(volume_text)} / 配信日: {date_text} / 配信状態: {status_text}"
                "</p>"
            )

    items: list[str] = []
    next_articles = journey.get("next_articles", [])
    if isinstance(next_articles, list):
        for row in next_articles:
            if not isinstance(row, dict):
                continue
            title = html.escape(str(row.get("title", "")).strip())
            url = html.escape(str(row.get("url", "")).strip())
            if not title or not url:
                continue
            items.append(f'<li><a href="{url}">{title}</a></li>')

    if not items:
        return ""

    # CSS クラスを決定
    if is_sale_optimized:
        box_class = "journey-box sale-journey-box"
    elif is_release_optimized:
        box_class = "journey-box release-journey-box"
    else:
        box_class = "journey-box"

    return (
        f'<div class="{box_class}">'
        f"<h2>{heading}</h2>"
        f"{price_meta}"
        f"{release_meta}"
        f"<p>{cta_text}</p>"
        "<ul>"
        f"{''.join(items)}"
        "</ul>"
        "</div>"
    )


def insert_journey_block(content_html: str, journey_html: str) -> str:
    """既存本文末尾に journey-box を差し込む。"""
    base_html = (content_html or "").strip()
    block = (journey_html or "").strip()

    if not block:
        return base_html
    if (
        '<div class="journey-box">' in base_html
        or "release-journey-box" in base_html
        or "sale-journey-box" in base_html
    ):
        return base_html

    return f"{base_html}{block}"
