import logging
from typing import Any, Dict, List

from .collector import NewReleaseCollector
from .proposal_generator import NewReleaseProposalGenerator
from .release_analyzer import NewReleaseAnalyzer


class NewReleaseBlock:
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.collector = NewReleaseCollector()
        self.analyzer_engine = NewReleaseAnalyzer()
        self.proposal_generator = NewReleaseProposalGenerator()

    def analyze(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        try:
            return self.analyzer_engine.analyze(data)
        except Exception as exc:
            self.logger.exception("new release analysis failed: %s", exc)
            return []

    def propose(self) -> List[Dict[str, Any]]:
        try:
            data = self.collector.collect()
            opportunities = self.analyze(data)
            return self.proposal_generator.generate(opportunities)
        except Exception as exc:
            self.logger.exception("new release proposal failed: %s", exc)
            return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    block = NewReleaseBlock()
    proposals = block.propose()
    for proposal in proposals[:6]:
        print(proposal)
