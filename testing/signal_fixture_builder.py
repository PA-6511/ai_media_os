from __future__ import annotations

# signal_fixture_builder.py
# normal / price_only / release_only / combined の4パターンのテスト用
# article_data (article_plan 相当) を生成して返す。
#
# 使用方法:
#   from testing.signal_fixture_builder import build_fixtures, FIXTURE_NAMES
#   fixtures = build_fixtures()          # dict[str, dict]
#   fixture  = fixtures["combined"]      # 特定パターンだけ取得

from typing import Any

# ------------------------------------------------------------------ #
# 共通ベースデータ
# ------------------------------------------------------------------ #

_BASE_WORK: dict[str, Any] = {
    "work_id": "manga_fixture_001",
    "keyword": "テスト漫画 セール",
    "article_type": "sale_article",
    "title": "テスト漫画（フィクスチャ用）",
    "slug": "test-manga-fixture-sale-article",
    "priority": 100,
    # ---- 価格系 ----
    "previous_price": 660,
    "current_price": 528,
    "price_diff": -132,
    "discount_rate": 20.0,
    "discount_rate_diff": 20.0,
    "change_reason": "discount_rate_threshold",
    # ---- 新刊系 ----
    "previous_latest_volume_number": 12,
    "current_latest_volume_number": 13,
    "previous_latest_release_date": "2025-12-10",
    "current_latest_release_date": "2026-03-20",
    "previous_availability_status": "available",
    "current_availability_status": "available",
    "release_change_reason": "new_volume",
    # ---- 関連情報 ----
    "internal_link_hints": [
        {"label": "前巻", "url": "/test-manga-vol12/", "type": "volume"},
        {"label": "全巻まとめ", "url": "/test-manga-all/", "type": "volume_guide"},
    ],
    "related_links": [],
    # ---- テスト用メタ ----
    "checked_at": "2026-03-12T12:00:00+00:00",
    "dry_run": True,
}

_BASE_VOLUME: dict[str, Any] = {
    "work_id": "manga_fixture_002",
    "keyword": "テスト漫画 最新巻",
    "article_type": "latest_volume",
    "title": "テスト漫画（フィクスチャ用）最新巻",
    "slug": "test-manga-fixture-latest-volume",
    "priority": 70,
    # ---- 価格系 ----
    "previous_price": 660,
    "current_price": 528,
    "price_diff": -132,
    "discount_rate": 20.0,
    "discount_rate_diff": 20.0,
    "change_reason": "discount_rate_threshold",
    # ---- 新刊系 ----
    "previous_latest_volume_number": 12,
    "current_latest_volume_number": 13,
    "previous_latest_release_date": "2025-12-10",
    "current_latest_release_date": "2026-03-20",
    "previous_availability_status": "available",
    "current_availability_status": "available",
    "release_change_reason": "new_volume",
    # ---- 関連情報 ----
    "internal_link_hints": [],
    "related_links": [],
    "checked_at": "2026-03-12T12:00:00+00:00",
    "dry_run": True,
}

# ------------------------------------------------------------------ #
# フィクスチャ名定義
# ------------------------------------------------------------------ #

FIXTURE_NAMES: tuple[str, ...] = (
    "normal",
    "price_only",
    "release_only",
    "combined",
)

# ---- sale_article ×各シグナル ----
SALE_FIXTURE_NAMES: tuple[str, ...] = (
    "sale_normal",
    "sale_price_only",
    "sale_release_only",
    "sale_combined",
)

# ---- latest_volume ×各シグナル ----
VOLUME_FIXTURE_NAMES: tuple[str, ...] = (
    "volume_normal",
    "volume_release_only",
    "volume_combined",
)


# ------------------------------------------------------------------ #
# フィクスチャ生成関数
# ------------------------------------------------------------------ #

