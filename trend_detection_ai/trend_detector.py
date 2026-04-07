import json
import logging
from typing import Any, Dict, List

from trend_detection_ai.proposal_generator import TrendProposalGenerator
from trend_detection_ai.trend_analyzer import TrendAnalyzer
from trend_detection_ai.trend_collector import TrendCollector


class TrendDetectionAI:
    def __init__(self, threshold: float = 0.85) -> None:
        self.threshold = threshold
        self.collector = TrendCollector()
        self.analyzer = TrendAnalyzer()
        self.proposal_generator = TrendProposalGenerator()
        self.logger = logging.getLogger(self.__class__.__name__)

    def collect_trends(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def analyze_trends(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.analyzer.analyze(data)

    def detect_keywords(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        detected = [item for item in trends if float(item.get("urgency_score", 0.0)) >= self.threshold]
        self.logger.info("detected hot keywords count=%d threshold=%.2f", len(detected), self.threshold)
        return detected

    def generate_proposal(self, keyword: Dict[str, Any]) -> Dict[str, Any]:
        proposals = self.proposal_generator.generate([keyword])
        return proposals[0] if proposals else {}

    def run(self) -> List[Dict[str, Any]]:
        raw = self.collect_trends()
        analyzed = self.analyze_trends(raw)
        detected = self.detect_keywords(analyzed)
        proposals = self.proposal_generator.generate(detected)
        return proposals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    ai = TrendDetectionAI(threshold=0.85)
    proposals = ai.run()
    print(json.dumps(proposals, ensure_ascii=False, indent=2))
