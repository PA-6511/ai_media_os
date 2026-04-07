from __future__ import annotations

import logging
from typing import Any

from wordpress_publisher.wp_client import WordPressClient


class TermResolver:
    """category_names / tag_names を WordPress term ID に解決する。"""

    def __init__(self, client: WordPressClient) -> None:
        self.client = client
        self.logger = logging.getLogger(self.__class__.__name__)

    def find_category_by_name(self, name: str) -> dict[str, Any] | None:
        """カテゴリ名で既存termを検索し、完全一致を優先して返す。"""
        target = name.strip()
        if not target:
            return None

        for row in self.client.list_categories(search=target):
            if str(row.get("name", "")).strip() == target:
                return row
        return None

    def create_category(self, name: str) -> dict[str, Any]:
        """カテゴリを作成してレスポンスを返す。"""
        return self.client.create_category(name=name.strip())

    def resolve_category_ids(self, names: list[str]) -> list[int]:
        """カテゴリ名配列をID配列へ変換する。"""
        ids: list[int] = []
        seen: set[int] = set()

        for raw in names:
            name = str(raw).strip()
            if not name:
                continue

            term = self.find_category_by_name(name)
            if term is None:
                term = self.create_category(name)

            term_id = int(term.get("id"))
            if term_id in seen:
                continue
            seen.add(term_id)
            ids.append(term_id)

        return ids

    def find_tag_by_name(self, name: str) -> dict[str, Any] | None:
        """タグ名で既存termを検索し、完全一致を優先して返す。"""
        target = name.strip()
        if not target:
            return None

        for row in self.client.list_tags(search=target):
            if str(row.get("name", "")).strip() == target:
                return row
        return None

    def create_tag(self, name: str) -> dict[str, Any]:
        """タグを作成してレスポンスを返す。"""
        return self.client.create_tag(name=name.strip())

    def resolve_tag_ids(self, names: list[str]) -> list[int]:
        """タグ名配列をID配列へ変換する。"""
        ids: list[int] = []
        seen: set[int] = set()

        for raw in names:
            name = str(raw).strip()
            if not name:
                continue

            term = self.find_tag_by_name(name)
            if term is None:
                term = self.create_tag(name)

            term_id = int(term.get("id"))
            if term_id in seen:
                continue
            seen.add(term_id)
            ids.append(term_id)

        return ids

    def enrich_payload_with_term_ids(self, payload: dict[str, Any]) -> dict[str, Any]:
        """nameベースtermをID配列へ置換した投稿payloadを返す。"""
        enriched = dict(payload)

        category_names = payload.get("category_names", [])
        if isinstance(category_names, list) and category_names:
            category_ids = self.resolve_category_ids([str(v) for v in category_names])
            if category_ids:
                enriched["categories"] = category_ids

        tag_names = payload.get("tag_names", [])
        if isinstance(tag_names, list) and tag_names:
            tag_ids = self.resolve_tag_ids([str(v) for v in tag_names])
            if tag_ids:
                enriched["tags"] = tag_ids

        # API送信用には name配列を除去する。
        enriched.pop("category_names", None)
        enriched.pop("tag_names", None)

        return enriched
