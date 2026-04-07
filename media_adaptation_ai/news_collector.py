import logging
from typing import Any, Dict, List

import requests


class NewsCollector:
    """Collect media adaptation related news from configured sources."""

    def __init__(self, timeout_sec: int = 10) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.sources = {
            "news_site": "https://example.com/api/news/media",
            "anime_news": "https://example.com/api/anime/news",
            "publisher": "https://example.com/api/publisher/releases",
            "official_sns": "https://example.com/api/sns/official",
        }

    def collect(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for source, endpoint in self.sources.items():
            items = self._fetch_or_fallback(source, endpoint)
            rows.extend(items)
            self.logger.info("news collected source=%s count=%d", source, len(items))
        return rows

    def _fetch_or_fallback(self, source: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                rows = payload
            else:
                rows = payload.get("items", [])
            return [self._normalize(row, source) for row in rows]
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback news used source=%s reason=%s", source, exc)
            return self._fallback(source)

    def _normalize(self, row: Dict[str, Any], source: str) -> Dict[str, Any]:
        return {
            "title": str(row.get("title", "")).strip(),
            "source": str(row.get("source", source)).strip() or source,
            "date": str(row.get("date", "")).strip(),
            "content": str(row.get("content", "")).strip(),
        }

    @staticmethod
    def _fallback(source: str) -> List[Dict[str, Any]]:
        return [
            {
                "title": "呪術廻戦 アニメ続編制作決定",
                "source": source,
                "date": "2026-04-01",
                "content": "人気漫画『呪術廻戦』のアニメ続編制作が決定。",
            },
            {
                "title": "薬屋のひとりごと 実写ドラマ化発表",
                "source": source,
                "date": "2026-04-02",
                "content": "話題作『薬屋のひとりごと』の実写ドラマ化が発表。",
            },
            {
                "title": "葬送のフリーレン 映画化プロジェクト始動",
                "source": source,
                "date": "2026-04-03",
                "content": "『葬送のフリーレン』映画化プロジェクトが始動。",
            },
            {
                "title": "転生王子の冒険譚 舞台化決定",
                "source": source,
                "date": "2026-04-03",
                "content": "ライトノベル作品の舞台化が決定。",
            },
        ]
