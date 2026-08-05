from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, event, inspect

from app.db.base import Base
from app.db.config import DATABASE_BACKEND
from app.db import models as _models  # noqa: F401


@pytest.fixture()
def isolated_engine(tmp_path: Path) -> Iterator[Engine]:
    """Exercise SQLite bootstrap behavior without opening the configured DB."""

    engine = create_engine(f"sqlite:///{tmp_path / 'bootstrap.sqlite'}")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection: object,
        connection_record: object,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def test_database_backend_is_supported() -> None:
    assert DATABASE_BACKEND in {"sqlite", "postgresql"}


def test_expected_tables_exist(isolated_engine: Engine) -> None:
    table_names = set(inspect(isolated_engine).get_table_names())

    assert "ebook_items" in table_names
    assert "store_offers" in table_names


def test_sqlite_foreign_keys_are_enabled(isolated_engine: Engine) -> None:
    if DATABASE_BACKEND != "sqlite":
        return

    with isolated_engine.connect() as connection:
        enabled = connection.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

    assert enabled == 1
