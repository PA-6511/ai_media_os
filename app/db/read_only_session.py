from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.db.access_guard import assert_database_target_allowed
from app.db.config import DATABASE_BACKEND, DATABASE_URL


def sqlite_database_path(database_url: str) -> Path:
    url = make_url(database_url)

    if not url.drivername.startswith("sqlite"):
        raise ValueError("Read-only GUI search requires a SQLite database URL.")

    if not url.database or url.database == ":memory:":
        raise ValueError("Read-only GUI search requires a file-backed SQLite database.")

    return Path(url.database).expanduser().resolve()


def sqlite_read_only_uri(database_path: str | Path) -> str:
    resolved_path = Path(database_path).expanduser().resolve()
    encoded_path = quote(str(resolved_path), safe="/")
    return f"file:{encoded_path}?mode=ro"


def create_sqlite_read_only_engine(
    database_path: str | Path,
) -> Engine:
    resolved_path = assert_database_target_allowed(
        database_path,
        operation="read-only SQLite engine creation",
    )
    if resolved_path is None:
        raise ValueError("Read-only SQLite requires a file-backed database.")
    read_only_uri = sqlite_read_only_uri(resolved_path)

    def connect_read_only() -> sqlite3.Connection:
        assert_database_target_allowed(
            resolved_path,
            operation="read-only SQLite connection",
        )
        return sqlite3.connect(
            read_only_uri,
            uri=True,
            check_same_thread=False,
            timeout=30,
        )

    return create_engine(
        "sqlite://",
        creator=connect_read_only,
        poolclass=NullPool,
        pool_pre_ping=True,
    )


def create_sqlite_read_only_session_factory(
    database_path: str | Path,
) -> sessionmaker:
    engine = create_sqlite_read_only_engine(database_path)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


if DATABASE_BACKEND != "sqlite":
    raise RuntimeError(
        "The database-search GUI currently supports read-only SQLite only."
    )


READ_ONLY_DATABASE_PATH = sqlite_database_path(DATABASE_URL)
_read_only_session_factory: sessionmaker | None = None


def get_read_only_session_factory() -> sessionmaker:
    global _read_only_session_factory
    assert_database_target_allowed(
        READ_ONLY_DATABASE_PATH,
        operation="cached read-only SQLite session factory",
    )
    if _read_only_session_factory is None:
        _read_only_session_factory = create_sqlite_read_only_session_factory(
            READ_ONLY_DATABASE_PATH
        )
    return _read_only_session_factory


def ReadOnlySessionLocal():
    """Compatibility callable which creates no engine during module import."""

    return get_read_only_session_factory()()
