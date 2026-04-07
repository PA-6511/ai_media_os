import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

import requests


class IndexMonitor:
    """Collects crawl/index signals after publication jobs run."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def run(self, sitemap_path: str, sample_urls: List[str]) -> Dict[str, object]:
        sitemap_stats = self._inspect_sitemap_file(sitemap_path)
        url_checks = self._check_urls(sample_urls)

        ok_count = sum(1 for row in url_checks if row.get("ok"))
        report = {
            "sitemap": sitemap_stats,
            "sample_checked": len(sample_urls),
            "sample_ok": ok_count,
            "sample_fail": len(sample_urls) - ok_count,
            "url_checks": url_checks,
        }
        self.logger.info("index monitor report generated: %s ok / %s checked", ok_count, len(sample_urls))
        return report

    def _inspect_sitemap_file(self, sitemap_path: str) -> Dict[str, object]:
        path = Path(sitemap_path)
        if not path.exists():
            return {"exists": False, "path": sitemap_path, "url_count": 0}

        try:
            tree = ET.parse(path)
            root = tree.getroot()
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            url_count = len(root.findall("sm:url", ns))
            sitemap_count = len(root.findall("sm:sitemap", ns))
        except ET.ParseError:
            return {"exists": True, "path": sitemap_path, "parse_error": True, "url_count": 0}

        return {
            "exists": True,
            "path": sitemap_path,
            "url_count": url_count,
            "sitemap_count": sitemap_count,
            "parse_error": False,
        }

    def _check_urls(self, urls: List[str]) -> List[Dict[str, object]]:
        checks: List[Dict[str, object]] = []
        for url in urls:
            try:
                resp = requests.get(url, timeout=self.timeout)
                checks.append({"url": url, "status": resp.status_code, "ok": resp.ok})
            except requests.RequestException as exc:
                checks.append({"url": url, "status": None, "ok": False, "error": str(exc)})

        return checks
