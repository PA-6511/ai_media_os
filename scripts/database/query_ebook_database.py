from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.db.config import DATABASE_BACKEND
from app.db.session import SessionLocal
from app.services.ebook_query_service import (
    EbookQueryService,
    EbookSearchFilters,
)


def parse_date(value: str | None):
    if value is None:
        return None

    return datetime.strptime(value, "%Y-%m-%d").date()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query the ebook operational database."
    )

    parser.add_argument("--keyword")
    parser.add_argument("--release-date-from")
    parser.add_argument("--release-date-to")
    parser.add_argument("--item-type")
    parser.add_argument("--store-name")
    parser.add_argument(
        "--include-excluded",
        action="store_true",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if DATABASE_BACKEND not in {"sqlite", "postgresql"}:
        raise RuntimeError(
            f"Unsupported database backend: {DATABASE_BACKEND}"
        )

    filters = EbookSearchFilters(
        keyword=args.keyword,
        release_date_from=parse_date(args.release_date_from),
        release_date_to=parse_date(args.release_date_to),
        item_type=args.item_type,
        store_name=args.store_name,
        excluded=None if args.include_excluded else False,
        limit=args.limit,
        offset=args.offset,
    )

    with SessionLocal() as session:
        result = EbookQueryService(session).search(filters)

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
