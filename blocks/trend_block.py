from typing import Dict, List


class TrendBlock:
    def run(self) -> List[Dict]:
        return [
            {
                "source": "trend_block",
                "action": "generate_article",
                "target": "異世界漫画ランキング",
                "priority": 0.8,
            }
        ]
