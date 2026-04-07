import json
import logging
from typing import Any, Dict, List


class MediaProposalGenerator:
    """Generate AI Council proposals for media adaptation articles."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for op in opportunities:
            reason = self._primary_reason(op.get("reasons", []))
            work_title = str(op.get("work_title", "注目作品"))
            adaptation_type = str(op.get("adaptation_type", "メディア化"))

            proposal = {
                "source": "media_adaptation_block",
                "action": "generate_media_article",
                "title": self._build_title(work_title, adaptation_type),
                "priority": self._priority(op, reason),
                "reason": reason,
                "metadata": {
                    "work_title": work_title,
                    "adaptation_type": adaptation_type,
                    "event_type": op.get("event_type", ""),
                    "trend_score": op.get("trend_score", 0),
                    "popularity_score": op.get("popularity_score", 0),
                    "announced_at": op.get("announced_at", ""),
                    "source": op.get("source", ""),
                    "reasons": op.get("reasons", []),
                },
            }
            proposals.append(proposal)
            self.logger.info("media proposal=%s", json.dumps(proposal, ensure_ascii=False))

        unique = {json.dumps(p, ensure_ascii=False, sort_keys=True): p for p in proposals}
        return list(unique.values())

    @staticmethod
    def _build_title(work_title: str, adaptation_type: str) -> str:
        if adaptation_type == "アニメ化":
            return f"{work_title}アニメ化決定！原作漫画まとめ"
        if adaptation_type == "実写ドラマ化":
            return f"{work_title}ドラマ化決定！原作電子書籍まとめ"
        if adaptation_type == "映画化":
            return f"{work_title}映画化決定！原作漫画まとめ"
        if adaptation_type == "舞台化":
            return f"{work_title}舞台化決定！原作漫画まとめ"
        if adaptation_type == "ゲーム化":
            return f"{work_title}ゲーム化決定！原作漫画まとめ"
        return f"{work_title}メディア化決定！原作まとめ"

    @staticmethod
    def _primary_reason(reasons: List[str]) -> str:
        priority_order = ["新規メディア化発表", "放送開始日発表", "キャスト発表", "PV公開", "SNSトレンド上昇", "人気作品判定"]
        for reason in priority_order:
            if reason in reasons:
                return reason
        return reasons[0] if reasons else "アニメ化発表"

    def _priority(self, op: Dict[str, Any], reason: str) -> float:
        score = 0.8
        trend_score = int(op.get("trend_score", 0))
        popularity_score = int(op.get("popularity_score", 0))

        score += min(trend_score / 100.0 * 0.1, 0.1)
        score += min(popularity_score / 100.0 * 0.07, 0.07)

        if reason == "新規メディア化発表":
            score += 0.06
        elif reason == "放送開始日発表":
            score += 0.05
        elif reason == "キャスト発表":
            score += 0.04
        elif reason == "PV公開":
            score += 0.04

        return round(min(score, 0.99), 2)
