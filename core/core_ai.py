from typing import Dict, List, Optional


class CoreAI:
    def evaluate(self, proposals: List[Dict]) -> Optional[Dict]:
        if not proposals:
            return None
        return max(proposals, key=lambda p: float(p.get("priority", 0.0)))
