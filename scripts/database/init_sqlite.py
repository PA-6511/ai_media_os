from __future__ import annotations

from app.db.base import Base
from app.db.config import DATABASE_BACKEND, DATABASE_URL
from app.db.models import EbookItem, StoreOffer  # noqa: F401
from app.db.session import get_engine


def main() -> int:
    if DATABASE_BACKEND != "sqlite":
        raise RuntimeError(
            "SQLite initializer refused because DATABASE_BACKEND "
            f"is {DATABASE_BACKEND!r}."
        )

    Base.metadata.create_all(bind=get_engine())

    print("SQLite database initialized.")
    print(f"DATABASE_URL={DATABASE_URL}")
    print("Tables:")
    for table_name in sorted(Base.metadata.tables):
        print(f"- {table_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
