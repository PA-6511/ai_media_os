from typing import Any, Dict, List


class ProposalSorter:
    """Sort and deduplicate proposals by priority."""

    def sort(self, proposals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Keep highest-priority proposal for the same title.
        by_title: Dict[str, Dict[str, Any]] = {}
        for proposal in proposals:
            title = str(proposal.get("title", "")).strip()
            if not title:
                continue
            current = by_title.get(title)
            if current is None or float(proposal.get("priority", 0.0)) > float(current.get("priority", 0.0)):
                by_title[title] = proposal

        return sorted(by_title.values(), key=lambda x: float(x.get("priority", 0.0)), reverse=True)
