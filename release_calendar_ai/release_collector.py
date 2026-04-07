from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE_DATA_PATH = BASE_DIR / "data" / "release_data_mock.json"


def _load_release_source() -> dict[str, dict[str, Any]]:
    """ダミー新刊データを読み込む。未作成時は空dictを返す。"""
    source_path = Path(os.getenv("RELEASE_DATA_PATH", str(DEFAULT_RELEASE_DATA_PATH))).expanduser()
    if not source_path.exists():
        return {}

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            normalized[str(key)] = value
    return normalized


def fetch_current_release_info(item: dict[str, Any]) -> dict[str, Any]:
    """item に対応する現在の新刊情報を返す。"""
    source = _load_release_source()
    work_id = str(item.get("work_id", "")).strip()
    keyword = str(item.get("keyword", "")).strip()

    row = source.get(work_id) or source.get(keyword) or {}

    title = str(row.get("title", "")).strip()
    if not title:
        title = keyword.split()[0].strip() if keyword else work_id

    latest_volume_number = row.get("latest_volume_number")
    if latest_volume_number is None:
        # work_id 由来で安定的に疑似巻数を作る。
        latest_volume_number = (sum(ord(ch) for ch in work_id) % 30) + 1

    latest_release_date = str(row.get("latest_release_date", "")).strip() or datetime.now(timezone.utc).date().isoformat()
    availability_status = str(row.get("availability_status", "")).strip() or "available"

    return {
        "work_id": work_id,
        "title": title,
        "latest_volume_number": int(latest_volume_number),
        "latest_release_date": latest_release_date,
        "availability_status": availability_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class ReleaseCollector:
    """Collect release schedule data from publishers and stores."""

    def __init__(self, timeout_sec: int = 10) -> None:
        self.timeout_sec = timeout_sec
        self.logger = logging.getLogger(self.__class__.__name__)
        self.endpoints = {
            "publisher": "https://example.com/api/releases/publisher",
            "ebook_store": "https://example.com/api/releases/store",
        }

    def collect(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for source, endpoint in self.endpoints.items():
            items = self._fetch_or_fallback(source, endpoint)
            rows.extend(items)
            self.logger.info("release rows collected source=%s count=%d", source, len(items))
        return rows

    def _fetch_or_fallback(self, source: str, endpoint: str) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(endpoint, timeout=self.timeout_sec)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                rows = payload
            else:
                rows = payload.get("items", [])
            return [self._normalize(row) for row in rows]
        except Exception as exc:  # pragma: no cover
            self.logger.warning("fallback release data source=%s reason=%s", source, exc)
            return self._fallback(source)

    def _normalize(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": str(row.get("title", "")).strip(),
            "work_id": str(row.get("work_id", "")).strip(),
            "release_date": str(row.get("release_date", "")).strip(),
            "publisher": str(row.get("publisher", "")).strip(),
            "content_type": str(row.get("content_type", "manga")).strip().lower(),
            "affiliate_url": str(row.get("affiliate_url", "")).strip(),
        }

    @staticmethod
    def _fallback(source: str) -> List[Dict[str, Any]]:
        _ = source
        return [
            {
                "title": "呪術廻戦 29巻",
                "work_id": "manga_0123",
                "release_date": "2026-04-04",
                "publisher": "集英社",
                "content_type": "manga",
                "affiliate_url": "https://affiliate.example.com/jujutsu-29",
            },
            {
                "title": "葬送のフリーレン 15巻",
                "work_id": "manga_0456",
                "release_date": "2026-04-01",
                "publisher": "小学館",
                "content_type": "manga",
                "affiliate_url": "https://affiliate.example.com/frieren-15",
            },
            {
                "title": "転生王子の冒険譚 8巻",
                "work_id": "ln_0010",
                "release_date": "2026-04-10",
                "publisher": "KADOKAWA",
                "content_type": "light_novel",
                "affiliate_url": "https://affiliate.example.com/tensei-prince-8",
            },
            {
                "title": "データ駆動SEO入門",
                "work_id": "book_0088",
                "release_date": "2026-04-18",
                "publisher": "技術評論社",
                "content_type": "book",
                "affiliate_url": "https://affiliate.example.com/seo-book",
            },
        ]
