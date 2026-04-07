import logging
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


class NewReleaseCollector:
    """Collect new release listings from ebook stores."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.store_urls = {
            "amazon_kindle": "https://example.com/kindle/new-releases",
            "rakuten_kobo": "https://example.com/kobo/new-releases",
            "dmm_books": "https://example.com/dmm/new-releases",
        }

    def collect(self) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {}
        for store, url in self.store_urls.items():
            data[store] = self._fetch_store_releases(store, url)
            self.logger.info("new releases collected store=%s count=%d", store, len(data[store]))
        return data

    def _fetch_store_releases(self, store: str, url: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return self._parse_html(store, response.text)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback new release data used store=%s reason=%s", store, exc)
            return self._fallback_data(store)

    def _parse_html(self, store: str, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".new-release-item")
        items: List[Dict[str, Any]] = []

        for card in cards:
            title_node = card.select_one(".title")
            author_node = card.select_one(".author")
            volume_node = card.select_one(".volume")
            date_node = card.select_one(".release-date")
            genre_node = card.select_one(".genre")

            items.append(
                {
                    "store": store,
                    "title": title_node.get_text(strip=True) if title_node else card.get("data-title", ""),
                    "author": author_node.get_text(strip=True) if author_node else card.get("data-author", ""),
                    "volume": self._to_int(volume_node.get_text(strip=True) if volume_node else card.get("data-volume", "0")),
                    "release_date": date_node.get_text(strip=True) if date_node else card.get("data-release-date", ""),
                    "genre": genre_node.get_text(strip=True) if genre_node else card.get("data-genre", "その他"),
                    "series_popularity": self._to_int(card.get("data-series-popularity", "0")),
                    "author_popularity": self._to_int(card.get("data-author-popularity", "0")),
                }
            )
        return items

    @staticmethod
    def _to_int(value: str) -> int:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _fallback_data(store: str) -> List[Dict[str, Any]]:
        return [
            {
                "store": store,
                "title": "異世界料理道",
                "author": "山田タロウ",
                "volume": 12,
                "release_date": "2026-03-07",
                "genre": "異世界",
                "series_popularity": 92,
                "author_popularity": 64,
            },
            {
                "store": store,
                "title": "恋するアルケミスト",
                "author": "佐藤ハナ",
                "volume": 1,
                "release_date": "2026-03-08",
                "genre": "恋愛",
                "series_popularity": 55,
                "author_popularity": 78,
            },
            {
                "store": store,
                "title": "AI編集部24時",
                "author": "高橋ケン",
                "volume": 3,
                "release_date": "2026-03-06",
                "genre": "ビジネス",
                "series_popularity": 40,
                "author_popularity": 49,
            },
        ]
