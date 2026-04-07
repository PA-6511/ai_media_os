import logging
from typing import Any, Dict

import requests


class WordPressClient:
    """Thin client for WordPress REST API post creation."""

    def __init__(self, base_url: str, username: str, application_password: str, timeout_sec: int = 15) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.application_password = application_password
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = "/wp-json/wp/v2/posts"
        self.logger.info("sending post request endpoint=%s status=%s", endpoint, post_data.get("status"))
        payload = self._post(endpoint=endpoint, data=post_data)
        self.logger.info("wordpress post created id=%s link=%s", payload.get("id"), payload.get("link"))
        return payload

    def find_post_by_slug(self, slug: str) -> Dict[str, Any] | None:
        """slug で既存投稿を検索して先頭1件を返す。"""
        normalized_slug = (slug or "").strip()
        if not normalized_slug:
            return None

        params = {
            "slug": normalized_slug,
            "per_page": 1,
            "status": "any",
        }
        data = self._get("/wp-json/wp/v2/posts", params=params)
        if not isinstance(data, list) or not data:
            return None

        first = data[0] if isinstance(data[0], dict) else {}
        if not first:
            return None

        return {
            "id": first.get("id"),
            "slug": first.get("slug"),
            "link": first.get("link"),
            "status": first.get("status"),
            "date_gmt": first.get("date_gmt"),
            "modified_gmt": first.get("modified_gmt"),
            "title": (first.get("title") or {}).get("rendered", "") if isinstance(first.get("title"), dict) else "",
        }

    def list_categories(self, search: str | None = None) -> list[Dict[str, Any]]:
        """カテゴリ一覧を取得する。"""
        params: dict[str, Any] = {"per_page": 100}
        if search:
            params["search"] = search
        data = self._get("/wp-json/wp/v2/categories", params=params)
        return data if isinstance(data, list) else []

    def create_category(self, name: str) -> Dict[str, Any]:
        """カテゴリを作成する。既存時は既存termを返す。"""
        try:
            data = self._post("/wp-json/wp/v2/categories", {"name": name})
            if isinstance(data, dict):
                return data
            raise RuntimeError("カテゴリ作成レスポンスが不正です")
        except requests.HTTPError as exc:
            resolved = self._try_resolve_existing_term_from_error(exc)
            if resolved is not None:
                return resolved
            raise

    def list_tags(self, search: str | None = None) -> list[Dict[str, Any]]:
        """タグ一覧を取得する。"""
        params: dict[str, Any] = {"per_page": 100}
        if search:
            params["search"] = search
        data = self._get("/wp-json/wp/v2/tags", params=params)
        return data if isinstance(data, list) else []

    def create_tag(self, name: str) -> Dict[str, Any]:
        """タグを作成する。既存時は既存termを返す。"""
        try:
            data = self._post("/wp-json/wp/v2/tags", {"name": name})
            if isinstance(data, dict):
                return data
            raise RuntimeError("タグ作成レスポンスが不正です")
        except requests.HTTPError as exc:
            resolved = self._try_resolve_existing_term_from_error(exc)
            if resolved is not None:
                return resolved
            raise

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.get(
            url,
            params=params,
            auth=(self.username, self.application_password),
            timeout=self.timeout_sec,
            headers={"Content-Type": "application/json"},
        )
        if response.status_code >= 400:
            self.logger.error("wordpress get failed status=%s url=%s body=%s", response.status_code, url, response.text)
            response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = requests.post(
            url,
            json=data,
            auth=(self.username, self.application_password),
            timeout=self.timeout_sec,
            headers={"Content-Type": "application/json"},
        )
        if response.status_code >= 400:
            self.logger.error("wordpress post failed status=%s url=%s body=%s", response.status_code, url, response.text)
            response.raise_for_status()
        return response.json()

    def _try_resolve_existing_term_from_error(self, exc: requests.HTTPError) -> Dict[str, Any] | None:
        """term_exists エラーなら既存term IDを抽出して再取得する。"""
        response = exc.response
        if response is None:
            return None
        try:
            payload = response.json()
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None
        if payload.get("code") != "term_exists":
            return None

        term_id = payload.get("data", {}).get("term_id")
        if not term_id:
            return None

        # categories / tags どちらの作成でも term_id だけで最終利用できるため、最小情報を返す。
        return {"id": int(term_id)}
