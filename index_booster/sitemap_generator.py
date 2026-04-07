import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET


class SitemapGenerator:
    """Builds sitemap.xml and optional sharded sitemaps for large URL sets."""

    def __init__(
        self,
        base_url: str,
        output_dir: str = "data/sitemaps",
        max_urls_per_sitemap: int = 50000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.output_dir = Path(output_dir)
        self.max_urls_per_sitemap = max_urls_per_sitemap
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, urls: Iterable[Dict[str, str]]) -> Dict[str, object]:
        records = [self._normalize_url_record(item) for item in urls]
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if len(records) <= self.max_urls_per_sitemap:
            sitemap_path = self.output_dir / "sitemap.xml"
            self._write_urlset(sitemap_path, records)
            return {
                "mode": "single",
                "count": len(records),
                "files": [str(sitemap_path)],
            }

        # For very large URL sets, split into multiple sitemap files and create an index.
        part_paths: List[Path] = []
        for idx in range(0, len(records), self.max_urls_per_sitemap):
            part = records[idx : idx + self.max_urls_per_sitemap]
            part_no = idx // self.max_urls_per_sitemap + 1
            part_path = self.output_dir / f"sitemap-{part_no}.xml"
            self._write_urlset(part_path, part)
            part_paths.append(part_path)

        index_path = self.output_dir / "sitemap.xml"
        self._write_index(index_path, part_paths)

        return {
            "mode": "index",
            "count": len(records),
            "files": [str(index_path)] + [str(p) for p in part_paths],
        }

    def load_urls_from_articles(self, articles: Iterable[Dict[str, object]]) -> List[Dict[str, str]]:
        urls: List[Dict[str, str]] = []
        for article in articles:
            slug = str(article.get("slug", "")).strip("/")
            if not slug:
                continue

            updated_at = article.get("updated_at")
            if isinstance(updated_at, datetime):
                lastmod = updated_at.astimezone(timezone.utc).isoformat()
            elif isinstance(updated_at, str) and updated_at:
                lastmod = updated_at
            else:
                lastmod = datetime.now(tz=timezone.utc).isoformat()

            urls.append(
                {
                    "loc": f"{self.base_url}/{slug}",
                    "lastmod": lastmod,
                    "changefreq": str(article.get("changefreq", "daily")),
                    "priority": str(article.get("priority", "0.8")),
                }
            )
        return urls

    def _normalize_url_record(self, record: Dict[str, str]) -> Dict[str, str]:
        loc = record.get("loc", "").strip()
        if not loc:
            raise ValueError("Each sitemap record must include a non-empty 'loc'.")

        if not loc.startswith("http://") and not loc.startswith("https://"):
            loc = f"{self.base_url}/{loc.strip('/')}"

        return {
            "loc": loc,
            "lastmod": record.get("lastmod") or datetime.now(tz=timezone.utc).isoformat(),
            "changefreq": record.get("changefreq", "daily"),
            "priority": record.get("priority", "0.8"),
        }

    def _write_urlset(self, path: Path, records: List[Dict[str, str]]) -> None:
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = ET.Element("urlset", xmlns=ns)

        for item in records:
            url_el = ET.SubElement(root, "url")
            ET.SubElement(url_el, "loc").text = item["loc"]
            ET.SubElement(url_el, "lastmod").text = item["lastmod"]
            ET.SubElement(url_el, "changefreq").text = item["changefreq"]
            ET.SubElement(url_el, "priority").text = item["priority"]

        self._write_xml(path, root)
        self.logger.info("sitemap written: %s (%s urls)", path, len(records))

    def _write_index(self, path: Path, part_paths: List[Path]) -> None:
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        root = ET.Element("sitemapindex", xmlns=ns)

        for part_path in part_paths:
            sitemap_el = ET.SubElement(root, "sitemap")
            loc = f"{self.base_url}/{self._public_sitemap_path(part_path)}"
            ET.SubElement(sitemap_el, "loc").text = loc
            ET.SubElement(sitemap_el, "lastmod").text = datetime.now(tz=timezone.utc).isoformat()

        self._write_xml(path, root)
        self.logger.info("sitemap index written: %s (%s parts)", path, len(part_paths))

    def _public_sitemap_path(self, file_path: Path) -> str:
        # Maps local output path to a web path. Override with env if needed.
        public_prefix = os.getenv("SITEMAP_PUBLIC_PREFIX", "sitemaps").strip("/")
        return f"{public_prefix}/{file_path.name}"

    def _write_xml(self, path: Path, root: ET.Element) -> None:
        tree = ET.ElementTree(root)
        tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    generator = SitemapGenerator(base_url="https://example.com")
    demo_urls = [
        {"loc": "https://example.com/ranking/sale-top", "changefreq": "hourly", "priority": "0.9"},
        {"loc": "https://example.com/work/demo-title", "changefreq": "daily", "priority": "0.8"},
    ]
    print(generator.generate(demo_urls))
