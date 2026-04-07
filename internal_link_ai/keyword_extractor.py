import re
from typing import Dict, List


class KeywordExtractor:
    """Extract SEO-relevant keywords from article title/content."""

    STOPWORDS = {
        "最新",
        "レビュー",
        "まとめ",
        "記事",
        "紹介",
        "ランキング",
        "セール",
        "作品",
        "漫画",
        "電子書籍",
        "ライトノベル",
        "おすすめ",
        "情報",
        "特集",
        "版",
        "巻",
    }

    def extract(self, article: Dict[str, str], max_keywords: int = 5) -> List[str]:
        title = str(article.get("title", ""))
        content = str(article.get("content", ""))

        # Prefer title terms, then enrich with content terms.
        tokens = self._tokenize(title) + self._tokenize(content)

        scored: Dict[str, int] = {}
        for token in tokens:
            if len(token) <= 1:
                continue
            if token in self.STOPWORDS:
                continue
            scored[token] = scored.get(token, 0) + 1

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)
        return [token for token, _ in ranked[:max_keywords]]

    def _tokenize(self, text: str) -> List[str]:
        # Keep Japanese words, alnum words, and Katakana ranges.
        words = re.findall(r"[一-龠ぁ-んァ-ヴーA-Za-z0-9]{2,}", text)
        return words
