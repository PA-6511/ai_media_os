from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from scripts.database.backfill_store_offer_metadata import run_backfill


def _setup(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'backfill.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = EbookItem(
            id="item-existing",
            source_name="test",
            source_item_id="item-existing",
            title="既存作品 第1巻",
        )
        session.add(item)
        session.commit()
    return engine


def test_backfill_defaults_dry_run_executes_and_then_reports_unchanged(tmp_path: Path) -> None:
    engine = _setup(tmp_path)
    csv_path = tmp_path / "backfill.csv"
    csv_path.write_text(
        "item_id,title,store_code,store_item_id,price,currency,item_url,"
        "affiliate_url,observed_at,source_row_sha256\n"
        "item-existing,既存作品 第1巻,rakuten_kobo,RK-1,0,,"
        "https://product.example/rk,https://affiliate.example/rk,"
        "2026-07-31T00:00:00Z," + ("b" * 64) + "\n"
        "missing,不存在,dmm,DMM-1,,,,,,\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        dry = run_backfill(session, csv_path)
        assert dry.mode == "DRY_RUN"
        assert dry.database_write_performed is False
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
        executed = run_backfill(session, csv_path, execute=True)
        assert executed.created == 1
        assert executed.missing_item == 1
        assert executed.database_write_performed is True
    with Session(engine) as session:
        again = run_backfill(session, csv_path)
        assert again.unchanged == 1
        offer = session.scalar(select(StoreOffer))
        assert offer.price_yen == 0
        assert offer.currency == "JPY"


def test_backfill_title_mismatch_is_review_and_failure_rolls_back(tmp_path: Path) -> None:
    engine = _setup(tmp_path)
    csv_path = tmp_path / "review.csv"
    csv_path.write_text(
        "item_id,title,store_code,store_item_id,price\n"
        "item-existing,まったく異なる題名,amazon,B000000001,100\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        result = run_backfill(session, csv_path, execute=True)
        assert result.review == 1
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
    csv_path.write_text(
        "item_id,title,store_code,store_item_id,price\n"
        "item-existing,既存作品 第1巻,amazon,B000000001,-1\n",
        encoding="utf-8",
    )
    with Session(engine) as session:
        with pytest.raises(ValueError):
            run_backfill(session, csv_path, execute=True)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
