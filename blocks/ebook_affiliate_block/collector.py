import logging
from typing import Any, Dict, List

import requests


class EbookStoreCollector:
    """Collects ebook catalog signals from multiple stores."""

    def __init__(self, timeout_sec: int = 5) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.store_endpoints = {
            "amazon_kindle": "https://example.com/api/kindle/signals",
            "rakuten_kobo": "https://example.com/api/kobo/signals",
            "dmm_books": "https://example.com/api/dmm/signals",
        }

    def collect(self) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {}
        for store, endpoint in self.store_endpoints.items():
            data[store] = self._fetch_or_fallback(store, endpoint)
            self.logger.info("collected %d items from %s", len(data[store]), store)
        return data

    def _fetch_or_fallback(self, store: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(endpoint, timeout=self.timeout_sec)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                return payload
            return payload.get("items", [])
        except Exception as exc:  # pragma: no cover - fallback path is expected in starter kit
            self.logger.warning("fallback dataset used for %s: %s", store, exc)
            return self._sample_data(store)

    @staticmethod
    def _sample_data(store: str) -> List[Dict[str, Any]]:
        return [
            {
                "store": store,
                "title": "異世界職人メシ",
                "genre": "異世界",
                "is_new_release": True,
                "is_on_sale": False,
                "rank_before": 42,
                "rank_now": 10,
            },
            {
                "store": store,
                "title": "推しと学ぶWeb3漫画",
                "genre": "ビジネス",
                "is_new_release": False,
                "is_on_sale": True,
                "rank_before": 30,
                "rank_now": 28,
            },
            {
                "store": store,
                "title": "辺境ギルド運営録",
                "genre": "ファンタジー",
                "is_new_release": False,
                "is_on_sale": False,
                "rank_before": 120,
                "rank_now": 35,
            },
        ]
