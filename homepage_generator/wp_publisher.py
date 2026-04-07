import logging
from typing import Any, Dict

import requests


class WPPublisher:
    """Create or update WordPress fixed page for homepage-like mall page."""

    def __init__(self, base_url: str, username: str, app_password: str, timeout_sec: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.app_password = app_password
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)

    def publish(self, page_data: Dict[str, Any], page_id: int | None = None, dry_run: bool = True) -> Dict[str, Any]:
        payload = {
            "title": page_data.get("title", "トップページ"),
            "content": page_data.get("content", ""),
            "status": "publish",
        }

        if dry_run:
            self.logger.info("dry_run enabled, skipping WP request")
            return {"dry_run": True, "request_payload": payload}

        if page_id:
            method = requests.post
            endpoint = f"{self.base_url}/wp-json/wp/v2/pages/{page_id}"
        else:
            method = requests.post
            endpoint = f"{self.base_url}/wp-json/wp/v2/pages"

        resp = method(
            endpoint,
            json=payload,
            auth=(self.username, self.app_password),
            headers={"Content-Type": "application/json"},
            timeout=self.timeout_sec,
        )
        if resp.status_code >= 400:
            self.logger.error("wordpress publish failed status=%s body=%s", resp.status_code, resp.text)
            resp.raise_for_status()

        result = resp.json()
        return {
            "dry_run": False,
            "page_id": result.get("id"),
            "status": result.get("status"),
            "link": result.get("link"),
        }
