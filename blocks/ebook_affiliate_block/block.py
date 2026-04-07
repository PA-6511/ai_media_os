from typing import Any, Dict, List, Optional

from .analyzer import EbookOpportunityAnalyzer
from .collector import EbookStoreCollector
from .proposal_generator import ProposalGenerator


class EbookAffiliateBlock:
    def __init__(self) -> None:
        self.collector = EbookStoreCollector()
        self.analyzer_engine = EbookOpportunityAnalyzer()
        self.proposal_generator = ProposalGenerator()
        self._latest_data: Optional[Dict[str, List[Dict[str, Any]]]] = None

    def analyze(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        return self.analyzer_engine.analyze(data)

    def propose(self) -> List[Dict[str, Any]]:
        data = self.collector.collect()
        self._latest_data = data
        opportunities = self.analyze(data)
        return self.proposal_generator.generate(opportunities)


if __name__ == "__main__":
    block = EbookAffiliateBlock()
    proposals = block.propose()
    for proposal in proposals[:5]:
        print(proposal)
