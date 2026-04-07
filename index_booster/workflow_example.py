import json
import logging
from datetime import datetime, timezone

from index_booster.index_monitor import IndexMonitor
from index_booster.link_builder import LinkBuilder
from index_booster.ping_sender import PingSender
from index_booster.recent_sitemap import RecentSitemapGenerator
from index_booster.sitemap_generator import SitemapGenerator


def run_workflow() -> dict:
    base_url = "https://example.com"
    now = datetime.now(tz=timezone.utc).isoformat()

    posted_articles = [
        {
            "work_id": "wk-001",
            "category": "review",
            "url": f"{base_url}/manga/jujutsu-review",
            "slug": "manga/jujutsu-review",
            "updated_at": now,
            "cta_url": f"{base_url}/manga/jujutsu-sale",
        },
        {
            "work_id": "wk-001",
            "category": "volume_guide",
            "url": f"{base_url}/manga/jujutsu-volumes",
            "slug": "manga/jujutsu-volumes",
            "updated_at": now,
            "cta_url": f"{base_url}/manga/jujutsu-sale",
        },
        {
            "work_id": "wk-002",
            "category": "sale",
            "url": f"{base_url}/manga/sale-today",
            "slug": "manga/sale-today",
            "updated_at": now,
            "cta_url": f"{base_url}/ranking/sale-ranking",
        },
    ]

    sitemap = SitemapGenerator(base_url=base_url)
    sitemap_urls = sitemap.load_urls_from_articles(posted_articles)
    sitemap_result = sitemap.generate(sitemap_urls)

    recent_sitemap = RecentSitemapGenerator(base_url=base_url)
    recent_result = recent_sitemap.generate(sitemap_urls)

    ping_sender = PingSender()
    ping_result = ping_sender.send(f"{base_url}/sitemaps/sitemap.xml")

    link_builder = LinkBuilder()
    links = link_builder.build(posted_articles)

    monitor = IndexMonitor()
    monitor_result = monitor.run(
        sitemap_path="data/sitemaps/sitemap.xml",
        sample_urls=[item["url"] for item in posted_articles],
    )

    return {
        "sitemap": sitemap_result,
        "recent_sitemap": recent_result,
        "ping": ping_result,
        "internal_links": links,
        "monitor": monitor_result,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    print(json.dumps(run_workflow(), indent=2, ensure_ascii=False))
