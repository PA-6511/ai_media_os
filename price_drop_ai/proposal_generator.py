from __future__ import annotations

from typing import Any

from price_drop_ai.change_detector import is_significant_change


def build_refresh_proposal(change_event: dict[str, Any]) -> dict[str, Any] | None:
    """価格変動イベントから sale_article 再生成候補を構築する。"""
    if str(change_event.get("article_type", "")).strip() != "sale_article":
        return None

    if not is_significant_change(change_event):
        return None

    return {
        "work_id": str(change_event.get("work_id", "")).strip(),
        "keyword": str(change_event.get("keyword", "")).strip(),
        "article_type": "sale_article",
        "price_changed": True,
        "previous_price": change_event.get("previous_price"),
        "current_price": change_event.get("current_price"),
        "discount_rate": change_event.get("discount_rate"),
        "price_diff": change_event.get("price_diff"),
        "change_reason": str(change_event.get("change_reason", "price_changed")),
        "decision_hint": "republish_allowed_price_changed",
    }


class PriceDropProposalGenerator:
    """旧実装との互換用ラッパークラス。"""

    def generate(self, drop_event: dict[str, Any]) -> dict[str, Any]:
        proposal = build_refresh_proposal(drop_event)
        if proposal:
            return proposal
        return {
            "work_id": str(drop_event.get("work_id", "")).strip(),
            "keyword": str(drop_event.get("keyword", "")).strip(),
            "article_type": str(drop_event.get("article_type", "")).strip() or "sale_article",
            "price_changed": False,
            "change_reason": str(drop_event.get("change_reason", "no_change")),
            "decision_hint": "skip_no_significant_change",
        }
