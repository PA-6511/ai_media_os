from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
HISTORY_DB_PATH = DATA_DIR / "publish_history.db"


@dataclass
class PublishRecord:
    """投稿履歴1件分のデータ。"""

    slug: str
    work_id: str
    keyword: str
    article_type: str
    title: str
    post_id: int | None
    link: str
    status: str
    published_at: str


def _get_connection(db_path: Path = HISTORY_DB_PATH) -> sqlite3.Connection:
    """履歴DB接続を返す。"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(db_path: Path = HISTORY_DB_PATH) -> None:
    """履歴テーブルを作成する。"""
    sql = """
    CREATE TABLE IF NOT EXISTS publish_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        work_id TEXT,
        keyword TEXT,
        article_type TEXT,
        title TEXT,
        post_id INTEGER,
        link TEXT,
        status TEXT,
        published_at TEXT NOT NULL
    )
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql)
        connection.commit()


def find_by_slug(slug: str, db_path: Path = HISTORY_DB_PATH) -> dict[str, Any] | None:
    """slug で履歴を検索する。"""
    normalized_slug = (slug or "").strip()
    if not normalized_slug:
        return None

    create_tables(db_path)
    query = """
    SELECT slug, work_id, keyword, article_type, title, post_id, link, status, published_at
    FROM publish_history
    WHERE slug = ?
    LIMIT 1
    """
    with _get_connection(db_path) as connection:
        row = connection.execute(query, (normalized_slug,)).fetchone()

    if row is None:
        return None

    return {
        "slug": row["slug"],
        "work_id": row["work_id"],
        "keyword": row["keyword"],
        "article_type": row["article_type"],
        "title": row["title"],
        "post_id": row["post_id"],
        "link": row["link"],
        "status": row["status"],
        "published_at": row["published_at"],
    }


def save_publish_record(record: PublishRecord, db_path: Path = HISTORY_DB_PATH) -> None:
    """投稿履歴を UPSERT 保存する。"""
    create_tables(db_path)
    upsert_sql = """
    INSERT INTO publish_history (
        slug, work_id, keyword, article_type, title, post_id, link, status, published_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(slug) DO UPDATE SET
        work_id = excluded.work_id,
        keyword = excluded.keyword,
        article_type = excluded.article_type,
        title = excluded.title,
        post_id = excluded.post_id,
        link = excluded.link,
        status = excluded.status,
        published_at = excluded.published_at
    """
    with _get_connection(db_path) as connection:
        connection.execute(
            upsert_sql,
            (
                record.slug,
                record.work_id,
                record.keyword,
                record.article_type,
                record.title,
                record.post_id,
                record.link,
                record.status,
                record.published_at,
            ),
        )
        connection.commit()


def build_record(
    slug: str,
    article_output_with_journey: dict[str, Any],
    post_id: int | None,
    link: str,
    status: str,
) -> PublishRecord:
    """記事データと投稿結果から履歴レコードを構築する。"""
    return PublishRecord(
        slug=slug,
        work_id=str(article_output_with_journey.get("work_id", "")).strip(),
        keyword=str(article_output_with_journey.get("keyword", "")).strip(),
        article_type=str(article_output_with_journey.get("article_type", "")).strip(),
        title=str(article_output_with_journey.get("title", "")).strip(),
        post_id=post_id,
        link=link,
        status=status,
        published_at=datetime.now(timezone.utc).isoformat(),
    )
