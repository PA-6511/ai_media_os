import re
from typing import Dict, List

from work_id_system.article_mapper import ArticleMapper
from work_id_system.work_database import WorkDatabase


class LinkMapper:
    """Generate canonical and related internal links from work/article mappings."""

    def __init__(self, database: WorkDatabase, article_mapper: ArticleMapper, base_url: str = "https://manga.example.com") -> None:
        self.database = database
        self.article_mapper = article_mapper
        self.base_url = base_url.rstrip("/")

    def build_work_base_url(self, work_id: str) -> str:
        work = self.database.get_work(work_id)
        if not work:
            raise ValueError(f"work_id not found: {work_id}")
        slug = self._slugify(str(work["title"]))
        return f"{self.base_url}/work/{slug}"

    def build_related_links(self, work_id: str) -> List[str]:
        base = self.build_work_base_url(work_id)
        articles = self.article_mapper.get_related_articles(work_id)
        links = [base]
        for article in articles:
            atype = str(article.get("article_type", "summary"))
            links.append(f"{base}/{atype.replace('_', '-')}")
        return sorted(set(links))

    def _slugify(self, text: str) -> str:
        lowered = text.strip().lower()
        lowered = re.sub(r"\s+", "-", lowered)
        lowered = re.sub(r"[^a-z0-9\-ぁ-んァ-ン一-龠]", "", lowered)
        return lowered or "work"
