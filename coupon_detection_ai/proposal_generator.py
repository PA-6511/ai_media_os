import logging
from typing import Any, Dict


class CouponProposalGenerator:
    """Generate article proposals from detected coupon events."""

    STORE_LABEL = {
        "amazon": "Kindle",
        "kobo": "楽天Kobo",
        "dmm": "DMMブックス",
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, coupon_event: Dict[str, Any]) -> Dict[str, Any]:
        store = str(coupon_event.get("store", "store")).lower()
        coupon_type = str(coupon_event.get("coupon_type", "percentage"))
        discount = int(coupon_event.get("discount", 0))
        target = str(coupon_event.get("target", "manga"))

        if coupon_type == "percentage":
            title = f"{self.STORE_LABEL.get(store, store)}{target} {discount}%OFFクーポン配布中"
        else:
            title = f"{self.STORE_LABEL.get(store, store)}{discount}円引きクーポン配布中"

        proposal = {
            "source": "coupon_detection_ai",
            "action": "generate_coupon_article",
            "title": title,
            "store": store,
            "discount": discount,
            "priority": self._priority(coupon_event),
            "reason": self._reason(coupon_event),
            "metadata": {
                "coupon_type": coupon_type,
                "target": target,
                "target_count": int(coupon_event.get("target_count", 0)),
                "expires_at": coupon_event.get("expires_at", ""),
            },
        }
        self.logger.info("coupon proposal generated store=%s title=%s", store, title)
        return proposal

    @staticmethod
    def _priority(event: Dict[str, Any]) -> float:
        coupon_type = str(event.get("coupon_type", "percentage"))
        discount = float(event.get("discount", 0.0))
        target_count = float(event.get("target_count", 0.0))

        score = 0.72
        if coupon_type == "percentage":
            score += min(discount / 100.0 * 0.22, 0.22)
        else:
            score += min(discount / 1000.0 * 0.18, 0.18)

        if target_count >= 50:
            score += 0.06
        if target_count >= 100:
            score += 0.03
        return round(min(score, 0.99), 2)

    @staticmethod
    def _reason(event: Dict[str, Any]) -> str:
        coupon_type = str(event.get("coupon_type", "percentage"))
        discount = int(event.get("discount", 0))
        if coupon_type == "percentage":
            return f"{discount}%OFFクーポンを検出"
        return f"{discount}円引きクーポンを検出"
