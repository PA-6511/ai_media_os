from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "release_history.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables() -> None:
    """新刊履歴テーブルを作成する。"""
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS release_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_id TEXT NOT NULL,
                title TEXT,
                latest_volume_number INTEGER,
                latest_release_date TEXT,
                availability_status TEXT,
                checked_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_release_history_work
            ON release_history(work_id, checked_at DESC)
            """
        )


def get_latest_release_record(work_id: str) -> dict[str, Any] | None:
    """work_id 単位で最新の新刊情報を取得する。"""
    create_tables()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, work_id, title, latest_volume_number, latest_release_date, availability_status, checked_at
            FROM release_history
            WHERE work_id = ?
            ORDER BY checked_at DESC, id DESC
            LIMIT 1
            """,
            (work_id,),
        ).fetchone()

    if not row:
        return None

    latest_volume_number = row["latest_volume_number"]
    return {
        "id": int(row["id"]),
        "work_id": str(row["work_id"] or ""),
        "title": str(row["title"] or ""),
        "latest_volume_number": int(latest_volume_number) if latest_volume_number is not None else None,
        "latest_release_date": str(row["latest_release_date"] or ""),
        "availability_status": str(row["availability_status"] or ""),
        "checked_at": str(row["checked_at"] or ""),
    }


def save_release_snapshot(record: dict[str, Any]) -> None:
    """今回取得した新刊情報を保存する。"""
    create_tables()

    work_id = str(record.get("work_id", "")).strip()
    checked_at = str(record.get("checked_at", "")).strip()
    if not work_id:
        raise ValueError("work_id が空です")
    if not checked_at:
        raise ValueError("checked_at が空です")

    volume_value = record.get("latest_volume_number")
    latest_volume_number = int(volume_value) if volume_value is not None else None

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO release_history (
                work_id,
                title,
                latest_volume_number,
                latest_release_date,
                availability_status,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                str(record.get("title", "")).strip(),
                latest_volume_number,
                str(record.get("latest_release_date", "")).strip(),
                str(record.get("availability_status", "")).strip(),
                checked_at,
            ),
        )
