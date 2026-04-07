from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "publish_history.db"

VALID_STATUSES = {"pending", "processing", "draft", "published", "skipped", "failed"}


@dataclass
class PostStatusRecord:
    """記事の現在ステータスを保持するレコード。"""

    slug: str
    work_id: str
    keyword: str
    article_type: str
    title: str
    status: str
    post_id: int | None
    link: str | None
    error_message: str | None
    created_at: str
    updated_at: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(db_path: Path = DB_PATH) -> None:
    """post_status_tracking テーブルを作成する。"""
    sql = """
    CREATE TABLE IF NOT EXISTS post_status_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        work_id TEXT,
        keyword TEXT,
        article_type TEXT,
        title TEXT,
        status TEXT NOT NULL,
        post_id INTEGER,
        link TEXT,
        error_message TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql)
        connection.commit()


def upsert_status(record: PostStatusRecord, db_path: Path = DB_PATH) -> None:
    """slug をキーに現在ステータスを UPSERT する。"""
    normalized_status = record.status.strip().lower()
    if normalized_status not in VALID_STATUSES:
        raise ValueError(f"不正な status です: {record.status}")

    create_tables(db_path)
    sql = """
    INSERT INTO post_status_tracking (
        slug, work_id, keyword, article_type, title, status,
        post_id, link, error_message, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(slug) DO UPDATE SET
        work_id = excluded.work_id,
        keyword = excluded.keyword,
        article_type = excluded.article_type,
        title = excluded.title,
        status = excluded.status,
        post_id = excluded.post_id,
        link = excluded.link,
        error_message = excluded.error_message,
        updated_at = excluded.updated_at
    """
    with _get_connection(db_path) as connection:
        connection.execute(
            sql,
            (
                record.slug,
                record.work_id,
                record.keyword,
                record.article_type,
                record.title,
                normalized_status,
                record.post_id,
                record.link,
                record.error_message,
                record.created_at,
                record.updated_at,
            ),
        )
        connection.commit()


def build_status_record(
    *,
    slug: str,
    work_id: str,
    keyword: str,
    article_type: str,
    title: str,
    status: str,
    post_id: int | None = None,
    link: str | None = None,
    error_message: str | None = None,
) -> PostStatusRecord:
    """現在時刻付きで PostStatusRecord を構築する。"""
    now = _utc_now_iso()
    return PostStatusRecord(
        slug=slug.strip(),
        work_id=work_id.strip(),
        keyword=keyword.strip(),
        article_type=article_type.strip(),
        title=title.strip(),
        status=status.strip().lower(),
        post_id=post_id,
        link=(link or "").strip() or None,
        error_message=(error_message or "").strip() or None,
        created_at=now,
        updated_at=now,
    )


def get_status_by_slug(slug: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """slug の現在ステータスを取得する。"""
    normalized_slug = (slug or "").strip()
    if not normalized_slug:
        return None

    create_tables(db_path)
    sql = """
    SELECT slug, work_id, keyword, article_type, title, status,
           post_id, link, error_message, created_at, updated_at
    FROM post_status_tracking
    WHERE slug = ?
    LIMIT 1
    """
    with _get_connection(db_path) as connection:
        row = connection.execute(sql, (normalized_slug,)).fetchone()

    if row is None:
        return None

    return {
        "slug": row["slug"],
        "work_id": row["work_id"],
        "keyword": row["keyword"],
        "article_type": row["article_type"],
        "title": row["title"],
        "status": row["status"],
        "post_id": row["post_id"],
        "link": row["link"],
        "error_message": row["error_message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_last_updated_at(slug: str, db_path: Path = DB_PATH) -> str | None:
    """slug の最終更新時刻を返す。"""
    row = get_status_by_slug(slug, db_path=db_path)
    if not row:
        return None
    return str(row.get("updated_at", "")).strip() or None


def list_by_status(status: str, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """指定 status の記事一覧を取得する。"""
    normalized_status = (status or "").strip().lower()
    if not normalized_status:
        return []

    create_tables(db_path)
    sql = """
    SELECT slug, work_id, keyword, article_type, title, status,
           post_id, link, error_message, created_at, updated_at
    FROM post_status_tracking
    WHERE status = ?
    ORDER BY updated_at DESC
    """
    with _get_connection(db_path) as connection:
        rows = connection.execute(sql, (normalized_status,)).fetchall()

    return [
        {
            "slug": row["slug"],
            "work_id": row["work_id"],
            "keyword": row["keyword"],
            "article_type": row["article_type"],
            "title": row["title"],
            "status": row["status"],
            "post_id": row["post_id"],
            "link": row["link"],
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def list_failed_items(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """failed 状態の記事一覧を取得する。"""
    return list_by_status("failed", db_path=db_path)


def list_skipped_items(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """skipped 状態の記事一覧を取得する。"""
    return list_by_status("skipped", db_path=db_path)


def get_failed_items(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """failed 記事一覧を返す（後方互換エイリアス）。"""
    return list_failed_items(db_path=db_path)


def update_status(
    *,
    slug: str,
    work_id: str,
    keyword: str,
    article_type: str,
    title: str,
    status: str,
    post_id: int | None = None,
    link: str | None = None,
    error_message: str | None = None,
    db_path: Path = DB_PATH,
) -> None:
    """現在ステータスを1件更新する。"""
    record = build_status_record(
        slug=slug,
        work_id=work_id,
        keyword=keyword,
        article_type=article_type,
        title=title,
        status=status,
        post_id=post_id,
        link=link,
        error_message=error_message,
    )
    upsert_status(record, db_path=db_path)
