import logging
from typing import Any, Dict, List

from .collector import MediaSourceCollector
from .media_analyzer import MediaAdaptationAnalyzer
from .proposal_generator import MediaProposalGenerator


class MediaAdaptationBlock:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = MediaSourceCollector()
        self.analyzer_engine = MediaAdaptationAnalyzer()
        self.proposal_generator = MediaProposalGenerator()

    def analyze(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        try:
            return self.analyzer_engine.analyze(data)
        except Exception as exc:
            self.logger.exception("media analysis failed: %s", exc)
            return []

    def propose(self) -> List[Dict[str, Any]]:
        try:
            data = self.collector.collect()
            opportunities = self.analyze(data)
            return self.proposal_generator.generate(opportunities)
        except Exception as exc:
            self.logger.exception("media proposal generation failed: %s", exc)
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    block = MediaAdaptationBlock()
    proposals = block.propose()
    for proposal in proposals[:8]:
        print(proposal)
