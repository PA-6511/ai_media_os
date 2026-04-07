import logging
from typing import Any, Dict, List, Set


class RankingAnalyzer:
    """Detect ranking movement events for article opportunities."""

    def __init__(self, surge_threshold: int = 10) -> None:
        self.surge_threshold = surge_threshold
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze(self, snapshots: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        events: List[Dict[str, Any]] = []
        for store, snapshot in snapshots.items():
            current = snapshot.get("current", [])
            previous = snapshot.get("previous", [])
            current_map = {item["title"]: item for item in current}
            previous_map = {item["title"]: item for item in previous}

            # Detect title-based movement events.
            for title, curr in current_map.items():
                prev = previous_map.get(title)
                if prev is None:
                    events.append(
                        {
                            "store": store,
                            "event_type": "new_entry",
                            "title": title,
                            "genre": curr.get("genre", "その他"),
                            "category": curr.get("category", "電子書籍"),
                            "current_rank": int(curr.get("rank", 9999)),
                            "previous_rank": None,
                            "reason": "新規ランクイン",
                        }
                    )
                    continue

                prev_rank = int(prev.get("rank", 9999))
                curr_rank = int(curr.get("rank", 9999))
                diff = prev_rank - curr_rank

                if diff >= self.surge_threshold:
                    events.append(
                        {
                            "store": store,
                            "event_type": "surge",
                            "title": title,
                            "genre": curr.get("genre", "その他"),
                            "category": curr.get("category", "電子書籍"),
                            "current_rank": curr_rank,
                            "previous_rank": prev_rank,
                            "reason": "ランキング急上昇",
                        }
                    )

                if curr_rank <= 10 and prev_rank > 10:
                    reason = "新刊がTOP10入り" if bool(curr.get("is_new_release", False)) else "TOP10入り"
                    events.append(
                        {
                            "store": store,
                            "event_type": "top10",
                            "title": title,
                            "genre": curr.get("genre", "その他"),
                            "category": curr.get("category", "電子書籍"),
                            "current_rank": curr_rank,
                            "previous_rank": prev_rank,
                            "reason": reason,
                        }
                    )

            # Detect genre share changes between snapshots.
            events.extend(self._detect_genre_shift(store, current, previous))

        self.logger.info("ranking events detected=%d", len(events))
        return events

    def _detect_genre_shift(
        self,
        store: str,
        current: List[Dict[str, Any]],
        previous: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        prev_top10_genres: Set[str] = {str(i.get("genre", "その他")) for i in previous if int(i.get("rank", 9999)) <= 10}
        curr_top10_genres: Set[str] = {str(i.get("genre", "その他")) for i in current if int(i.get("rank", 9999)) <= 10}

        entered = sorted(curr_top10_genres - prev_top10_genres)
        events: List[Dict[str, Any]] = []
        for genre in entered:
            events.append(
                {
                    "store": store,
                    "event_type": "genre_shift",
                    "title": f"{genre}ジャンル",
                    "genre": genre,
                    "category": "ジャンル別ランキング",
                    "current_rank": 10,
                    "previous_rank": None,
                    "reason": "特定ジャンルのランキング変動",
                }
            )
        return events
