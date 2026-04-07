from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.database.db_utils import connect_db, get_db_path


def create_tables() -> None:
    """works / articles テーブルを作成する。"""
    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS works (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT,
                    type TEXT NOT NULL,
                    genre TEXT,
                    created_at TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    article_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT
                )
                """
            )
            conn.commit()
    except Exception as exc:
        raise RuntimeError(f"テーブル作成に失敗しました: {exc}") from exc


def insert_sample_works() -> None:
    """サンプル作品を最低3件投入する。"""
    now = datetime.now(timezone.utc).isoformat()
    sample_works: list[tuple[str, str, str, str, str, str]] = [
        ("manga_0001", "呪術廻戦", "芥見下々", "manga", "バトル", now),
        ("manga_0002", "葬送のフリーレン", "山田鐘人", "manga", "ファンタジー", now),
        ("lightnovel_0001", "無職転生", "理不尽な孫の手", "lightnovel", "異世界", now),
    ]

    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR IGNORE INTO works (work_id, title, author, type, genre, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                sample_works,
            )
            conn.commit()
    except Exception as exc:
        raise RuntimeError(f"サンプル作品投入に失敗しました: {exc}") from exc


def insert_article(work_id: str, article_type: str, title: str, status: str) -> None:
    """articles テーブルに記事を追加する。"""
    if not work_id.strip():
        raise ValueError("work_id は必須です。")
    if not article_type.strip():
        raise ValueError("article_type は必須です。")
    if not title.strip():
        raise ValueError("title は必須です。")
    if not status.strip():
        raise ValueError("status は必須です。")

    now = datetime.now(timezone.utc).isoformat()

    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM works WHERE work_id = ? LIMIT 1", (work_id,))
            if cur.fetchone() is None:
                raise ValueError(f"works に存在しない work_id です: {work_id}")

            cur.execute(
                """
                INSERT INTO articles (work_id, article_type, title, status, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (work_id, article_type, title, status, now),
            )
            conn.commit()
    except Exception as exc:
        raise RuntimeError(f"記事追加に失敗しました: {exc}") from exc


def get_all_works() -> list[dict[str, Any]]:
    """works 一覧を取得する。"""
    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, work_id, title, author, type, genre, created_at
                FROM works
                ORDER BY id ASC
                """
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        raise RuntimeError(f"works 取得に失敗しました: {exc}") from exc


def get_articles_by_work(work_id: str) -> list[dict[str, Any]]:
    """指定 work_id の articles 一覧を取得する。"""
    if not work_id.strip():
        raise ValueError("work_id は必須です。")

    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, work_id, article_type, title, status, created_at
                FROM articles
                WHERE work_id = ?
                ORDER BY id ASC
                """,
                (work_id,),
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        raise RuntimeError(f"articles 取得に失敗しました: {exc}") from exc


def run() -> list[dict[str, Any]]:
    """最小セットアップを実行して works 一覧を返す。"""
    create_tables()
    insert_sample_works()

    existing = get_articles_by_work("manga_0001")
    if not any(row.get("title") == "呪術廻戦 テスト記事" for row in existing):
        insert_article("manga_0001", "work_article", "呪術廻戦 テスト記事", "draft")

    return get_all_works()


if __name__ == "__main__":
    try:
        works = run()
        print(f"DB作成先: {get_db_path()}")
        print(f"works件数: {len(works)}")
        for item in works:
            print(item)
    except Exception as exc:
        print(f"エラー: {exc}")
