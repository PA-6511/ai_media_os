import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

from index_booster.sitemap_generator import SitemapGenerator


class RecentSitemapGenerator:
    """Creates a compact sitemap with only the most recently updated URLs."""

    def __init__(
        self,
        base_url: str,
        output_dir: str = "data/sitemaps",
        filename: str = "sitemap-recent.xml",
        max_urls: int = 500,
    ) -> None:
        self.base_url = base_url
        self.output_dir = output_dir
        self.filename = filename
        self.max_urls = max_urls
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, urls: Iterable[Dict[str, str]]) -> Dict[str, object]:
        records = list(urls)
        sorted_records = sorted(records, key=self._timestamp_key, reverse=True)
        recent = sorted_records[: self.max_urls]

        generator = SitemapGenerator(base_url=self.base_url, output_dir=self.output_dir, max_urls_per_sitemap=50000)
        output_path = Path(self.output_dir) / self.filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        normalized = [generator._normalize_url_record(item) for item in recent]  # noqa: SLF001
        generator._write_urlset(output_path, normalized)  # noqa: SLF001
        self.logger.info("recent sitemap generated: %s (%s urls)", output_path, len(normalized))

        return {
            "count": len(recent),
            "files": [str(output_path)],
        }

    def _timestamp_key(self, record: Dict[str, str]) -> float:
        raw = record.get("lastmod", "")
        if not raw:
            return 0.0
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
