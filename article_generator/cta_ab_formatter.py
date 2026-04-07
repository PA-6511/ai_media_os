from __future__ import annotations

# cta_ab_formatter.py
# AB テストのバリアント辞書を CTA HTML ブロックに変換する。
#
# 出力 HTML の構造:
#   <div class="cta-box cta-variant-{a|b|c}"
#        data-cta-experiment="..."
#        data-cta-variant="...">
#     <h2>CTA タイトル</h2>
#     <p>CTA 本文</p>
#     <a href="#" class="cta-button">ボタン文言</a>
#     <p class="cta-note">補助文</p>  <!-- note があれば -->
#   </div>
#
# 設計方針:
#   - variant が空辞書の場合はフォールバック CTA を返す（例外を投げない）。
#   - HTML エスケープは必ず行う（XSS 対策）。
#   - data 属性には実験名・バリアント名を埋め込み、
#     将来のクリック計測・GA イベント計測と接続しやすくする。

from html import escape
from typing import Any


# =====================================================================
# 公開 API
# =====================================================================


def build_cta_block_from_variant(
    variant: dict[str, Any],
    article_data: dict[str, Any],
    experiment_name: str = "price_changed_sale_cta_v1",
) -> str:
    """選択されたバリアントから CTA HTML ブロックを生成して返す。

    Args:
        variant:         cta_variant_selector.select_variant() の返り値。
                         空辞書の場合はフォールバック CTA を返す。
        article_data:    記事データ辞書（将来の動的差し込みに備えて受け取る）。
        experiment_name: 実験名。data 属性に埋め込む。

    Returns:
        CTA HTML 文字列。
    """
    if not variant:
        return _build_fallback_cta()

    variant_name = str(variant.get("name", "A"))
    title = str(variant.get("title", ""))
    body = str(variant.get("body", ""))
    button_text = str(variant.get("button_text", "確認する"))
    note = str(variant.get("note", ""))

    # CSS クラス: cta-variant-a / cta-variant-b / cta-variant-c
    variant_class = f"cta-variant-{variant_name.lower()}"

    lines: list[str] = [
        f'<div class="cta-box {variant_class}"'
        f' data-cta-experiment="{escape(experiment_name)}"'
        f' data-cta-variant="{escape(variant_name)}">',
    ]

    if title:
        lines.append(f"  <h2>{escape(title)}</h2>")

    if body:
        lines.append(f"  <p>{escape(body)}</p>")

    lines.append(f'  <a href="#" class="cta-button">{escape(button_text)}</a>')

    if note:
        lines.append(f'  <p class="cta-note">{escape(note)}</p>')

    lines.append("</div>")

    return "\n".join(lines)


def build_price_changed_cta_html(
    variant: dict[str, Any],
    article_data: dict[str, Any],
) -> str:
    """price_changed 記事専用の CTA HTML を生成する省略形。

    build_cta_block_from_variant のラッパー。
    experiment_name は EXPERIMENT_PRICE_CHANGED_V1 に固定。
    """
    from article_generator.cta_experiment_registry import EXPERIMENT_PRICE_CHANGED_V1

    return build_cta_block_from_variant(
        variant=variant,
        article_data=article_data,
        experiment_name=EXPERIMENT_PRICE_CHANGED_V1,
    )


# =====================================================================
# 内部ユーティリティ
# =====================================================================


def _build_fallback_cta() -> str:
    """variant が空の場合に使うフォールバック CTA。

    AB テスト実験が設定されていない場合や
    price_changed = False の場合に使う最小 CTA ブロック。
    """
    return (
        '<div class="cta-box">'
        "<p>最新価格をストアページで確認してください。</p>"
        "</div>"
    )
