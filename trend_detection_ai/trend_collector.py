import logging
from typing import Any, Dict, List

import requests


class TrendCollector:
    """Collect trend signals from SNS, search, and news sources."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.endpoints = {
            "twitter_trend": "https://example.com/api/twitter/trends",
            "google_trend": "https://example.com/api/google/trends",
            "news_site": "https://example.com/api/news/trends",
            "anime_news_site": "https://example.com/api/anime/trends",
        }

    def collect(self) -> List[Dict[str, Any]]:
        all_items: List[Dict[str, Any]] = []
        for source, endpoint in self.endpoints.items():
            items = self._fetch_or_fallback(source, endpoint)
            all_items.extend(items)
            self.logger.info("trend source collected source=%s count=%d", source, len(items))
        return all_items

    def _fetch_or_fallback(self, source: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            response = requests.get(endpoint, timeout=self.timeout_sec)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                return [self._normalize_item(x, source) for x in payload]
            rows = payload.get("items", [])
            return [self._normalize_item(x, source) for x in rows]
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback trend data source=%s reason=%s", source, exc)
            return self._fallback(source)

    def _normalize_item(self, item: Dict[str, Any], source: str) -> Dict[str, Any]:
        return {
            "keyword": str(item.get("keyword", "")).strip(),
            "trend_score": float(item.get("trend_score", 0.0)),
            "source": item.get("source", source),
            "event": str(item.get("event", "")).strip(),
            "velocity": float(item.get("velocity", 0.0)),
        }

    @staticmethod
    def _fallback(source: str) -> List[Dict[str, Any]]:
        mapping = {
            "twitter_trend": [
                {"keyword": "葬送のフリーレン", "trend_score": 0.92, "source": source, "event": "SNS急上昇", "velocity": 0.35},
                {"keyword": "薬屋のひとりごと", "trend_score": 0.84, "source": source, "event": "SNS急上昇", "velocity": 0.22},
            ],
            "google_trend": [
                {"keyword": "俺だけレベルアップな件", "trend_score": 0.88, "source": source, "event": "検索トレンド急増", "velocity": 0.30},
                {"keyword": "怪獣8号", "trend_score": 0.81, "source": source, "event": "検索トレンド急増", "velocity": 0.18},
            ],
            "news_site": [
                {"keyword": "ダンダダン", "trend_score": 0.79, "source": source, "event": "ニュース掲載", "velocity": 0.14},
            ],
            "anime_news_site": [
                {"keyword": "チ。地球の運動について", "trend_score": 0.90, "source": source, "event": "アニメ化発表", "velocity": 0.32},
            ],
        }
        return mapping.get(source, [])
