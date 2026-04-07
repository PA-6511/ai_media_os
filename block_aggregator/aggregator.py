import json
import logging
from typing import Any, Dict, Iterable, List

from block_aggregator.proposal_collector import ProposalCollector
from block_aggregator.proposal_sorter import ProposalSorter


class BlockAIAggregator:
    def __init__(self, blocks: Iterable[Any]) -> None:
        self.blocks = list(blocks)
        self.collector = ProposalCollector(self.blocks)
        self.sorter = ProposalSorter()
        self.logger = logging.getLogger(self.__class__.__name__)

    def collect_proposals(self) -> List[Dict[str, Any]]:
        return self.collector.collect()

    def sort_proposals(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.sorter.sort(proposals)

    def get_article_opportunities(self, top_k: int = 10) -> List[Dict[str, Any]]:
        proposals = self.collect_proposals()
        sorted_proposals = self.sort_proposals(proposals)
        selected = sorted_proposals[:top_k]

        opportunities = [
            {
                "title": item.get("title", ""),
                "priority": float(item.get("priority", 0.0)),
                "source": item.get("source", ""),
                "reason": item.get("reason", ""),
            }
            for item in selected
        ]

        self.logger.info("article opportunities generated count=%d", len(opportunities))
        return opportunities


if __name__ == "__main__":
    from blocks.media_adaptation_block.block import MediaAdaptationBlock
    from blocks.new_release_block.block import NewReleaseBlock
    from blocks.ranking_monitor_block.block import RankingMonitorBlock
    from blocks.sale_detection_block.block import SaleDetectionBlock

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    blocks = [
        NewReleaseBlock(),
        SaleDetectionBlock(),
        RankingMonitorBlock(),
        MediaAdaptationBlock(),
    ]

    aggregator = BlockAIAggregator(blocks=blocks)
    result = aggregator.get_article_opportunities(top_k=10)
    print(json.dumps(result, ensure_ascii=False, indent=2))
