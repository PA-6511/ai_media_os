import json
import logging
from typing import Any, Dict, List


class SaleProposalGenerator:
    """Generates Council proposals from sale opportunities."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for item in opportunities:
            main_reason = self._choose_reason(item.get("reasons", []))
            priority = self._score_priority(item)
            store_label = self._store_label(item.get("store", "ebook"))

            proposal = {
                "source": "sale_detection_block",
                "action": "generate_sale_article",
                "title": f"{store_label}漫画セールまとめ",
                "priority": priority,
                "reason": main_reason,
                "metadata": {
                    "work_title": item.get("title", ""),
                    "sale_type": item.get("sale_type", ""),
                    "discount_rate": item.get("discount_rate", 0),
                    "rank": item.get("rank", 9999),
                    "days_left": item.get("days_left", 99),
                    "reasons": item.get("reasons", []),
                },
            }
            proposals.append(proposal)
            self.logger.info("sale proposal: %s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    @staticmethod
    def _choose_reason(reasons: List[str]) -> str:
        priority_order = [
            "70%OFFセール検出",
            "半額セール",
            "ランキング作品が対象",
            "セール期間が短い",
            "ポイント還元セール",
            "まとめ買いセール",
            "期間限定セール",
            "高割引セール検出",
        ]
        for reason in priority_order:
            if reason in reasons:
                return reason
        return reasons[0] if reasons else "セール検出"

    def _score_priority(self, item: Dict[str, Any]) -> float:
        score = 0.55
        discount = int(item.get("discount_rate", 0))
        rank = int(item.get("rank", 9999))
        days_left = int(item.get("days_left", 99))
        points_back = int(item.get("points_back", 0))
        reasons = item.get("reasons", [])

        score += min(discount / 100.0, 0.35)
        if rank <= 10:
            score += 0.12
        elif rank <= 30:
            score += 0.07

        if days_left <= 1:
            score += 0.1
        elif days_left <= 3:
            score += 0.06

        if points_back >= 20:
            score += 0.04

        if "70%OFFセール検出" in reasons:
            score += 0.08

        return round(min(score, 0.99), 2)

    @staticmethod
    def _store_label(store_key: str) -> str:
        mapping = {
            "amazon_kindle": "Kindle",
            "rakuten_kobo": "楽天Kobo",
            "dmm_books": "DMMブックス",
        }
        return mapping.get(store_key, "電子書籍")
