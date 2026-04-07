import logging
from typing import Any, Dict, List


class MediaAdaptationAnalyzer:
    """Detect adaptation opportunities from collected media signals."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.valid_adaptation_types = {"アニメ化", "実写ドラマ化", "映画化", "舞台化", "ゲーム化"}
        self.valid_events = {"新規メディア化発表", "放送開始日発表", "キャスト発表", "PV公開"}

    def analyze(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        for _, signals in data.items():
            for signal in signals:
                adaptation_type = str(signal.get("adaptation_type", "")).strip()
                event_type = str(signal.get("event_type", "")).strip()
                if adaptation_type not in self.valid_adaptation_types:
                    continue
                if event_type not in self.valid_events:
                    continue

                reasons = self._build_reasons(signal)
                if not reasons:
                    continue

                opportunities.append(
                    {
                        "work_title": signal.get("work_title", "不明作品"),
                        "adaptation_type": adaptation_type,
                        "event_type": event_type,
                        "trend_score": int(signal.get("trend_score", 0)),
                        "popularity_score": int(signal.get("popularity_score", 0)),
                        "announced_at": signal.get("announced_at", ""),
                        "source": signal.get("source", ""),
                        "reasons": reasons,
                    }
                )

        self.logger.info("media adaptation opportunities detected=%d", len(opportunities))
        return opportunities

    def _build_reasons(self, signal: Dict[str, Any]) -> List[str]:
        reasons: List[str] = []
        event_type = str(signal.get("event_type", "")).strip()

        if event_type in {"新規メディア化発表", "放送開始日発表", "キャスト発表", "PV公開"}:
            reasons.append(event_type)

        trend_score = int(signal.get("trend_score", 0))
        popularity_score = int(signal.get("popularity_score", 0))
        if trend_score >= 80:
            reasons.append("SNSトレンド上昇")
        if popularity_score >= 75:
            reasons.append("人気作品判定")

        return reasons
