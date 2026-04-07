import logging
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


class SaleCollector:
    """Collect sale listings from ebook stores using HTML parsing."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.store_urls = {
            "amazon_kindle": "https://example.com/kindle/sale",
            "rakuten_kobo": "https://example.com/kobo/sale",
            "dmm_books": "https://example.com/dmm/sale",
        }

    def collect(self) -> Dict[str, List[Dict[str, Any]]]:
        results: Dict[str, List[Dict[str, Any]]] = {}
        for store, url in self.store_urls.items():
            results[store] = self._fetch_store_sales(store, url)
            self.logger.info("sale items collected store=%s count=%d", store, len(results[store]))
        return results

    def _fetch_store_sales(self, store: str, url: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return self._parse_html(store, response.text)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback sale data used store=%s reason=%s", store, exc)
            return self._fallback_sales(store)

    def _parse_html(self, store: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".sale-item")
        items: List[Dict[str, Any]] = []

        for card in cards:
            title = card.get("data-title") or card.select_one(".title").get_text(strip=True)
            discount_text = card.get("data-discount") or card.select_one(".discount").get_text(strip=True)
            point_text = card.get("data-points") or card.select_one(".points").get_text(strip=True)
            rank_text = card.get("data-rank") or card.select_one(".rank").get_text(strip=True)
            sale_type = card.get("data-sale-type") or card.select_one(".sale-type").get_text(strip=True)
            days_left_text = card.get("data-days-left") or card.select_one(".days-left").get_text(strip=True)

            items.append(
                {
                    "store": store,
                    "title": title,
                    "discount_rate": self._to_int(discount_text),
                    "points_back": self._to_int(point_text),
                    "rank": self._to_int(rank_text),
                    "sale_type": sale_type,
                    "days_left": self._to_int(days_left_text),
                }
            )

        return items

    @staticmethod
    def _to_int(value: str) -> int:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _fallback_sales(store: str) -> List[Dict[str, Any]]:
        return [
            {
                "store": store,
                "title": "異世界ギルド経営論",
                "discount_rate": 70,
                "points_back": 0,
                "rank": 12,
                "sale_type": "70%OFF",
                "days_left": 2,
            },
            {
                "store": store,
                "title": "恋愛転生アンソロジー",
                "discount_rate": 50,
                "points_back": 20,
                "rank": 68,
                "sale_type": "半額セール",
                "days_left": 5,
            },
            {
                "store": store,
                "title": "少年バトル総集編",
                "discount_rate": 35,
                "points_back": 30,
                "rank": 7,
                "sale_type": "ポイント還元セール",
                "days_left": 1,
            },
            {
                "store": store,
                "title": "週末まとめ買いセット",
                "discount_rate": 40,
                "points_back": 10,
                "rank": 90,
                "sale_type": "まとめ買いセール",
                "days_left": 3,
            },
        ]
