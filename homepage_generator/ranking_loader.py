import logging
from typing import Any, Dict, List

import requests


class RankingLoader:
    """Load ranking and discovery content for homepage sections."""

    def __init__(self, timeout_sec: int = 8) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.endpoint = "https://example.com/api/home/rankings"

    def load(self) -> Dict[str, Any]:
        try:
            resp = requests.get(self.endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json()
            return self._normalize(payload)
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback ranking data used reason=%s", exc)
            return self._fallback()

    def _normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "popular_manga": payload.get("popular_manga", []),
            "completed_manga": payload.get("completed_manga", []),
            "genre_ranking": payload.get("genre_ranking", []),
            "keyword_tags": payload.get("keyword_tags", []),
            "hero_banner": payload.get("hero_banner", {"title": "今週の注目セール", "subtitle": "人気作品をチェック"}),
        }

    def _fallback(self) -> Dict[str, Any]:
        return {
            "hero_banner": {
                "title": "今週の電子書籍ビッグセール",
                "subtitle": "値下げ・新刊・話題作をまとめてチェック",
            },
            "popular_manga": [
                {"rank": 1, "title": "呪術廻戦", "url": "https://affiliate.example.com/manga/jujutsu"},
                {"rank": 2, "title": "葬送のフリーレン", "url": "https://affiliate.example.com/manga/frieren"},
                {"rank": 3, "title": "怪獣8号", "url": "https://affiliate.example.com/manga/kaiju8"},
            ],
            "completed_manga": [
                {"title": "鋼の錬金術師", "url": "https://affiliate.example.com/manga/hagaren"},
                {"title": "鬼滅の刃", "url": "https://affiliate.example.com/manga/kimetsu"},
            ],
            "genre_ranking": [
                {"genre": "異世界", "top_title": "無職転生", "url": "https://affiliate.example.com/genre/isekai"},
                {"genre": "恋愛", "top_title": "わたしの幸せな結婚", "url": "https://affiliate.example.com/genre/romance"},
                {"genre": "バトル", "top_title": "ワールドトリガー", "url": "https://affiliate.example.com/genre/battle"},
            ],
            "keyword_tags": ["新刊", "半額", "異世界", "完結", "ランキング", "試し読み"],
        }
