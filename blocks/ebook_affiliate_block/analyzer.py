import logging
from typing import Any, Dict, List


class EbookOpportunityAnalyzer:
    """Analyzes ebook signals and detects article opportunities."""

    def __init__(self, surge_threshold: int = 20) -> None:
        self.surge_threshold = surge_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
        self.popular_genres = {"異世界", "恋愛", "ファンタジー", "バトル"}

    def analyze(self, store_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        for _, items in store_data.items():
            for item in items:
                opportunities.extend(self._detect(item))
        self.logger.info("detected opportunities=%d", len(opportunities))
        return opportunities

    def _detect(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        found: List[Dict[str, Any]] = []
        title = item.get("title", "不明タイトル")
        genre = item.get("genre", "その他")
        rank_before = int(item.get("rank_before", 9999))
        rank_now = int(item.get("rank_now", 9999))
        rank_gain = rank_before - rank_now

        if bool(item.get("is_new_release", False)):
            found.append({"type": "new_release", "title": title, "genre": genre, "reason": "新刊漫画"})

        if bool(item.get("is_on_sale", False)):
            found.append({"type": "sale", "title": title, "genre": genre, "reason": "セール対象作品"})

        if rank_gain >= self.surge_threshold:
            found.append({"type": "ranking_surge", "title": title, "genre": genre, "reason": "ランキング急上昇"})

        if genre in self.popular_genres:
            found.append({"type": "popular_genre", "title": title, "genre": genre, "reason": "人気ジャンル"})

        return found
