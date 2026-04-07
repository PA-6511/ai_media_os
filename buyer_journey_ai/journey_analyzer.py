import json
import logging
from typing import Any, Dict

from buyer_journey_ai.cta_optimizer import CTAOptimizer
from buyer_journey_ai.next_article_selector import NextArticleSelector
from buyer_journey_ai.stage_classifier import StageClassifier
from intent_ai.intent_analyzer import SearchIntentAnalyzerAI


class BuyerJourneyAI:
    """Buyer journey optimizer for stage classification, next-article ranking, and CTA only."""

    def __init__(self, use_intent_analyzer: bool = True) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stage_classifier = StageClassifier()
        self.selector = NextArticleSelector()
        self.cta_optimizer = CTAOptimizer()
        self.intent_analyzer = SearchIntentAnalyzerAI() if use_intent_analyzer else None

    def classify_stage(self, keyword: str, article_type: str) -> str:
        normalized_type = article_type
        if not normalized_type and self.intent_analyzer:
            analyzed = self.intent_analyzer.analyze_keyword(keyword)
            normalized_type = str(analyzed.get("article_type", "work_article"))
        return self.stage_classifier.classify_stage(keyword=keyword, article_type=normalized_type or "work_article")

    def recommend_next_articles(self, current_article: str, stage: str, keyword: str = "") -> Dict[str, Any]:
        next_articles = self.selector.recommend_next_articles(
            keyword=keyword,
            current_article=current_article,
            stage=stage,
        )
        return {
            "next_articles": next_articles,
            "article_order": [
                {"position": idx + 1, "article": title}
                for idx, title in enumerate(next_articles)
            ],
        }

    def optimize_cta(self, stage: str, current_article: str, article_type: str = "work_article") -> Dict[str, str]:
        return self.cta_optimizer.optimize(stage=stage, article_type=article_type, keyword=current_article)

    def generate_journey_plan(self, keyword: str, article_type: str, current_article: str) -> Dict[str, Any]:
        stage_result = self.stage_classifier.classify(keyword=keyword, article_type=article_type)
        recommended = self.recommend_next_articles(
            current_article=current_article,
            stage=stage_result.stage,
            keyword=keyword,
        )
        cta = self.optimize_cta(
            stage=stage_result.stage,
            current_article=current_article,
            article_type=article_type,
        )

        result = {
            "keyword": keyword,
            "current_article": current_article,
            "article_type": article_type,
            "journey_stage": stage_result.stage,
            "stage_scores": stage_result.scores,
            "matched_rules": stage_result.matched_rules,
            "next_articles": recommended["next_articles"],
            "article_order": recommended["article_order"],
            "cta_text": cta["cta_text"],
            "cta_subtext": cta["cta_subtext"],
            "cta_placement": cta["cta_placement"],
            "button_style": cta["button_style"],
            "journey_flow": self._build_journey_flow(stage=stage_result.stage),
        }
        self.logger.info(
            "buyer journey plan generated keyword=%s article_type=%s stage=%s next_articles=%d",
            keyword,
            article_type,
            stage_result.stage,
            len(result["next_articles"]),
        )
        return result

    def to_article_generator_context(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Returns structured context so Article Generator can embed links and CTA blocks."""
        return {
            "journey": {
                "stage": plan.get("journey_stage"),
                "next_articles": plan.get("next_articles", []),
                "article_order": plan.get("article_order", []),
                "cta": {
                    "text": plan.get("cta_text", ""),
                    "subtext": plan.get("cta_subtext", ""),
                    "placement": plan.get("cta_placement", "after_summary"),
                    "style": plan.get("button_style", "primary-large"),
                },
                "flow": plan.get("journey_flow", {}),
            }
        }

    def _build_journey_flow(self, stage: str) -> Dict[str, str]:
        if stage == "information_gathering":
            return {
                "current": "information_gathering",
                "next": "work_article",
                "then": "purchase_ready",
                "final": "purchase",
            }
        if stage == "comparison":
            return {
                "current": "comparison",
                "next": "purchase_ready",
                "then": "purchase",
                "final": "conversion",
            }
        return {
            "current": "purchase_ready",
            "next": "purchase",
            "then": "upsell",
            "final": "purchase",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    analyzer = BuyerJourneyAI(use_intent_analyzer=True)
    sample = analyzer.generate_journey_plan(
        keyword="呪術廻戦 何巻まで",
        article_type="volume_guide",
        current_article="呪術廻戦 何巻まで",
    )
    print(json.dumps(sample, ensure_ascii=False, indent=2))
