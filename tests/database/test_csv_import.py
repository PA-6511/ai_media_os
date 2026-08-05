from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.csv_import_service import CsvImportService


def test_csv_import_dry_run_does_not_persist(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        "source_name,source_item_id,title,store_name,"
        "store_item_id,price\n"
        "rakuten,RK-001,Test Book,rakuten,RK-001,770\n",
        encoding="utf-8",
    )

    with Session(engine) as session:
        summary = CsvImportService(session).import_file(
            csv_path,
            dry_run=True,
        )

        assert summary.processed == 1
        assert summary.created == 1

    with Session(engine) as session:
        item_count = session.scalar(
            select(func.count()).select_from(EbookItem)
        )
        offer_count = session.scalar(
            select(func.count()).select_from(StoreOffer)
        )

    assert item_count == 0
    assert offer_count == 0


def test_csv_import_execute_persists_and_updates(tmp_path: Path) -> None:
    database_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)

    csv_path = tmp_path / "input.csv"
    csv_path.write_text(
        "source_name,source_item_id,title,store_name,"
        "store_item_id,price\n"
        "rakuten,RK-001,Test Book,rakuten,RK-001,770\n",
        encoding="utf-8",
    )

    with Session(engine) as session:
        first = CsvImportService(session).import_file(
            csv_path,
            dry_run=False,
        )

        assert first.created == 1
        assert first.offer_created == 1

    csv_path.write_text(
        "source_name,source_item_id,title,store_name,"
        "store_item_id,price\n"
        "rakuten,RK-001,Test Book Updated,rakuten,RK-001,660\n",
        encoding="utf-8",
    )

    with Session(engine) as session:
        second = CsvImportService(session).import_file(
            csv_path,
            dry_run=False,
        )

        assert second.updated == 1
        assert second.offer_updated == 1

    with Session(engine) as session:
        items = session.scalars(select(EbookItem)).all()
        offers = session.scalars(select(StoreOffer)).all()

        assert len(items) == 1
        assert len(offers) == 1
        assert items[0].title == "Test Book Updated"
    assert offers[0].price_yen == 660

    with Session(engine) as session:
        third = CsvImportService(session).import_file(
            csv_path,
            dry_run=False,
        )

    assert third.created == 0
    assert third.updated == 0
    assert third.unchanged == 1
    assert third.offer_created == 0
    assert third.offer_updated == 0
    assert third.offer_unchanged == 1
