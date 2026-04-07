import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup


class CouponParser:
    """Parse coupon payloads from API JSON or HTML pages."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_json(self, source_store: str, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = payload.get("items", [])
        else:
            rows = []

        parsed: List[Dict[str, Any]] = []
        for row in rows:
            parsed.append(self._normalize(source_store, row))
        return parsed

    def parse_html(self, source_store: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".coupon-item")
        rows: List[Dict[str, Any]] = []

        for card in cards:
            row = {
                "store": card.get("data-store", source_store),
                "coupon_type": card.get("data-coupon-type", self._text(card, ".coupon-type", "percentage")),
                "discount": self._to_int(card.get("data-discount", self._text(card, ".discount", "0"))),
                "target": card.get("data-target", self._text(card, ".target", "manga")),
                "target_count": self._to_int(card.get("data-target-count", self._text(card, ".target-count", "0"))),
                "expires_at": card.get("data-expires-at", self._text(card, ".expires-at", "")),
            }
            rows.append(self._normalize(source_store, row))

        return rows

    def _normalize(self, source_store: str, row: Dict[str, Any]) -> Dict[str, Any]:
        coupon_type = str(row.get("coupon_type", "percentage")).strip().lower()
        if coupon_type not in {"percentage", "yen"}:
            coupon_type = "percentage"

        return {
            "store": str(row.get("store", source_store)).strip().lower() or source_store,
            "coupon_type": coupon_type,
            "discount": int(float(row.get("discount", 0))),
            "target": str(row.get("target", "manga")).strip() or "manga",
            "target_count": int(float(row.get("target_count", 0))),
            "expires_at": str(row.get("expires_at", "")).strip(),
        }

    @staticmethod
    def _text(node, selector: str, default: str) -> str:
        found = node.select_one(selector)
        return found.get_text(strip=True) if found else default

    @staticmethod
    def _to_int(value: str) -> int:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0
