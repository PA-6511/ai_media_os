import logging
from typing import Dict


class ArticleTypeMapper:
    """Maps search intent + keyword hints into one of the target article types."""

    VALID_TYPES = {
        "volume_guide",
        "sale_article",
        "ranking_article",
        "genre_article",
        "work_article",
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def map(self, keyword: str, primary_intent: str, scores: Dict[str, int]) -> str:
        normalized = (keyword or "").strip().lower()

        # Explicit keyword cues first for deterministic behavior.
        if any(token in normalized for token in ["何巻", "どこまで", "読む順", "完結", "最新刊", "発売日"]):
            return self._decide("volume_guide", keyword)

        if any(token in normalized for token in ["セール", "値下げ", "クーポン", "最安", "off", "%off", "deal"]):
            return self._decide("sale_article", keyword)

        if any(token in normalized for token in ["ランキング", "順位", "top", "best"]):
            return self._decide("ranking_article", keyword)

        if any(token in normalized for token in ["ジャンル", "異世界", "恋愛", "バトル", "ミステリー", "genre"]):
            return self._decide("genre_article", keyword)

        # Intent-based fallback.
        if primary_intent == "purchase":
            return self._decide("sale_article", keyword)
        if primary_intent == "comparison":
            if scores.get("comparison", 0) >= 3:
                return self._decide("ranking_article", keyword)
            return self._decide("work_article", keyword)
        if primary_intent == "review":
            return self._decide("work_article", keyword)

        return self._decide("work_article", keyword)

    def _decide(self, article_type: str, keyword: str) -> str:
        if article_type not in self.VALID_TYPES:
            raise ValueError(f"invalid article_type: {article_type}")
        self.logger.info("article_type mapped keyword=%s article_type=%s", keyword, article_type)
        return article_type
