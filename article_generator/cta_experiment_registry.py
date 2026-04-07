from __future__ import annotations

# cta_experiment_registry.py
# CTA AB テスト実験定義レジストリ。
#
# 役割:
#   - 実験名・バリアント名・CTA 文言（title / body / button_text / note / tone）を一元管理する。
#   - 実験の追加はこのファイルの _EXPERIMENTS 辞書にエントリを追加するだけでよい。
#   - 実行時に import されるだけで、I/O・状態変化は一切行わない。

from typing import Any


# =====================================================================
# 実験名定数
# =====================================================================

#: price_changed 記事向け CTA AB テスト（第一弾）
EXPERIMENT_PRICE_CHANGED_V1 = "price_changed_sale_cta_v1"


# =====================================================================
# バリアント定義
#
# 各バリアント辞書のキー:
#   name        : バリアント識別子（"A" / "B" / "C" ...）
#   title       : CTA ブロック見出し
#   body        : CTA 本文
#   button_text : ボタン文言
#   note        : 補助文（ボタン直下の小文字説明）
#   tone        : 訴求トーン識別子（buy_journey との整合に使用）
#                 "direct" / "discount" / "compare"
# =====================================================================

_EXPERIMENTS: dict[str, list[dict[str, Any]]] = {
    EXPERIMENT_PRICE_CHANGED_V1: [
        {
            # Variant A: 直球訴求 ─ 価格変動を率直に伝え行動を促す
            "name": "A",
            "title": "価格が変わったので今すぐ確認",
            "body": "値下げが確認できたため、まずは現在価格をチェックしてください。",
            "button_text": "最新価格を確認する",
            "note": "価格変動があったため、早めに確認するのがおすすめです。",
            "tone": "direct",
        },
        {
            # Variant B: 割引訴求 ─ 「セール中かも」の期待感を煽る
            "name": "B",
            "title": "セール中の可能性があります",
            "body": "割引率が変化しているため、対象巻や価格状況を確認するのがおすすめです。",
            "button_text": "セール状況を見る",
            "note": "セール価格は短期間で変わることがあります。",
            "tone": "discount",
        },
        {
            # Variant C: 比較訴求 ─ 全巻・最新巻情報もまとめて見せる
            "name": "C",
            "title": "価格比較しながら確認",
            "body": (
                "現在価格だけでなく、全巻情報や最新巻もあわせて見ると"
                "判断しやすくなります。"
            ),
            "button_text": "関連情報も見る",
            "note": "購入前に他の巻の価格状況もあわせて確認してください。",
            "tone": "compare",
        },
    ],
}


# =====================================================================
# 公開 API
# =====================================================================


def get_price_changed_cta_experiment() -> dict[str, Any]:
    """price_changed 記事用 CTA 実験の定義をまとめて返す。

    Returns:
        {
            "name": 実験名,
            "variants": [バリアント辞書, ...],
        }
    """
    return {
        "name": EXPERIMENT_PRICE_CHANGED_V1,
        "variants": list(_EXPERIMENTS[EXPERIMENT_PRICE_CHANGED_V1]),
    }


def get_variants_for_experiment(experiment_name: str) -> list[dict[str, Any]]:
    """実験名に対応するバリアント一覧を返す。

    存在しない実験名が渡された場合は空リストを返す（例外を投げない）。
    """
    return [dict(v) for v in _EXPERIMENTS.get(experiment_name, [])]


def get_experiment_names() -> list[str]:
    """登録済みの実験名一覧を返す。"""
    return list(_EXPERIMENTS.keys())


def get_variant_by_name(experiment_name: str, variant_name: str) -> dict[str, Any]:
    """実験名とバリアント名を指定して対応するバリアント辞書を返す。

    見つからない場合は空辞書を返す。
    デバッグや強制上書きテスト用途を想定。
    """
    for v in _EXPERIMENTS.get(experiment_name, []):
        if v.get("name") == variant_name:
            return dict(v)
    return {}
