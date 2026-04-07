import logging
from collections import defaultdict
from typing import Dict, List


class GenreLinker:
    """Connects articles within the same genre cluster for crawl path expansion."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def link_by_genre(self, genre: str, article_db: List[Dict[str, object]], limit: int = 4) -> Dict[str, List[Dict[str, str]]]:
        target = (genre or "").strip().lower()
        genre_articles = [a for a in article_db if str(a.get("genre", "")).strip().lower() == target]

        by_work: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        for article in genre_articles:
            by_work[str(article.get("work_id", ""))].append(article)

        result: Dict[str, List[Dict[str, str]]] = {}
        for article in genre_articles:
            current_id = str(article.get("article_id", ""))
            current_work_id = str(article.get("work_id", ""))
            if not current_id:
                continue

            links: List[Dict[str, str]] = []
            for work_id, rows in by_work.items():
                if work_id == current_work_id:
                    continue
                for candidate in rows:
                    candidate_id = str(candidate.get("article_id", ""))
                    if not candidate_id or candidate_id == current_id:
                        continue
                    links.append(
                        {
                            "article_id": candidate_id,
                            "title": str(candidate.get("title", "関連記事")),
                            "url": str(candidate.get("url", "")),
                            "reason": "same_genre",
                        }
                    )
                    break
                if len(links) >= limit:
                    break

            result[current_id] = links

        self.logger.info("genre links built genre=%s articles=%d", genre, len(result))
        return result
