import logging
from typing import Any, Dict, List

from work_id_system.work_database import WorkDatabase


class ArticleMapper:
    """Map generated articles to work IDs for unified content management."""

    VALID_ARTICLE_TYPES = {"review", "latest_volume", "sale", "ranking", "summary"}

    def __init__(self, database: WorkDatabase) -> None:
        self.database = database
        self.logger = logging.getLogger(self.__class__.__name__)

    def map_article(self, work_id: str, article_type: str, url: str) -> Dict[str, Any]:
        if article_type not in self.VALID_ARTICLE_TYPES:
            raise ValueError(f"invalid article_type: {article_type}")
        if not self.database.get_work(work_id):
            raise ValueError(f"work_id not found: {work_id}")

        article_id = self.database.insert_article(work_id=work_id, article_type=article_type, url=url)
        mapped = {
            "id": article_id,
            "work_id": work_id,
            "article_type": article_type,
            "url": url,
        }
        self.logger.info("article mapped work_id=%s article_type=%s", work_id, article_type)
        return mapped

    def get_related_articles(self, work_id: str) -> List[Dict[str, Any]]:
        return self.database.get_articles_by_work_id(work_id)
