import logging
from typing import Any, Dict, List


class TrendAnalyzer:
    """Analyze trend records and score urgency for content opportunity."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        analyzed: List[Dict[str, Any]] = []
        for item in data:
            keyword = str(item.get("keyword", "")).strip()
            if not keyword:
                continue

            base_score = float(item.get("trend_score", 0.0))
            velocity = float(item.get("velocity", 0.0))
            event = str(item.get("event", "")).strip()

            event_boost = self._event_boost(event)
            final_score = min(1.0, base_score + event_boost + min(0.15, velocity * 0.4))

            analyzed.append(
                {
                    **item,
                    "trend_score": round(base_score, 4),
                    "urgency_score": round(final_score, 4),
                }
            )

        analyzed.sort(key=lambda x: x["urgency_score"], reverse=True)
        self.logger.info("trend analyzed count=%d", len(analyzed))
        return analyzed

    @staticmethod
    def _event_boost(event: str) -> float:
        boosts = {
            "SNS急上昇": 0.06,
            "検索トレンド急増": 0.07,
            "ニュース掲載": 0.04,
            "アニメ化発表": 0.08,
        }
        return boosts.get(event, 0.0)
