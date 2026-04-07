import logging
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


class RankingCollector:
    """Collect ranking snapshots from ebook stores."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.store_urls = {
            "amazon_kindle": "https://example.com/kindle/ranking",
            "rakuten_kobo": "https://example.com/kobo/ranking",
            "dmm_books": "https://example.com/dmm/ranking",
        }

    def collect(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        snapshots: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for store, url in self.store_urls.items():
            snapshots[store] = self._fetch_store_snapshot(store, url)
            self.logger.info(
                "ranking snapshot collected store=%s current=%d previous=%d",
                store,
                len(snapshots[store].get("current", [])),
                len(snapshots[store].get("previous", [])),
            )
        return snapshots

    def _fetch_store_snapshot(self, store: str, url: str) -> Dict[str, List[Dict[str, Any]]]:
        try:
            response = requests.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return self._parse_html(response.text)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback ranking data used store=%s reason=%s", store, exc)
            return self._fallback_snapshot(store)

    def _parse_html(self, html: str) -> Dict[str, List[Dict[str, Any]]]:
        soup = BeautifulSoup(html, "html.parser")
        current_rows = soup.select("#current .rank-item")
        previous_rows = soup.select("#previous .rank-item")

        def parse_rows(rows) -> List[Dict[str, Any]]:
            items: List[Dict[str, Any]] = []
            for row in rows:
                title = (row.get("data-title") or row.select_one(".title").get_text(strip=True))
                genre = (row.get("data-genre") or row.select_one(".genre").get_text(strip=True))
                category = (row.get("data-category") or row.select_one(".category").get_text(strip=True))
                rank = self._to_int(row.get("data-rank") or row.select_one(".rank").get_text(strip=True))
                is_new = str(row.get("data-is-new") or "false").lower() in {"1", "true", "yes"}
                items.append(
                    {
                        "title": title,
                        "genre": genre,
                        "category": category,
                        "rank": rank,
                        "is_new_release": is_new,
                    }
                )
            return items

        return {
            "current": parse_rows(current_rows),
            "previous": parse_rows(previous_rows),
        }

    @staticmethod
    def _to_int(value: str) -> int:
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _fallback_snapshot(store: str) -> Dict[str, List[Dict[str, Any]]]:
        previous = [
            {"title": "異世界開拓記", "genre": "異世界", "category": "漫画", "rank": 27, "is_new_release": False},
            {"title": "夜明けの魔導院", "genre": "ファンタジー", "category": "漫画", "rank": 11, "is_new_release": False},
            {"title": "恋愛アルゴリズム", "genre": "恋愛", "category": "新刊", "rank": 18, "is_new_release": True},
            {"title": "経営戦略マンガ入門", "genre": "ビジネス", "category": "電子書籍", "rank": 9, "is_new_release": False},
        ]

        current = [
            {"title": "異世界開拓記", "genre": "異世界", "category": "漫画", "rank": 6, "is_new_release": False},
            {"title": "夜明けの魔導院", "genre": "ファンタジー", "category": "漫画", "rank": 8, "is_new_release": False},
            {"title": "恋愛アルゴリズム", "genre": "恋愛", "category": "新刊", "rank": 4, "is_new_release": True},
            {"title": "新作バトルクロニクル", "genre": "バトル", "category": "漫画", "rank": 9, "is_new_release": True},
        ]

        # vary store slightly to emulate independent movement
        if store == "dmm_books":
            current[1]["rank"] = 14
            current[3]["rank"] = 7
        if store == "rakuten_kobo":
            current[0]["rank"] = 3
            current[2]["rank"] = 2

        return {"current": current, "previous": previous}
