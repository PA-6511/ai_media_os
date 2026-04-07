import logging
from typing import Any, Dict, List

import requests

from coupon_detection_ai.coupon_parser import CouponParser


class CouponCollector:
    """Collect coupon data from ebook stores and parse to normalized records."""

    def __init__(self, timeout_sec: int = 10) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parser = CouponParser()
        self.endpoints = {
            "amazon": "https://example.com/api/coupons/amazon",
            "kobo": "https://example.com/api/coupons/kobo",
            "dmm": "https://example.com/api/coupons/dmm",
        }

    def collect(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for store, endpoint in self.endpoints.items():
            collected = self._fetch_or_fallback(store, endpoint)
            rows.extend(collected)
            self.logger.info("coupon rows collected store=%s count=%d", store, len(collected))
        return rows

    def _fetch_or_fallback(self, store: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()

            content_type = (resp.headers.get("Content-Type") or "").lower()
            if "application/json" in content_type:
                return self.parser.parse_json(store, resp.json())
            return self.parser.parse_html(store, resp.text)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback coupon data store=%s reason=%s", store, exc)
            return self._fallback(store)

    def _fallback(self, store: str) -> List[Dict[str, Any]]:
        base = {
            "store": store,
            "target_count": 80,
            "expires_at": "2026-03-31",
        }

        if store == "amazon":
            return [
                {**base, "coupon_type": "percentage", "discount": 50, "target": "manga"},
                {**base, "coupon_type": "yen", "discount": 200, "target": "all_books", "target_count": 30},
            ]
        if store == "kobo":
            return [
                {**base, "coupon_type": "yen", "discount": 300, "target": "all_books", "target_count": 55},
            ]
        return [
            {**base, "coupon_type": "percentage", "discount": 25, "target": "manga", "target_count": 120},
            {**base, "coupon_type": "yen", "discount": 500, "target": "manga", "target_count": 90},
        ]
