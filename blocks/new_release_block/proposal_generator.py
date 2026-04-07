import json
import logging
from typing import Any, Dict, List


class NewReleaseProposalGenerator:
    """Generate AI Council proposals from new release opportunities."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for item in opportunities:
            reason = self._select_reason(item.get("reasons", []))
            title = self._build_article_title(item)
            priority = self._priority(item, reason)

            proposal = {
                "source": "new_release_block",
                "action": "generate_new_release_article",
                "title": title,
                "priority": priority,
                "reason": reason,
                "metadata": {
                    "store": item.get("store", ""),
                    "manga_title": item.get("title", ""),
                    "author": item.get("author", ""),
                    "volume": item.get("volume", 0),
                    "release_date": item.get("release_date", ""),
                    "genre": item.get("genre", ""),
                    "reasons": item.get("reasons", []),
                },
            }
            proposals.append(proposal)
            self.logger.info("new release proposal=%s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    @staticmethod
    def _select_reason(reasons: List[str]) -> str:
        for reason in ["人気シリーズ新刊", "人気作者の新作", "新刊漫画発売"]:
            if reason in reasons:
                return reason
        return reasons[0] if reasons else "新刊漫画発売"

    @staticmethod
    def _build_article_title(item: Dict[str, Any]) -> str:
        manga_title = str(item.get("title", "新刊漫画"))
        volume = int(item.get("volume", 0))
        if volume > 0:
            return f"{manga_title} 最新{volume}巻レビュー"
        return f"{manga_title} 最新巻レビュー"

    def _priority(self, item: Dict[str, Any], reason: str) -> float:
        score = 0.72
        series_popularity = int(item.get("series_popularity", 0))
        author_popularity = int(item.get("author_popularity", 0))
        volume = int(item.get("volume", 0))

        score += min(series_popularity / 100.0 * 0.18, 0.18)
        score += min(author_popularity / 100.0 * 0.08, 0.08)

        if volume >= 10:
            score += 0.05
        elif volume >= 5:
            score += 0.03

        if reason == "人気シリーズ新刊":
            score += 0.06
        elif reason == "人気作者の新作":
            score += 0.04

        return round(min(score, 0.99), 2)
