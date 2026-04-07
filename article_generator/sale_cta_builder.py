from __future__ import annotations

# sale_cta_builder.py
# sale_article 向け CTA 文言・HTML を生成する。
#
# price_changed = True かつ article_type = sale_article の場合は
# CTA AB テスト variant を使用する。
# それ以外は従来の CTA 文言・HTML をそのまま返す。

from html import escape
from typing import Any

from article_generator.cta_experiment_registry import EXPERIMENT_PRICE_CHANGED_V1
from article_generator.cta_variant_selector import select_variant
from article_generator.cta_ab_formatter import build_cta_block_from_variant


def _to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_price_change_intensity_cta(article_data: dict[str, Any]) -> str:
    """値下げ幅・割引率に応じた買い時 CTA を返す。"""
    diff = _to_float(article_data.get("price_diff"))
    discount = _to_float(article_data.get("discount_rate"))

    # 強訴求: 大きい値下げ or 高割引
    if (diff is not None and diff <= -200) or (discount is not None and discount >= 30.0):
        return (
            "セール価格が更新されているため、今の価格を優先して確認してください。"
            "値下げ幅が大きい可能性があるため、購入候補なら早めの判断がおすすめです。"
            "セール中にまとめ買いしたい方は全巻情報もあわせて確認してください。"
        )

    # 中訴求: ある程度の値下げ
    if (diff is not None and diff <= -80) or (discount is not None and discount >= 15.0):
        return (
            "値下げが入っている可能性があるため、ストアページで最新価格をチェックしてください。"
            "最新巻と全巻情報をあわせて見ると、買い時の判断がしやすくなります。"
        )

    # 弱訴求: 軽微な変動
    return (
        "価格が更新されているため、購入前に最新価格を確認してください。"
        "関連セール情報もあわせて確認しておくと安心です。"
    )


def build_sale_cta_text(article_data: dict[str, Any]) -> str:
    """価格情報に応じた CTA 文言を返す。

    price_changed = True かつ sale_article の場合は AB テスト variant の body を使用する。
    それ以外は従来ロジックで生成する。
    """
    price_changed = bool(article_data.get("price_changed", False))
    article_type = str(article_data.get("article_type", "")).strip()

    # ---- AB テスト対象: price_changed = True かつ sale_article ----
    if price_changed and article_type == "sale_article":
        variant = select_variant(EXPERIMENT_PRICE_CHANGED_V1, article_data)
        if variant:
            base = str(variant.get("body", "")).strip()
            intensity = _build_price_change_intensity_cta(article_data)
            return base + intensity

    # ---- 従来ロジック（price_changed = False または AB テスト外） ----
    change_reason = str(article_data.get("change_reason", "")).strip()
    discount_rate = _to_float(article_data.get("discount_rate"))
    price_diff = _to_float(article_data.get("price_diff"))

    messages: list[str] = []

    if price_changed:
        messages.append("値下げが確認できたため、価格が変わる前にストアで最新状況を確認してください。")
        messages.append("セール対象かどうかを今のうちにチェックしておくのがおすすめです。")

    if discount_rate is not None and discount_rate >= 20.0:
        messages.append("割引率が高いため、早めに確認しておくのがおすすめです。")

    if change_reason == "discount_rate_threshold":
        messages.append("割引率が変化したため、最新価格を優先して確認してください。")

    if price_diff is not None and price_diff > 0:
        messages.append("価格が上昇するケースもあるため、購入前に再確認してください。")

    if not messages:
        messages.append("セール価格は変動するため、最新価格をストアページで確認してください。")

    return "".join(messages)


def build_sale_cta_html(article_data: dict[str, Any]) -> str:
    """sale_article 向け CTA HTML を返す。

    price_changed = True かつ article_type = sale_article の場合は
    AB テスト variant から HTML を生成する。
    それ以外は従来の CTA HTML を返す（既存動作を保持）。
    """
    price_changed = bool(article_data.get("price_changed", False))
    article_type = str(article_data.get("article_type", "")).strip()

    # ---- AB テスト対象 ----
    if price_changed and article_type == "sale_article":
        variant = select_variant(EXPERIMENT_PRICE_CHANGED_V1, article_data)
        if variant:
            # 価格変動の強弱に応じた補助文を variant に反映する
            enriched_variant = dict(variant)
            current_body = str(enriched_variant.get("body", "")).strip()
            intensity = _build_price_change_intensity_cta(article_data)
            enriched_variant["body"] = current_body + intensity
            return build_cta_block_from_variant(
                variant=enriched_variant,
                article_data=article_data,
                experiment_name=EXPERIMENT_PRICE_CHANGED_V1,
            )

    # ---- 従来ロジック（AB テスト外 / フォールバック） ----
    text = build_sale_cta_text(article_data)
    cls = "cta-box sale-updated" if price_changed else "cta-box"
    return f'<div class="{cls}"><p>{escape(text)}</p></div>'
