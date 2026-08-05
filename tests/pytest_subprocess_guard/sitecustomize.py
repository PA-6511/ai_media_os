"""Install the SQLite path guard only in Python children spawned by pytest."""

from __future__ import annotations

import sqlite3
import os
from typing import Any

from app.db.access_guard import assert_database_target_allowed


os.environ["AI_MEDIA_OS_PYTEST_SUBPROCESS_GUARD_LOADED"] = "1"


if not getattr(sqlite3, "_ai_media_os_guard_installed", False):
    _original_sqlite_connect = sqlite3.connect

    def _guarded_sqlite_connect(database: Any, *args: Any, **kwargs: Any):
        assert_database_target_allowed(
            database,
            operation="sqlite3.connect in pytest subprocess",
            testing=True,
        )
        return _original_sqlite_connect(database, *args, **kwargs)

    sqlite3.connect = _guarded_sqlite_connect
    sqlite3.dbapi2.connect = _guarded_sqlite_connect
    sqlite3._ai_media_os_guard_installed = True
