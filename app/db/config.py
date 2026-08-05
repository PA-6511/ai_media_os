from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_DATABASE_DIRECTORY = (
    PROJECT_ROOT / "data" / "database"
).resolve(strict=False)
PRODUCTION_SQLITE_PATH = (
    PRODUCTION_DATABASE_DIRECTORY / "ebook_affiliate.db"
).resolve(strict=False)

# Backwards-compatible name retained for callers that treat the production
# SQLite file as the default database.
DEFAULT_SQLITE_PATH = PRODUCTION_SQLITE_PATH

DATABASE_BACKEND = os.getenv("DATABASE_BACKEND", "sqlite").strip().lower()

DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    DEFAULT_DATABASE_URL,
).strip()


def validate_database_config() -> None:
    allowed_backends = {"sqlite", "postgresql"}

    if DATABASE_BACKEND not in allowed_backends:
        raise ValueError(
            f"Unsupported DATABASE_BACKEND={DATABASE_BACKEND!r}. "
            f"Allowed values: {sorted(allowed_backends)}"
        )

    if DATABASE_BACKEND == "sqlite" and not DATABASE_URL.startswith("sqlite"):
        raise ValueError(
            "DATABASE_BACKEND is sqlite, but DATABASE_URL is not SQLite."
        )

    if DATABASE_BACKEND == "postgresql" and not DATABASE_URL.startswith(
        ("postgresql://", "postgresql+psycopg://")
    ):
        raise ValueError(
            "DATABASE_BACKEND is postgresql, but DATABASE_URL is not PostgreSQL."
        )
