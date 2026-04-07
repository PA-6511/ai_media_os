import logging
from typing import Any, Dict, List

from .collector import RankingCollector
from .proposal_generator import RankingProposalGenerator
from .ranking_analyzer import RankingAnalyzer


class RankingMonitorBlock:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = RankingCollector()
        self.analyzer_engine = RankingAnalyzer()
        self.proposal_generator = RankingProposalGenerator()

    def analyze(self, data: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        try:
            return self.analyzer_engine.analyze(data)
        except Exception as exc:
            self.logger.exception("analysis failed: %s", exc)
            return []

    def propose(self) -> List[Dict[str, Any]]:
        try:
            data = self.collector.collect()
            events = self.analyze(data)
            return self.proposal_generator.generate(events)
        except Exception as exc:
            self.logger.exception("proposal generation failed: %s", exc)
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    block = RankingMonitorBlock()
    proposals = block.propose()
    for proposal in proposals[:6]:
        print(proposal)
