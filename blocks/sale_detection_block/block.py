from typing import Any, Dict, List

from .collector import SaleCollector
from .proposal_generator import SaleProposalGenerator
from .sale_analyzer import SaleAnalyzer


class SaleDetectionBlock:
    def __init__(self) -> None:
        self.collector = SaleCollector()
        self.analyzer_engine = SaleAnalyzer()
        self.proposal_generator = SaleProposalGenerator()

    def analyze(self, data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        return self.analyzer_engine.analyze(data)

    def propose(self) -> List[Dict[str, Any]]:
        sales_data = self.collector.collect()
        opportunities = self.analyze(sales_data)
        return self.proposal_generator.generate(opportunities)


if __name__ == "__main__":
    block = SaleDetectionBlock()
    proposals = block.propose()
    for proposal in proposals[:5]:
        print(proposal)
