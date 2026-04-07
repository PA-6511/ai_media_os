from __future__ import annotations

# cta_variant_selector.py
# 記事ごとにどの CTA バリアントを使うかを決定論的に選択する。
#
# 選択ルール:
#   - work_id + keyword + experiment_name を SHA-256 でハッシュし、
#     バリアント数で割った余りでインデックスを決める。
#   - 同じ work_id + keyword の組み合わせでは常に同じバリアントが返る。
#   - price_changed = False の場合はバリアントなし（空辞書）を返す。
#   - article_type が sale_article 以外の場合も AB テスト対象外（空辞書）。

import hashlib
from typing import Any

from article_generator.cta_experiment_registry import (
    EXPERIMENT_PRICE_CHANGED_V1,
    get_variants_for_experiment,
)


# =====================================================================
# 内部ユーティリティ
# =====================================================================


def stable_bucket(key: str, modulo: int) -> int:
    """key を SHA-256 でハッシュし modulo で割った余りを返す（決定論的）。

    Args:
        key:     ハッシュに使う文字列キー。
        modulo:  割る数（バリアント数など）。

    Returns:
        0 以上 modulo 未満の整数。
        modulo <= 0 のときは 0 を返す（ゼロ除算を防ぐ）。
    """
    if modulo <= 0:
        return 0
    try:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        # 上位 16 hex 文字（64 bit）を整数化してバケットを決定
        return int(digest[:16], 16) % modulo
    except Exception:
        return 0


def _is_ab_test_target(article_data: dict[str, Any]) -> bool:
    """この記事が CTA AB テスト対象かを判定する。

    条件: price_changed = True かつ article_type = "sale_article"
    """
    price_changed = bool(article_data.get("price_changed", False))
    article_type = str(article_data.get("article_type", "")).strip()
    return price_changed and article_type == "sale_article"


# =====================================================================
# 公開 API
# =====================================================================


def select_variant(
    experiment_name: str,
    article_data: dict[str, Any],
) -> dict[str, Any]:
    """article_data に基づき、実験のバリアントを決定論的に選択する。

    同じ work_id + keyword の組み合わせでは常に同じバリアントが返る。

    Args:
        experiment_name: 実験名（cta_experiment_registry の定数を使用）。
        article_data:    記事データ辞書。

    Returns:
        選択されたバリアント辞書（コピー）。
        AB テスト対象外か取得失敗の場合は空辞書を返す。
    """
    if not _is_ab_test_target(article_data):
        return {}

    variants = get_variants_for_experiment(experiment_name)
    if not variants:
        return {}

    # ハッシュキー: work_id + keyword + experiment_name の組み合わせ
    work_id = str(article_data.get("work_id", "")).strip()
    keyword = str(article_data.get("keyword", "")).strip()
    hash_key = f"{work_id}::{keyword}::{experiment_name}"

    try:
        bucket = stable_bucket(hash_key, len(variants))
        return dict(variants[bucket])
    except Exception:
        # フォールバック: 先頭バリアントを返す
        return dict(variants[0])


def select_price_changed_variant(article_data: dict[str, Any]) -> dict[str, Any]:
    """price_changed 記事用 CTA AB テストのバリアントを選択する。

    内部的に EXPERIMENT_PRICE_CHANGED_V1 を使用する省略形。
    """
    return select_variant(EXPERIMENT_PRICE_CHANGED_V1, article_data)


def get_cta_mode(article_data: dict[str, Any]) -> str:
    """CTA モード文字列を返す。

    Returns:
        "ab_test"  : price_changed = True かつ sale_article → AB テスト対象
        "standard" : それ以外 → 従来 CTA
    """
    return "ab_test" if _is_ab_test_target(article_data) else "standard"


def describe_variant_selection(
    experiment_name: str,
    article_data: dict[str, Any],
) -> dict[str, Any]:
    """デバッグ用: バリアント選択の詳細情報を辞書で返す。

    Returns:
        {
            "experiment_name": str,
            "is_ab_test_target": bool,
            "hash_key": str,
            "bucket": int,
            "total_variants": int,
            "selected_variant_name": str,
            "selected_tone": str,
        }
    """
    is_target = _is_ab_test_target(article_data)
    variants = get_variants_for_experiment(experiment_name)

    work_id = str(article_data.get("work_id", "")).strip()
    keyword = str(article_data.get("keyword", "")).strip()
    hash_key = f"{work_id}::{keyword}::{experiment_name}"

    bucket = stable_bucket(hash_key, len(variants)) if (is_target and variants) else -1
    selected = variants[bucket] if (is_target and variants and bucket >= 0) else {}

    return {
        "experiment_name": experiment_name,
        "is_ab_test_target": is_target,
        "hash_key": hash_key,
        "bucket": bucket,
        "total_variants": len(variants),
        "selected_variant_name": selected.get("name", ""),
        "selected_tone": selected.get("tone", ""),
    }
