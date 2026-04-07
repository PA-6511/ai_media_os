import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List

from article_generator.generator import ArticleGenerator
from intent_ai.article_type_mapper import ArticleTypeMapper
from intent_ai.intent_classifier import IntentClassifier


class SearchIntentAnalyzerAI:
    """End-to-end analyzer: keyword -> intent -> article type -> article generation."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.classifier = IntentClassifier()
        self.mapper = ArticleTypeMapper()
        self.generator = ArticleGenerator(model=model)

    def analyze_keyword(self, keyword: str) -> Dict[str, Any]:
        intent = self.classifier.classify(keyword)
        article_type = self.mapper.map(keyword=keyword, primary_intent=intent.primary_intent, scores=intent.scores)
        result = {
            "keyword": keyword,
            "search_intent": intent.primary_intent,
            "intent_scores": intent.scores,
            "matched_rules": intent.matched_rules,
            "article_type": article_type,
        }
        self.logger.info("keyword analyzed keyword=%s intent=%s article_type=%s", keyword, intent.primary_intent, article_type)
        return result

    def create_article_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        keyword = str(analysis.get("keyword", "")).strip()
        article_type = str(analysis.get("article_type", "work_article"))

        title = self._build_title(keyword=keyword, article_type=article_type)
        sections = self._build_sections(article_type=article_type)

        return {
            "title": title,
            "keyword": keyword,
            "article_type": article_type,
            "search_intent": analysis.get("search_intent", "information"),
            "sections": sections,
        }

    def generate_article_from_keyword(self, keyword: str) -> Dict[str, Any]:
        analysis = self.analyze_keyword(keyword)
        plan = self.create_article_plan(analysis)
        article_payload = self.generator.generate_article(plan)
        return {
            "analysis": analysis,
            "article_plan": plan,
            "article_payload": article_payload,
        }

    def analyze_batch(self, keywords: List[str]) -> List[Dict[str, Any]]:
        return [self.analyze_keyword(keyword) for keyword in keywords]

    def _build_title(self, keyword: str, article_type: str) -> str:
        if article_type == "volume_guide":
            return f"{keyword}を徹底解説: 何巻まで・読む順・最新情報"
        if article_type == "sale_article":
            return f"{keyword}の最新セール情報まとめ【最安・クーポン対応】"
        if article_type == "ranking_article":
            return f"{keyword}ランキング最新版【人気順】"
        if article_type == "genre_article":
            return f"{keyword}おすすめガイド【ジャンル別に厳選】"
        return f"{keyword}の評価・見どころ・おすすめポイント"

    def _build_sections(self, article_type: str) -> List[str]:
        base_sections = ["結論", "作品概要", "おすすめポイント", "よくある質問", "購入リンク"]

        if article_type == "volume_guide":
            return ["結論", "現在の巻数", "完結状況", "読む順番", "購入リンク"]
        if article_type == "sale_article":
            return ["結論", "現在の最安価格", "クーポン情報", "セール期限", "購入リンク"]
        if article_type == "ranking_article":
            return ["ランキング概要", "TOP作品", "比較ポイント", "読者タイプ別おすすめ", "購入リンク"]
        if article_type == "genre_article":
            return ["ジャンル概要", "おすすめ作品", "作品比較", "よくある質問", "購入リンク"]

        return base_sections


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    analyzer = SearchIntentAnalyzerAI(model="gpt-4o-mini")
    sample_keywords = [
        "呪術廻戦 何巻まで",
        "漫画 セール",
        "異世界漫画 おすすめ",
    ]

    analyses = analyzer.analyze_batch(sample_keywords)
    print(json.dumps(analyses, ensure_ascii=False, indent=2))
