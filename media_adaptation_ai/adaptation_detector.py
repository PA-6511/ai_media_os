import json
import logging
from typing import Any, Dict, List, Optional

from media_adaptation_ai.news_collector import NewsCollector
from media_adaptation_ai.news_parser import NewsParser
from media_adaptation_ai.proposal_generator import ProposalGenerator


class MediaAdaptationAI:
    """Detect adaptation events from news and produce article proposals."""

    KEYWORDS = {
        "anime": ["アニメ化決定", "アニメ続編", "アニメ化"],
        "drama": ["実写化", "ドラマ化", "テレビドラマ化"],
        "movie": ["映画化", "劇場版"],
        "stage": ["舞台化"],
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = NewsCollector()
        self.parser = NewsParser()
        self.generator = ProposalGenerator()

    def collect_news(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def detect_adaptation(self, news_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed = self.parser.parse(news_data)
        events: List[Dict[str, Any]] = []

        for row in parsed:
            text = str(row.get("text", ""))
            detected = self._match_keyword(text)
            if not detected:
                continue

            adaptation_type, keyword = detected
            reason = self._reason_for(adaptation_type)

            events.append(
                {
                    "work_title": row.get("work_title", "不明作品"),
                    "adaptation_type": adaptation_type,
                    "keyword": keyword,
                    "reason": reason,
                    "source": row.get("source", ""),
                    "date": row.get("date", ""),
                    "title": row.get("title", ""),
                }
            )

        self.logger.info("adaptation events detected count=%d", len(events))
        return events

    def generate_proposal(self, adaptation_event: Dict[str, Any]) -> Dict[str, Any]:
        return self.generator.generate(adaptation_event)

    def run(self) -> List[Dict[str, Any]]:
        news = self.collect_news()
        events = self.detect_adaptation(news)
        proposals = [self.generate_proposal(ev) for ev in events]
        self.logger.info("media adaptation proposals generated count=%d", len(proposals))
        return proposals

    def _match_keyword(self, text: str) -> Optional[tuple[str, str]]:
        for adaptation_type, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return adaptation_type, keyword
        return None

    @staticmethod
    def _reason_for(adaptation_type: str) -> str:
        mapping = {
            "anime": "アニメ化情報を検出",
            "drama": "ドラマ化情報を検出",
            "movie": "映画化情報を検出",
            "stage": "舞台化情報を検出",
        }
        return mapping.get(adaptation_type, "メディア化情報を検出")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    ai = MediaAdaptationAI()
    proposals = ai.run()
    print(json.dumps(proposals, ensure_ascii=False, indent=2))
