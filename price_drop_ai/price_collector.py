from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PRICE_DATA_PATH = BASE_DIR / "data" / "price_data_mock.json"


def _load_price_source() -> dict[str, dict[str, Any]]:
    """ダミー価格データを読み込む。未作成時は空dictを返す。"""
    source_path = Path(os.getenv("PRICE_DATA_PATH", str(DEFAULT_PRICE_DATA_PATH))).expanduser()
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


def _fallback_price(item: dict[str, Any]) -> float:
    """価格データ未設定時のフォールバック価格を返す。"""
    work_id = str(item.get("work_id", "")).strip()
    article_type = str(item.get("article_type", "")).strip()
    base = 700.0 if article_type == "sale_article" else 650.0

    # 同一作品は同じ価格が出るよう、簡易的に安定ハッシュを使う。
    modifier = sum(ord(ch) for ch in work_id) % 120
    return max(100.0, base - float(modifier))


def _fallback_discount_rate(item: dict[str, Any]) -> float:
    """割引率データ未設定時のフォールバック値を返す。"""
    article_type = str(item.get("article_type", "")).strip()
    if article_type == "sale_article":
        return 15.0
    return 0.0


def fetch_current_price(item: dict[str, Any]) -> float:
    """item に対応する現在価格を返す。"""
    source = _load_price_source()
    work_id = str(item.get("work_id", "")).strip()
    keyword = str(item.get("keyword", "")).strip()

    # キー優先度: work_id -> keyword
    row = source.get(work_id) or source.get(keyword)
    if row and "current_price" in row:
        try:
            return float(row.get("current_price"))
        except (TypeError, ValueError):
            pass

    return _fallback_price(item)


def fetch_current_discount_rate(item: dict[str, Any]) -> float:
    """item に対応する現在の割引率を返す。"""
    source = _load_price_source()
    work_id = str(item.get("work_id", "")).strip()
    keyword = str(item.get("keyword", "")).strip()

    row = source.get(work_id) or source.get(keyword)
    if row and "discount_rate" in row:
        try:
            return float(row.get("discount_rate"))
        except (TypeError, ValueError):
            pass

    return _fallback_discount_rate(item)


def build_current_price_record(item: dict[str, Any]) -> dict[str, Any]:
    """比較と保存に使う現在価格レコードを生成する。"""
    return {
        "work_id": str(item.get("work_id", "")).strip(),
        "keyword": str(item.get("keyword", "")).strip(),
        "article_type": str(item.get("article_type", "")).strip(),
        "current_price": fetch_current_price(item),
        "discount_rate": fetch_current_discount_rate(item),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


class PriceCollector:
    """旧実装との互換用ラッパークラス。"""

    def collect(self) -> list[dict[str, Any]]:
        source = _load_price_source()
        rows: list[dict[str, Any]] = []
        for key, value in source.items():
            rows.append(
                {
                    "work_id": key,
                    "title": str(value.get("title", key)),
                    "price": int(float(value.get("current_price", 0) or 0)),
                    "store": str(value.get("store", "manual")),
                    "is_sale": float(value.get("discount_rate", 0) or 0) > 0,
                }
            )
        return rows
