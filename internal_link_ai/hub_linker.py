import logging
from typing import Dict, List


class HubLinker:
    """Links articles to hub pages (ranking/genre/tag summaries) for structural authority."""

    HUB_TYPES = {"ranking_article", "genre_article", "summary", "tag_page"}

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self, article: Dict[str, object], article_db: List[Dict[str, object]], limit: int = 3) -> List[Dict[str, str]]:
        genre = str(article.get("genre", "")).strip().lower()
        tags = article.get("tags") or []
        if not isinstance(tags, list):
            tags = []

        links: List[Dict[str, str]] = []
        for candidate in article_db:
            candidate_id = str(candidate.get("article_id", ""))
            current_id = str(article.get("article_id", ""))
            if not candidate_id or candidate_id == current_id:
                continue

            c_type = str(candidate.get("article_type", "")).strip().lower()
            if c_type not in self.HUB_TYPES:
                continue

            c_genre = str(candidate.get("genre", "")).strip().lower()
            c_tags = candidate.get("tags") or []
            if not isinstance(c_tags, list):
                c_tags = []

            same_genre = genre and c_genre == genre
            shared_tag = bool(set(str(t).lower() for t in tags) & set(str(t).lower() for t in c_tags))

            if not same_genre and not shared_tag:
                continue

            links.append(
                {
                    "article_id": candidate_id,
                    "title": str(candidate.get("title", "ハブ記事")),
                    "url": str(candidate.get("url", "")),
                    "reason": "hub_connection",
                }
            )
            if len(links) >= limit:
                break

        self.logger.info("hub links connected article_id=%s count=%d", article.get("article_id"), len(links))
        return links
