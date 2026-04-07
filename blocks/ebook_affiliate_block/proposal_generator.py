import json
import logging
from typing import Any, Dict, List


class ProposalGenerator:
    """Builds Council proposals from detected opportunities."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.priority_map = {
            "new_release": 0.72,
            "sale": 0.81,
            "ranking_surge": 0.87,
            "popular_genre": 0.68,
        }

    def generate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for op in opportunities:
            genre = op.get("genre", "人気")
            reason = op.get("reason", "注目トピック")
            title = self._build_title(op)
            priority = self.priority_map.get(op.get("type", "popular_genre"), 0.6)

            proposal = {
                "source": "ebook_affiliate_block",
                "action": "generate_article",
                "title": title,
                "target": title,
                "priority": round(priority, 2),
                "reason": reason,
                "metadata": {
                    "genre": genre,
                    "work_title": op.get("title", ""),
                    "opportunity_type": op.get("type", ""),
                },
            }
            proposals.append(proposal)
            self.logger.info("proposal generated: %s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    @staticmethod
    def _build_title(opportunity: Dict[str, Any]) -> str:
        genre = opportunity.get("genre", "漫画")
        if opportunity.get("type") == "sale":
            return f"{genre}漫画セールおすすめ特集"
        if opportunity.get("type") == "new_release":
            return f"今週の新刊{genre}漫画まとめ"
        if opportunity.get("type") == "ranking_surge":
            return f"おすすめ{genre}漫画ランキング急上昇まとめ"
        return f"人気{genre}漫画ランキング"
