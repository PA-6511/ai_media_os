import json
import logging
from typing import Any, Dict, List


class RankingProposalGenerator:
    """Generate Council proposals from ranking events."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for event in events:
            reason = event.get("reason", "ランキング変動")
            proposal = {
                "source": "ranking_monitor_block",
                "action": "generate_ranking_article",
                "title": self._build_title(event),
                "priority": self._priority(event),
                "reason": reason,
                "metadata": {
                    "store": event.get("store", ""),
                    "event_type": event.get("event_type", ""),
                    "work_title": event.get("title", ""),
                    "genre": event.get("genre", ""),
                    "category": event.get("category", ""),
                    "current_rank": event.get("current_rank", 9999),
                    "previous_rank": event.get("previous_rank"),
                },
            }
            proposals.append(proposal)
            self.logger.info("ranking proposal=%s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    def _priority(self, event: Dict[str, Any]) -> float:
        base = 0.7
        event_type = event.get("event_type", "")
        current_rank = int(event.get("current_rank", 9999))
        previous_rank = event.get("previous_rank")

        if event_type == "surge":
            base += 0.16
        elif event_type == "top10":
            base += 0.14
        elif event_type == "new_entry":
            base += 0.1
        elif event_type == "genre_shift":
            base += 0.08

        if current_rank <= 3:
            base += 0.08
        elif current_rank <= 10:
            base += 0.05

        if isinstance(previous_rank, int):
            diff = previous_rank - current_rank
            if diff >= 20:
                base += 0.08
            elif diff >= 10:
                base += 0.04

        return round(min(base, 0.99), 2)

    @staticmethod
    def _build_title(event: Dict[str, Any]) -> str:
        event_type = event.get("event_type", "")
        genre = event.get("genre", "漫画")
        if event_type == "surge":
            return f"今売れている{genre}漫画ランキング"
        if event_type == "top10":
            return f"TOP10入りした注目{genre}作品まとめ"
        if event_type == "new_entry":
            return f"新規ランクイン{genre}電子書籍まとめ"
        if event_type == "genre_shift":
            return f"{genre}ジャンル急伸ランキング特集"
        return "今売れている漫画ランキング"
