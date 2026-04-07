from __future__ import annotations

# signal_template_router.py
# price_changed / release_changed の組み合わせから signal_mode を判定し、
# 利用するテンプレートビルダを選択する。

from typing import Any, Callable

SignalBuilder = Callable[[dict[str, Any]], str]


def detect_signal_mode(article_data: dict[str, Any]) -> str:
    """記事データから signal_mode を返す。

    Returns:
        normal | price_only | release_only | combined
    """
    try:
        # 既に上流で決定済みの signal_mode があれば最優先で尊重する。
        explicit = str(article_data.get("signal_mode", "")).strip().lower()
        if explicit in {"normal", "price_only", "release_only", "combined"}:
            return explicit

        price_changed = bool(article_data.get("price_changed", False))
        release_changed = bool(article_data.get("release_changed", False))

        if price_changed and release_changed:
            return "combined"
        if price_changed:
            return "price_only"
        if release_changed:
            return "release_only"
        return "normal"
    except Exception:
        return "normal"


def select_template_builder(article_data: dict[str, Any]) -> str:
    """signal_mode と article_type から利用すべきビルダ識別子を返す。

    戻り値は以下のいずれか:
      - combined_template_builder
      - sale_template_builder
      - release_template_builder
      - standard_formatter

    実際の import は呼び出し側で行う（循環参照回避）。
    """
    signal_mode = detect_signal_mode(article_data)
    article_type = str(article_data.get("article_type", "")).strip()

    if signal_mode == "combined":
        return "combined_template_builder"

    if signal_mode == "price_only":
        if article_type == "sale_article":
            return "sale_template_builder"
        return "standard_formatter"

    if signal_mode == "release_only":
        if article_type in {"latest_volume", "volume_guide", "summary"}:
            return "release_template_builder"
        return "standard_formatter"

    # normal
    if article_type == "sale_article":
        return "sale_template_builder"
    if article_type == "latest_volume":
        return "release_template_builder"
    return "standard_formatter"
