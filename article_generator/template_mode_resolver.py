from __future__ import annotations

# template_mode_resolver.py
# article_type / price_changed / release_changed の組み合わせから
# 最終テンプレモードを返すリゾルバ。
# content_formatter / generator から呼び出される。

from typing import Any


# ------------------------------------------------------------------ #
# テンプレモード定数
# ------------------------------------------------------------------ #

# 標準（シグナルなし）
TEMPLATE_MODE_STANDARD = "standard"

# セール単独
TEMPLATE_MODE_SALE_PRICE_CHANGED = "sale_price_changed"
TEMPLATE_MODE_SALE_STANDARD = "sale_standard"

# 新刊単独
TEMPLATE_MODE_LATEST_VOLUME_RELEASE = "latest_volume_release"
TEMPLATE_MODE_LATEST_VOLUME_STANDARD = "latest_volume_standard"

# 複合
TEMPLATE_MODE_COMBINED_SALE_RELEASE = "combined_sale_release"
TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE = "combined_latest_release_price"

# 巻数ガイド / summary + 新刊
TEMPLATE_MODE_VOLUME_GUIDE_RELEASE = "volume_guide_release"
TEMPLATE_MODE_SUMMARY_RELEASE = "summary_release"


def resolve_template_mode(article_data: dict[str, Any]) -> str:
    """article_type / price_changed / release_changed の組み合わせから
    テンプレモードを決定して返す。

    判定優先順:
        1. 複合シグナル（price_changed AND release_changed）
        2. 単独セールシグナル（sale_article + price_changed）
        3. 単独新刊シグナル（latest_volume / volume_guide / summary + release_changed）
        4. フォールバック（article_type ごとのデフォルト）

    Args:
        article_data: 記事データ辞書（article_plan / article_output いずれも可）。

    Returns:
        テンプレモード文字列。
    """
    try:
        article_type = str(article_data.get("article_type", "")).strip().lower()
        price_changed = bool(article_data.get("price_changed", False))
        release_changed = bool(article_data.get("release_changed", False))

        # ---- 1. 複合シグナル判定（両方あり）----
        if price_changed and release_changed:
            if article_type == "sale_article":
                return TEMPLATE_MODE_COMBINED_SALE_RELEASE
            if article_type == "latest_volume":
                return TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE
            if article_type == "volume_guide":
                # volume_guide + 両シグナル → volume_guide_release で吸収
                return TEMPLATE_MODE_VOLUME_GUIDE_RELEASE
            if article_type == "summary":
                return TEMPLATE_MODE_SUMMARY_RELEASE

        # ---- 2. セール単独シグナル ----
        if article_type == "sale_article":
            if price_changed:
                return TEMPLATE_MODE_SALE_PRICE_CHANGED
            return TEMPLATE_MODE_SALE_STANDARD

        # ---- 3. 新刊単独シグナル ----
        if release_changed:
            if article_type == "latest_volume":
                return TEMPLATE_MODE_LATEST_VOLUME_RELEASE
            if article_type == "volume_guide":
                return TEMPLATE_MODE_VOLUME_GUIDE_RELEASE
            if article_type == "summary":
                return TEMPLATE_MODE_SUMMARY_RELEASE

        # ---- 4. フォールバック（latest_volume 通常 / standard）----
        if article_type == "latest_volume":
            return TEMPLATE_MODE_LATEST_VOLUME_STANDARD

        return TEMPLATE_MODE_STANDARD

    except Exception as exc:
        # リゾルバ失敗でパイプラインを止めないため standard を返す
        import sys
        print(f"[template_mode_resolver] ERROR: {exc}", file=sys.stderr)
        return TEMPLATE_MODE_STANDARD


def is_combined_signal(article_data: dict[str, Any]) -> bool:
    """price_changed AND release_changed が両方 True かどうかを返す。

    Args:
        article_data: 記事データ辞書。

    Returns:
        両方 True なら True、それ以外は False。
    """
    price_changed = bool(article_data.get("price_changed", False))
    release_changed = bool(article_data.get("release_changed", False))
    return price_changed and release_changed


def is_sale_mode(template_mode: str) -> bool:
    """テンプレモードがセール系かどうかを返す。"""
    return template_mode in {
        TEMPLATE_MODE_SALE_PRICE_CHANGED,
        TEMPLATE_MODE_SALE_STANDARD,
        TEMPLATE_MODE_COMBINED_SALE_RELEASE,
    }


def is_release_mode(template_mode: str) -> bool:
    """テンプレモードが新刊系かどうかを返す。"""
    return template_mode in {
        TEMPLATE_MODE_LATEST_VOLUME_RELEASE,
        TEMPLATE_MODE_LATEST_VOLUME_STANDARD,
        TEMPLATE_MODE_COMBINED_SALE_RELEASE,
        TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE,
        TEMPLATE_MODE_VOLUME_GUIDE_RELEASE,
        TEMPLATE_MODE_SUMMARY_RELEASE,
    }


def is_combined_mode(template_mode: str) -> bool:
    """テンプレモードが複合テンプレかどうかを返す。"""
    return template_mode in {
        TEMPLATE_MODE_COMBINED_SALE_RELEASE,
        TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE,
    }
