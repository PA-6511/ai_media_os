import logging
from typing import Any, Dict, List


class NewReleaseAnalyzer:
    """Analyze new-release records and detect article opportunities."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.series_popularity_threshold = 75
        self.author_popularity_threshold = 70

    def analyze(self, release_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        for store, items in release_data.items():
            for item in items:
                reasons = self._build_reasons(item)
                if not reasons:
                    continue

                opportunities.append(
                    {
                        "store": store,
                        "title": item.get("title", "不明タイトル"),
                        "author": item.get("author", "不明作者"),
                        "volume": int(item.get("volume", 0)),
                        "release_date": item.get("release_date", ""),
                        "genre": item.get("genre", "その他"),
                        "series_popularity": int(item.get("series_popularity", 0)),
                        "author_popularity": int(item.get("author_popularity", 0)),
                        "reasons": reasons,
                    }
                )

        self.logger.info("new release opportunities detected=%d", len(opportunities))
        return opportunities

    def _build_reasons(self, item: Dict[str, Any]) -> List[str]:
        reasons: List[str] = []
        volume = int(item.get("volume", 0))
        series_popularity = int(item.get("series_popularity", 0))
        author_popularity = int(item.get("author_popularity", 0))

        reasons.append("新刊漫画発売")

        if volume >= 2 and series_popularity >= self.series_popularity_threshold:
            reasons.append("人気シリーズ新刊")

        if author_popularity >= self.author_popularity_threshold:
            reasons.append("人気作者の新作")

        return reasons
