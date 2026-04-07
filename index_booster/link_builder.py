import logging
from collections import defaultdict
from typing import Dict, Iterable, List


class LinkBuilder:
    """Builds related internal link recommendations to speed crawl discovery and user navigation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def build(self, articles: Iterable[Dict[str, object]], per_article: int = 6) -> Dict[str, List[str]]:
        records = [a for a in articles if a.get("url")]
        by_work_id: Dict[str, List[Dict[str, object]]] = defaultdict(list)
        by_category: Dict[str, List[Dict[str, object]]] = defaultdict(list)

        for item in records:
            work_id = str(item.get("work_id", ""))
            category = str(item.get("category", "general"))
            if work_id:
                by_work_id[work_id].append(item)
            by_category[category].append(item)

        result: Dict[str, List[str]] = {}
        for item in records:
            url = str(item["url"])
            links: List[str] = []

            work_id = str(item.get("work_id", ""))
            category = str(item.get("category", "general"))

            if work_id:
                links.extend(self._pick_other_urls(by_work_id.get(work_id, []), current=url, limit=3))

            # Blend in category links for broader crawl graph.
            links.extend(self._pick_other_urls(by_category.get(category, []), current=url, limit=2))

            # Add one high-priority route if provided.
            cta_url = item.get("cta_url")
            if isinstance(cta_url, str) and cta_url and cta_url != url:
                links.append(cta_url)

            deduped = []
            seen = set()
            for link in links:
                if link in seen:
                    continue
                seen.add(link)
                deduped.append(link)

            result[url] = deduped[:per_article]

        self.logger.info("built internal links for %s articles", len(result))
        return result

    def render_html_snippet(self, links: List[str], title: str = "関連記事") -> str:
        if not links:
            return ""

        items = "".join(
            f"<li><a href='{link}' rel='internal'>{link}</a></li>"
            for link in links
        )
        return f"<aside class='related-links'><h3>{title}</h3><ul>{items}</ul></aside>"

    def _pick_other_urls(self, items: List[Dict[str, object]], current: str, limit: int) -> List[str]:
        urls: List[str] = []
        for item in items:
            candidate = str(item.get("url", ""))
            if not candidate or candidate == current:
                continue
            urls.append(candidate)
            if len(urls) >= limit:
                break
        return urls
