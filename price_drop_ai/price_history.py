from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "price_history.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables() -> None:
    """価格履歴テーブルを作成する。"""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id TEXT NOT NULL,
                article_type TEXT,
                keyword TEXT,
                current_price REAL,
                discount_rate REAL,
                checked_at TEXT NOT NULL
            )
            """
        )

        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(price_history)").fetchall()
        }

        # 旧スキーマ（price_history_store）との互換マイグレーション。
        if "article_type" not in columns:
            conn.execute("ALTER TABLE price_history ADD COLUMN article_type TEXT")
        if "keyword" not in columns:
            conn.execute("ALTER TABLE price_history ADD COLUMN keyword TEXT")
        if "current_price" not in columns:
            conn.execute("ALTER TABLE price_history ADD COLUMN current_price REAL")
        if "discount_rate" not in columns:
            conn.execute("ALTER TABLE price_history ADD COLUMN discount_rate REAL")
        if "checked_at" not in columns:
            conn.execute("ALTER TABLE price_history ADD COLUMN checked_at TEXT")

        # 旧カラム名から新カラムへ値を補完する。
        if "price" in columns:
            conn.execute(
                """
                UPDATE price_history
                SET current_price = COALESCE(current_price, price)
                """
            )
        if "recorded_at" in columns:
            conn.execute(
                """
                UPDATE price_history
                SET checked_at = COALESCE(checked_at, recorded_at, CURRENT_TIMESTAMP)
                """
            )
        else:
            conn.execute(
                """
                UPDATE price_history
                SET checked_at = COALESCE(checked_at, CURRENT_TIMESTAMP)
                """
            )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_history_lookup
            ON price_history(work_id, article_type, keyword, checked_at DESC)
            """
        )


def get_latest_price(work_id: str, article_type: str, keyword: str) -> dict[str, Any] | None:
    """作品/記事タイプ/キーワード単位で直近の価格スナップショットを返す。"""
    create_tables()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, work_id, article_type, keyword, current_price, discount_rate, checked_at
            FROM price_history
            WHERE work_id = ? AND article_type = ? AND keyword = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT 1
            """,
            (work_id, article_type, keyword),
        ).fetchone()

    if not row:
        return None

    return {
        "id": int(row["id"]),
        "work_id": str(row["work_id"] or ""),
        "article_type": str(row["article_type"] or ""),
        "keyword": str(row["keyword"] or ""),
        "current_price": float(row["current_price"] or 0.0),
        "discount_rate": float(row["discount_rate"] or 0.0),
        "checked_at": str(row["checked_at"] or ""),
    }


def save_price_snapshot(record: dict[str, Any]) -> None:
    """現在価格スナップショットを保存する。"""
    create_tables()

    work_id = str(record.get("work_id", "")).strip()
    article_type = str(record.get("article_type", "")).strip()
    keyword = str(record.get("keyword", "")).strip()
    checked_at = str(record.get("checked_at", "")).strip()
    if not work_id:
        raise ValueError("work_id が空です")
    if not checked_at:
        raise ValueError("checked_at が空です")

    current_price = float(record.get("current_price", 0.0) or 0.0)
    discount_rate = float(record.get("discount_rate", 0.0) or 0.0)

    with _connect() as conn:
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(price_history)").fetchall()
        }

        payload: dict[str, Any] = {
            "work_id": work_id,
            "article_type": article_type,
            "keyword": keyword,
            "current_price": current_price,
            "discount_rate": discount_rate,
            "checked_at": checked_at,
        }

        # 旧スキーマ互換カラムの補完。
        if "store" in columns:
            payload["store"] = str(record.get("store", "manual")).strip() or "manual"
        if "title" in columns:
            payload["title"] = str(record.get("title", keyword)).strip() or keyword
        if "price" in columns:
            payload["price"] = int(round(current_price))
        if "is_sale" in columns:
            payload["is_sale"] = 1 if discount_rate > 0 else 0
        if "recorded_at" in columns:
            payload["recorded_at"] = checked_at

        target_columns = [name for name in payload.keys() if name in columns]
        placeholders = ", ".join(["?" for _ in target_columns])
        columns_sql = ", ".join(target_columns)
        values = [payload[name] for name in target_columns]

        conn.execute(
            f"INSERT INTO price_history ({columns_sql}) VALUES ({placeholders})",
            values,
        )


class PriceHistoryStore:
    """旧実装との互換用ラッパークラス。"""

    def __init__(self, db_path: str = "data/price_history.db") -> None:
        _ = db_path  # 既存シグネチャ互換のため保持

    def get_latest(self, work_id: str, store: str) -> dict[str, Any] | None:
        # 旧実装は store 軸だったため keyword に store を流用する。
        return get_latest_price(work_id=work_id, article_type="sale_article", keyword=store)

    def save(self, row: dict[str, Any]) -> None:
        checked_at = row.get("recorded_at") or row.get("checked_at")
        if not checked_at:
            checked_at = datetime.now(timezone.utc).isoformat()
        save_price_snapshot(
            {
                "work_id": str(row.get("work_id", "")).strip(),
                "article_type": "sale_article",
                "keyword": str(row.get("store", "manual")).strip() or "manual",
                "current_price": row.get("price", 0),
                "discount_rate": 10.0 if bool(row.get("is_sale", False)) else 0.0,
                "checked_at": checked_at,
                "store": row.get("store", "manual"),
                "title": row.get("title", ""),
            }
        )
