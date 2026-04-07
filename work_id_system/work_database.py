import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class WorkDatabase:
    """SQLite-backed storage for works and their related articles."""

    def __init__(self, db_path: str = "data/ai_media_os.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS works (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT,
                    genre TEXT,
                    type TEXT NOT NULL,
                    volumes INTEGER DEFAULT 0,
                    release_date TEXT,
                    UNIQUE(title, type)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work_id TEXT NOT NULL,
                    article_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    UNIQUE(work_id, article_type, url),
                    FOREIGN KEY(work_id) REFERENCES works(id)
                )
                """
            )
        self.logger.info("database initialized path=%s", self.db_path)

    def insert_work(self, work_data: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO works (id, title, author, publisher, genre, type, volumes, release_date)
                VALUES (:id, :title, :author, :publisher, :genre, :type, :volumes, :release_date)
                """,
                {
                    "id": work_data["id"],
                    "title": work_data["title"],
                    "author": work_data.get("author"),
                    "publisher": work_data.get("publisher"),
                    "genre": work_data.get("genre"),
                    "type": work_data["type"],
                    "volumes": int(work_data.get("volumes", 0) or 0),
                    "release_date": work_data.get("release_date"),
                },
            )

    def get_work_by_title_and_type(self, title: str, work_type: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM works WHERE title = ? AND type = ?",
                (title, work_type),
            ).fetchone()
            return dict(row) if row else None

    def get_work(self, work_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
            return dict(row) if row else None

    def list_works(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM works ORDER BY id LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def next_sequence(self, prefix: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM works WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
                (f"{prefix}_%",),
            ).fetchone()
            if not row:
                return 1
            last_id = str(row["id"])
            try:
                return int(last_id.split("_")[-1]) + 1
            except ValueError:
                return 1

    def insert_article(self, work_id: str, article_type: str, url: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO articles (work_id, article_type, url)
                VALUES (?, ?, ?)
                """,
                (work_id, article_type, url),
            )
            return int(cur.lastrowid)

    def get_articles_by_work_id(self, work_id: str) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, work_id, article_type, url FROM articles WHERE work_id = ? ORDER BY id",
                (work_id,),
            ).fetchall()
            return [dict(r) for r in rows]
