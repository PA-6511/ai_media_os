import logging
import urllib.parse
from typing import Dict, Iterable, List

import requests


class PingSender:
    """Sends sitemap update notifications to search engines and optional webhook endpoints."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.logger = logging.getLogger(self.__class__.__name__)

    def send(self, sitemap_url: str, endpoints: Iterable[str] | None = None) -> List[Dict[str, object]]:
        target_endpoints = list(endpoints) if endpoints else self.default_endpoints()
        results: List[Dict[str, object]] = []

        encoded_sitemap = urllib.parse.quote(sitemap_url, safe="")
        for endpoint in target_endpoints:
            url = endpoint.replace("{sitemap}", encoded_sitemap)
            try:
                response = requests.get(url, timeout=self.timeout)
                results.append(
                    {
                        "endpoint": endpoint,
                        "request_url": url,
                        "status_code": response.status_code,
                        "ok": response.ok,
                    }
                )
                self.logger.info("ping sent: %s -> %s", endpoint, response.status_code)
            except requests.RequestException as exc:
                self.logger.warning("ping failed: %s -> %s", endpoint, exc)
                results.append(
                    {
                        "endpoint": endpoint,
                        "request_url": url,
                        "status_code": None,
                        "ok": False,
                        "error": str(exc),
                    }
                )

        return results

    def default_endpoints(self) -> List[str]:
        # Google's historical ping endpoint may not always be available.
        # Keep endpoints configurable so operators can swap in their preferred notify hooks.
        return [
            "https://www.google.com/ping?sitemap={sitemap}",
            "https://www.bing.com/ping?sitemap={sitemap}",
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    sender = PingSender()
    demo_results = sender.send("https://example.com/sitemaps/sitemap.xml")
    print(demo_results)
