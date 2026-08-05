from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models.ebook import EbookItem
from app.db.access_guard import (
    ProductionDatabaseAccessBlocked,
    assert_database_target_allowed,
)
from app.db.config import PRODUCTION_SQLITE_PATH
from app.services.amazon_manual_link_service import AmazonManualLinkError
from app.services.amazon_manual_offer_service import AmazonManualOfferService


DEFAULT_DATABASE_PATH = PRODUCTION_SQLITE_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon暫定アフィリエイトリンクをstore_offersへ保存します。",
    )
    parser.add_argument(
        "--ebook-item-id",
        required=True,
        help="対象ebook_items.id",
    )
    parser.add_argument(
        "--asin",
        required=True,
        help="Amazon ASIN（10文字）",
    )
    parser.add_argument(
        "--tracking-id",
        required=True,
        help="AmazonアソシエイトのトラッキングID",
    )
    parser.add_argument(
        "--database",
        default=str(DEFAULT_DATABASE_PATH),
        help="SQLite DBパス",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="指定した場合のみDBへ確定保存",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        database_path = assert_database_target_allowed(
            args.database,
            operation="manual Amazon offer CLI",
        )
    except ProductionDatabaseAccessBlocked as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    if database_path is None:
        print("ERROR: file-backed database required", file=sys.stderr)
        return 1

    if not database_path.is_file():
        print(
            f"ERROR: database not found: {database_path}",
            file=sys.stderr,
        )
        return 1

    engine = create_engine(f"sqlite+pysqlite:///{database_path}")

    try:
        with Session(engine) as session:
            item = session.scalar(
                select(EbookItem).where(
                    EbookItem.id == args.ebook_item_id,
                )
            )

            if item is None:
                print(
                    f"ERROR: ebook item not found: {args.ebook_item_id}",
                    file=sys.stderr,
                )
                return 1

            service = AmazonManualOfferService(session)

            result = service.save(
                ebook_item_id=item.id,
                asin=args.asin,
                tracking_id=args.tracking_id,
            )

            print(f"title={item.title}")
            print(f"ebook_item_id={result.ebook_item_id}")
            print(f"asin={result.asin}")
            print(f"product_url={result.product_url}")
            print(f"affiliate_url={result.affiliate_url}")
            print(f"offer_id={result.offer_id}")

            if args.commit:
                session.commit()
                print("result=COMMITTED")
            else:
                session.rollback()
                print("result=DRY_RUN_NOT_SAVED")

        return 0

    except AmazonManualLinkError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    except Exception as exc:
        print(
            f"ERROR: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
