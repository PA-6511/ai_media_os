"""Fail-closed SQLite path checks shared by runtime and test entrypoints.

This module deliberately uses only the Python standard library so one-shot
CLI tools can run the guard before importing SQLAlchemy or opening SQLite.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Mapping, Sequence
from urllib.parse import unquote, urlsplit


PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST = (
    "PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST"
)


class ProductionDatabaseAccessBlocked(RuntimeError):
    """Raised before SQLite is opened when a test target is not isolated."""


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_test_environment(
    *,
    environ: Mapping[str, str] | None = None,
    argv: Sequence[str] | None = None,
) -> bool:
    """Return whether the current process must use isolated test databases."""

    environment = os.environ if environ is None else environ
    arguments = sys.argv if argv is None else argv
    if environment.get("PYTEST_CURRENT_TEST"):
        return True
    if environment.get("APP_ENV", "").strip().lower() in {
        "test",
        "testing",
        "pytest",
    }:
        return True
    if _truthy(environment.get("AI_MEDIA_OS_TESTING")):
        return True
    if arguments:
        executable = Path(arguments[0]).name.lower()
        if "pytest" in executable:
            return True
        if any(Path(value).name.lower() in {"pytest", "py.test"} for value in arguments[1:]):
            return True
    return False


def _sqlite_target_text(target: str | os.PathLike[str]) -> str | None:
    text = os.fspath(target).strip()
    lower = text.lower()
    if lower in {":memory:", "file::memory:"} or lower.startswith(
        "file::memory:?"
    ):
        return None

    if lower.startswith("sqlite"):
        marker = lower.find(":///")
        if marker < 0:
            if lower in {"sqlite://", "sqlite:///:memory:"}:
                return None
            raise ValueError(f"Unsupported SQLite URL: {text!r}")
        database = text[marker + 4 :]
        database = database.split("?", 1)[0]
        if database.lower() == ":memory:":
            return None
        if database.lower().startswith("file:"):
            return _sqlite_target_text(database)
        return unquote(database)

    if lower.startswith("file:"):
        parsed = urlsplit(text)
        if parsed.netloc not in {"", "localhost"}:
            raise ValueError(f"Remote SQLite file URI is not allowed: {text!r}")
        path = unquote(parsed.path)
        if not path:
            path = unquote(text[5:].split("?", 1)[0])
        if path == ":memory:":
            return None
        return path

    return text


def sqlite_target_path(
    target: str | os.PathLike[str],
    *,
    cwd: Path | None = None,
) -> Path | None:
    """Normalize raw paths, SQLite URLs, and SQLite file URIs."""

    text = _sqlite_target_text(target)
    if text is None:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (cwd or Path.cwd()) / path
    return path.resolve(strict=False)


def _sqlite_lexical_path(
    target: str | os.PathLike[str],
    *,
    cwd: Path | None = None,
) -> Path | None:
    """Return an absolute path without following a final symlink chain."""

    text = _sqlite_target_text(target)
    if text is None:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (cwd or Path.cwd()) / path
    return Path(os.path.abspath(path))


def _is_within(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def assert_database_target_allowed(
    target: str | os.PathLike[str],
    *,
    operation: str = "SQLite access",
    testing: bool | None = None,
    cwd: Path | None = None,
    production_database_path: Path | None = None,
    production_database_directory: Path | None = None,
    temporary_directory: Path = Path("/tmp"),
) -> Path | None:
    """Reject every non-temporary file-backed SQLite target during tests.

    The production directory check happens before the /tmp allow rule.  This
    ordering also rejects a hard link placed under /tmp when it aliases the
    production database inode.
    """

    if testing is None:
        testing = is_test_environment()
    lexical_path = _sqlite_lexical_path(target, cwd=cwd)
    path = sqlite_target_path(target, cwd=cwd)
    if not testing or path is None:
        return path

    if production_database_path is None or production_database_directory is None:
        from app.db.config import (
            PRODUCTION_DATABASE_DIRECTORY,
            PRODUCTION_SQLITE_PATH,
        )

        production_database_path = (
            production_database_path or PRODUCTION_SQLITE_PATH
        )
        production_database_directory = (
            production_database_directory or PRODUCTION_DATABASE_DIRECTORY
        )

    production_path = production_database_path.expanduser().resolve(strict=False)
    production_directory = production_database_directory.expanduser().resolve(
        strict=False
    )
    blocked_reason: str | None = None
    if (
        path == production_path
        or _is_within(path, production_directory)
        or (
            lexical_path is not None
            and _is_within(lexical_path, production_directory)
        )
    ):
        blocked_reason = "target is in the production database directory"
    elif path.exists() and production_path.exists():
        try:
            if os.path.samefile(path, production_path):
                blocked_reason = "target is a hard link to the production database"
        except OSError:
            blocked_reason = "production inode identity could not be verified"

    temporary_root = temporary_directory.resolve(strict=False)
    if blocked_reason is None and not _is_within(path, temporary_root):
        blocked_reason = "test SQLite targets must be under /tmp"

    if blocked_reason is not None:
        raise ProductionDatabaseAccessBlocked(
            f"{PRODUCTION_DATABASE_ACCESS_BLOCKED_DURING_TEST}: "
            f"{operation} blocked for {path}: {blocked_reason}"
        )
    return path
