import logging
from typing import Any, Dict, Iterable, List


class ProposalCollector:
    """Collect proposals from multiple Block AI instances."""

    def __init__(self, blocks: Iterable[Any]) -> None:
        self.blocks = list(blocks)
        self.logger = logging.getLogger(self.__class__.__name__)

    def collect(self) -> List[Dict[str, Any]]:
        proposals: List[Dict[str, Any]] = []
        for block in self.blocks:
            block_name = block.__class__.__name__
            try:
                block_proposals = block.propose()
                if not isinstance(block_proposals, list):
                    self.logger.warning("block returned non-list proposals block=%s", block_name)
                    continue
                self.logger.info("collected proposals block=%s count=%d", block_name, len(block_proposals))
                for proposal in block_proposals:
                    normalized = self._normalize(proposal)
                    if normalized is not None:
                        proposals.append(normalized)
            except Exception as exc:
                self.logger.exception("failed to collect proposals block=%s error=%s", block_name, exc)

        self.logger.info("total collected proposals=%d", len(proposals))
        return proposals

    def _normalize(self, proposal: Dict[str, Any]) -> Dict[str, Any] | None:
        if not isinstance(proposal, dict):
            return None

        title = str(proposal.get("title", "")).strip()
        if not title:
            return None

        raw_priority = proposal.get("priority", 0.0)
        try:
            priority = float(raw_priority)
        except (TypeError, ValueError):
            priority = 0.0

        normalized = {
            "source": proposal.get("source", "unknown_block"),
            "action": proposal.get("action", "generate_article"),
            "title": title,
            "priority": max(0.0, min(1.0, priority)),
            "reason": proposal.get("reason", "no_reason"),
            "metadata": proposal.get("metadata", {}),
        }
        return normalized