def _sale_fixture(
    *,
    price_changed: bool,
    release_changed: bool,
    label: str,
) -> dict[str, Any]:
    data = dict(_BASE_WORK)
    data["price_changed"] = price_changed
    data["release_changed"] = release_changed
    # シグナルがない場合は変動値をリセットして「通常時」を再現する
    if not price_changed:
        data["previous_price"] = 660
        data["current_price"] = 660
        data["price_diff"] = 0.0
        data["discount_rate"] = 0.0
        data["discount_rate_diff"] = 0.0
        data["change_reason"] = "no_change"
    if not release_changed:
        data["previous_latest_volume_number"] = 12
        data["current_latest_volume_number"] = 12
        data["previous_latest_release_date"] = "2025-12-10"
        data["current_latest_release_date"] = "2025-12-10"
        data["release_change_reason"] = "no_change"
    data["_fixture_label"] = label
    return data


def _volume_fixture(
    *,
    price_changed: bool,
    release_changed: bool,
    label: str,
) -> dict[str, Any]:
    data = dict(_BASE_VOLUME)
    data["price_changed"] = price_changed
    data["release_changed"] = release_changed
    if not price_changed:
        data["previous_price"] = 660
        data["current_price"] = 660
        data["price_diff"] = 0.0
        data["discount_rate"] = 0.0
        data["discount_rate_diff"] = 0.0
        data["change_reason"] = "no_change"
    if not release_changed:
        data["previous_latest_volume_number"] = 12
        data["current_latest_volume_number"] = 12
        data["previous_latest_release_date"] = "2025-12-10"
        data["current_latest_release_date"] = "2025-12-10"
        data["release_change_reason"] = "no_change"
    data["_fixture_label"] = label
    return data


# ------------------------------------------------------------------ #
# パブリック API
# ------------------------------------------------------------------ #

def build_fixtures(article_type: str = "sale_article") -> dict[str, dict[str, Any]]:
    """normal / price_only / release_only / combined の4パターンを返す。

    Args:
        article_type: "sale_article" または "latest_volume"。
            "sale_article" の場合は _BASE_WORK ベース。
            "latest_volume" の場合は _BASE_VOLUME ベース。

    Returns:
        {fixture_name: article_data} の辞書。
    """
    builder = _sale_fixture if article_type == "sale_article" else _volume_fixture

    return {
        "normal": builder(
            price_changed=False,
            release_changed=False,
            label="normal",
        ),
        "price_only": builder(
            price_changed=True,
            release_changed=False,
            label="price_only",
        ),
        "release_only": builder(
            price_changed=False,
            release_changed=True,
            label="release_only",
        ),
        "combined": builder(
            price_changed=True,
            release_changed=True,
            label="combined",
        ),
    }


def build_all_fixtures() -> dict[str, dict[str, Any]]:
    """sale_article / latest_volume の全8パターンを返す。

    Returns:
        {fixture_name: article_data} の辞書。
        キーは "sale_normal", "sale_price_only" ... など。
    """
    sale_fixtures = build_fixtures("sale_article")
    volume_fixtures = build_fixtures("latest_volume")

    result: dict[str, dict[str, Any]] = {}
    for name, data in sale_fixtures.items():
        result[f"sale_{name}"] = data
    for name, data in volume_fixtures.items():
        if name in ("normal", "release_only", "combined"):
            result[f"volume_{name}"] = data
    return result


def get_combined_fixture(article_type: str = "sale_article") -> dict[str, Any]:
    """combined パターンだけを返すショートカット。"""
    return build_fixtures(article_type)["combined"]


def get_fixture(name: str, article_type: str = "sale_article") -> dict[str, Any]:
    """名前を指定して1件取得するショートカット。

    Args:
        name: "normal" | "price_only" | "release_only" | "combined"
        article_type: "sale_article" | "latest_volume"
    """
    fixtures = build_fixtures(article_type)
    if name not in fixtures:
        valid = ", ".join(fixtures.keys())
        raise ValueError(f"不明なフィクスチャ名: {name!r} (有効値: {valid})")
    return fixtures[name]
