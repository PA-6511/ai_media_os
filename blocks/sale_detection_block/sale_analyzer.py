import logging
from typing import Any, Dict, List


class SaleAnalyzer:
    """Detects sale opportunities for affiliate article generation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.high_discount_threshold = 50
        self.ultra_discount_threshold = 70
        self.ranking_threshold = 30
        self.short_sale_days = 3

    def analyze(self, sales_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        for store, sales in sales_data.items():
            for sale in sales:
                reasons = self._collect_reasons(sale)
                if reasons:
                    opportunities.append(
                        {
                            "store": store,
                            "title": sale.get("title", "不明作品"),
                            "sale_type": sale.get("sale_type", "セール"),
                            "discount_rate": int(sale.get("discount_rate", 0)),
                            "rank": int(sale.get("rank", 9999)),
                            "days_left": int(sale.get("days_left", 99)),
                            "points_back": int(sale.get("points_back", 0)),
                            "reasons": reasons,
                        }
                    )

        self.logger.info("sale opportunities detected=%d", len(opportunities))
        return opportunities

    def _collect_reasons(self, sale: Dict[str, Any]) -> List[str]:
        reasons: List[str] = []
        discount_rate = int(sale.get("discount_rate", 0))
        rank = int(sale.get("rank", 9999))
        days_left = int(sale.get("days_left", 99))
        points_back = int(sale.get("points_back", 0))
        sale_type = str(sale.get("sale_type", ""))

        if discount_rate >= self.ultra_discount_threshold:
            reasons.append("70%OFFセール検出")
        elif discount_rate >= self.high_discount_threshold:
            reasons.append("高割引セール検出")

        if rank <= self.ranking_threshold:
            reasons.append("ランキング作品が対象")

        if days_left <= self.short_sale_days:
            reasons.append("セール期間が短い")

        if points_back >= 20 or "ポイント" in sale_type:
            reasons.append("ポイント還元セール")

        if "まとめ買い" in sale_type:
            reasons.append("まとめ買いセール")

        if "期間" in sale_type:
            reasons.append("期間限定セール")

        if "半額" in sale_type or discount_rate >= 50:
            reasons.append("半額セール")

        return list(dict.fromkeys(reasons))
