import logging
from typing import Any, Dict, List

import requests


class SaleCollector:
    """Collect sale items from ebook stores and normalize records."""

    def __init__(self, timeout_sec: int = 10) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sources = {
            "amazon": "https://example.com/api/sales/amazon",
            "rakuten": "https://example.com/api/sales/rakuten",
            "dmm": "https://example.com/api/sales/dmm",
        }

    def collect(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for store, endpoint in self.sources.items():
            collected = self._fetch_or_fallback(store, endpoint)
            rows.extend(collected)
            self.logger.info("sale rows collected store=%s count=%d", store, len(collected))
        return rows

    def _fetch_or_fallback(self, store: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                return [self._normalize(x, store) for x in payload]
            items = payload.get("items", [])
            return [self._normalize(x, store) for x in items]
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback sale data used store=%s reason=%s", store, exc)
            return self._fallback(store)

    def _normalize(self, row: Dict[str, Any], store: str) -> Dict[str, Any]:
        return {
            "title": str(row.get("title", "")).strip(),
            "discount": int(float(row.get("discount", 0))),
            "store": str(row.get("store", store)).strip() or store,
            "url": str(row.get("url", "")).strip(),
        }

    @staticmethod
    def _fallback(store: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "呪術廻戦",
                "discount": 70,
                "store": store,
                "url": f"https://affiliate.example.com/{store}/jujutsu",
            },
            {
                "title": "葬送のフリーレン",
                "discount": 60,
                "store": store,
                "url": f"https://affiliate.example.com/{store}/frieren",
            },
            {
                "title": "薬屋のひとりごと",
                "discount": 50,
                "store": store,
                "url": f"https://affiliate.example.com/{store}/kusuriya",
            },
            {
                "title": "怪獣8号",
                "discount": 40,
                "store": store,
                "url": f"https://affiliate.example.com/{store}/kaiju8",
            },
        ]
