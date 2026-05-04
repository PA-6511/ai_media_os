from pathlib import Path
from typing import Any, Dict, List, Optional

from core.governance import AuthorityRequest, evaluate_authority_request

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

    def handshake(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "block_id": "ebook_affiliate_block",
            "name": "Ebook Affiliate Block",
            "protocol": "phase2-handshake-v1",
            "mode": "dry_run",
        }

    def request_execution(
        self,
        *,
        actor: str,
        action: str,
        target: str,
        phase: str = "PHASE2",
        message: str = "",
        run_id: str | None = None,
        log_path: str | Path | None = None,
        kpi: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        req = AuthorityRequest(
            actor=actor,
            phase=phase,
            component="blocks",
            action=action,
            target=target,
            message=message,
            metadata={"kpi": kpi or {}},
        )
        if log_path:
            decision = evaluate_authority_request(
                req,
                run_id=run_id,
                log_path=Path(log_path),
            )
        else:
            decision = evaluate_authority_request(
                req,
                run_id=run_id,
            )

        return {
            "block_id": "ebook_affiliate_block",
            "decision": decision.decision.value,
            "policy_id": decision.policy_id,
            "reason": decision.reason,
            "run_id": decision.run_id,
        }

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
