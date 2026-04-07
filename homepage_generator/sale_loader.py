import logging
from typing import Any, Dict, List

import requests


class SaleLoader:
    """Load sale ranking, price drop, and new release snippets for homepage."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.endpoint = "https://example.com/api/home/sales"
        self.logger = logging.getLogger(self.__class__.__name__)

    def load(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            resp = requests.get(self.endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json()
            return {
                "sale_ranking": payload.get("sale_ranking", []),
                "today_price_drop": payload.get("today_price_drop", []),
                "new_releases": payload.get("new_releases", []),
            }
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback sale/new release data used reason=%s", exc)
            return self._fallback()

    def _fallback(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "sale_ranking": [
                {"rank": 1, "title": "呪術廻戦", "discount": 70, "url": "https://affiliate.example.com/jujutsu-sale"},
                {"rank": 2, "title": "葬送のフリーレン", "discount": 65, "url": "https://affiliate.example.com/frieren-sale"},
            ],
            "today_price_drop": [
                {"title": "薬屋のひとりごと", "discount": 50, "url": "https://affiliate.example.com/kusuriya-sale"},
                {"title": "怪獣8号", "discount": 40, "url": "https://affiliate.example.com/kaiju-sale"},
            ],
            "new_releases": [
                {"date": "2026-04-04", "title": "呪術廻戦 29巻", "url": "https://affiliate.example.com/jujutsu-29"},
                {"date": "2026-04-05", "title": "葬送のフリーレン 14巻", "url": "https://affiliate.example.com/frieren-14"},
            ],
        }
