import json
import logging
from typing import Any, Dict, List


class TrendProposalGenerator:
    """Generate AI Council proposals from detected trend opportunities."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []

        for item in keywords:
            keyword = str(item.get("keyword", "")).strip()
            if not keyword:
                continue

            urgency = float(item.get("urgency_score", 0.0))
            event = str(item.get("event", "")).strip() or "SNS急上昇"
            reason = self._reason_label(event)

            proposal = {
                "source": "trend_detection_ai",
                "action": "generate_trend_article",
                "title": f"{keyword}が話題！人気の理由まとめ",
                "priority": round(min(0.99, max(0.0, urgency)), 2),
                "reason": reason,
                "metadata": {
                    "keyword": keyword,
                    "event": event,
                    "trend_score": item.get("trend_score", 0.0),
                    "urgency_score": item.get("urgency_score", 0.0),
                    "source": item.get("source", ""),
                },
            }
            proposals.append(proposal)
            self.logger.info("trend proposal=%s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    @staticmethod
    def _reason_label(event: str) -> str:
        if event == "SNS急上昇":
            return "SNSトレンド急上昇"
        if event == "検索トレンド急増":
            return "検索トレンド急増"
        if event == "ニュース掲載":
            return "ニュース掲載増加"
        if event == "アニメ化発表":
            return "アニメ化発表"
        return "トレンド急上昇"
