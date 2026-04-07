from typing import Dict, List


class ArticleBlock:
    def run(self) -> List[Dict]:
        return [
            {
                "source": "article_block",
                "action": "generate_article",
                "target": "2026年春の電子書籍セール特集",
                "priority": 0.6,
            }
        ]
