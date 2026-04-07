import logging
import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class IntentResult:
    keyword: str
    primary_intent: str
    scores: Dict[str, int]
    matched_rules: List[str]


class IntentClassifier:
    """Classifies search intent using transparent rule-based scoring."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rules: Dict[str, List[str]] = {
            "purchase": [
                "セール",
                "割引",
                "値下げ",
                "最安",
                "クーポン",
                "安い",
                "買う",
                "まとめ買い",
                "off",
                "%off",
            ],
            "comparison": [
                "比較",
                "違い",
                "どっち",
                "おすすめ",
                "ランキング",
                "順位",
                "人気",
                "ベスト",
                "top",
            ],
            "information": [
                "何巻",
                "どこまで",
                "完結",
                "読む順",
                "最新刊",
                "発売日",
                "あらすじ",
                "ネタバレ",
                "作者",
            ],
            "review": [
                "評価",
                "レビュー",
                "感想",
                "面白い",
                "つまらない",
                "口コミ",
            ],
        }

    def classify(self, keyword: str) -> IntentResult:
        normalized = self._normalize(keyword)
        if not normalized:
            return IntentResult(keyword=keyword, primary_intent="information", scores=self._zero_scores(), matched_rules=[])

        scores = self._zero_scores()
        matched_rules: List[str] = []

        for intent, patterns in self.rules.items():
            for pattern in patterns:
                if pattern in normalized:
                    scores[intent] += 2
                    matched_rules.append(f"{intent}:{pattern}")

        # Add lightweight lexical hints for better precision.
        if re.search(r"\\b(top|rank|ranking)\\b", normalized):
            scores["comparison"] += 2
            matched_rules.append("comparison:ranking-token")

        if re.search(r"\\b(when|latest|volume)\\b", normalized):
            scores["information"] += 1
            matched_rules.append("information:en-token")

        if re.search(r"\\b(sale|coupon|deal)\\b", normalized):
            scores["purchase"] += 2
            matched_rules.append("purchase:en-token")

        primary_intent = self._choose_primary_intent(scores)
        self.logger.info("intent classified keyword=%s primary_intent=%s scores=%s", keyword, primary_intent, scores)
        return IntentResult(keyword=keyword, primary_intent=primary_intent, scores=scores, matched_rules=matched_rules)

    def _normalize(self, keyword: str) -> str:
        return (keyword or "").strip().lower()

    def _zero_scores(self) -> Dict[str, int]:
        return {
            "purchase": 0,
            "comparison": 0,
            "information": 0,
            "review": 0,
        }

    def _choose_primary_intent(self, scores: Dict[str, int]) -> str:
        # Priority tie-breaker reflects affiliate media conversion behavior.
        priority = ["purchase", "comparison", "review", "information"]
        best_intent = "information"
        best_score = -1
        for intent in priority:
            score = scores.get(intent, 0)
            if score > best_score:
                best_intent = intent
                best_score = score

        if best_score <= 0:
            return "information"
        return best_intent
