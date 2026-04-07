import logging
from typing import Any, Dict

import requests


class WPPublisher:
    """Publish generated ranking pages to WordPress as draft posts."""

    def __init__(self, base_url: str, username: str, app_password: str, timeout_sec: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)

    def publish(self, article: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        payload = {
            "title": article.get("title"),
            "content": article.get("content"),
            "status": "draft",
        }

        if dry_run:
            self.logger.info("dry_run enabled, skipping WP API call")
            return {
                "dry_run": True,
                "request_payload": payload,
            }

        url = f"{self.base_url}/wp-json/wp/v2/posts"
        self.logger.info("posting to wordpress endpoint=%s", url)
        resp = requests.post(
            url,
            json=payload,
            auth=(self.username, self.app_password),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout_sec,
        )

        if resp.status_code >= 400:
            self.logger.error("wordpress post failed status=%s body=%s", resp.status_code, resp.text)
            resp.raise_for_status()

        row = resp.json()
        return {
            "dry_run": False,
            "post_id": row.get("id"),
            "status": row.get("status"),
            "link": row.get("link"),
        }
