from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.gui.ebook_database_view_model import (
    EbookDatabaseQuery,
    EbookDatabaseViewModel,
    parse_optional_date,
)


def create_session(tmp_path):
    database_path = tmp_path / "gui_query.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed(session: Session) -> None:
    item = EbookItem(
        source_name="new_release_multistore",
        source_item_id="GUI-001",
        title="GUI Test Comic",
        normalized_title="GUI Test Comic",
        volume_label="第1巻",
        author_name="Author GUI",
        publisher_name="Publisher GUI",
        release_date=date(2026, 7, 20),
        item_type="tankobon",
        is_excluded=False,
    )

    item.offers.extend(
        [
            StoreOffer(
                store_name="amazon",
                store_item_id="amazon:GUI-001",
                price_yen=770,
                affiliate_url="https://example.com/affiliate",
            ),
            StoreOffer(
                store_name="rakuten_kobo",
                store_item_id="rakuten:GUI-001",
                price_yen=750,
            ),
        ]
    )

    session.add(item)
    session.commit()


def test_parse_optional_date() -> None:
    assert parse_optional_date("") is None
    assert parse_optional_date("2026-07-20") == date(2026, 7, 20)


def test_parse_optional_date_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        parse_optional_date("2026/07/20")


def test_view_model_flattens_database_items(tmp_path) -> None:
    with create_session(tmp_path) as session:
        seed(session)

        rows = EbookDatabaseViewModel(session).search(
            EbookDatabaseQuery(keyword="GUI")
        )

        assert len(rows) == 1

        row = rows[0]

        assert row["source_item_id"] == "GUI-001"
        assert row["title"] == "GUI Test Comic"
        assert row["store_names"] == "amazon, rakuten_kobo"
        assert row["prices"] == "amazon:770, rakuten_kobo:750"
        assert row["affiliate_count"] == 1


def test_view_model_filters_by_date(tmp_path) -> None:
    with create_session(tmp_path) as session:
        seed(session)

        rows = EbookDatabaseViewModel(session).search(
            EbookDatabaseQuery(
                release_date_from="2026-07-20",
                release_date_to="2026-07-20",
            )
        )

        assert len(rows) == 1


def test_view_model_filters_out_nonmatching_date(tmp_path) -> None:
    with create_session(tmp_path) as session:
        seed(session)

        rows = EbookDatabaseViewModel(session).search(
            EbookDatabaseQuery(
                release_date_from="2026-07-21",
            )
        )

        assert rows == []


def test_view_model_includes_workflow_statuses(tmp_path) -> None:
    with create_session(tmp_path) as session:
        seed(session)

        rows = EbookDatabaseViewModel(session).search(
            EbookDatabaseQuery(keyword="GUI")
        )

        assert len(rows) == 1

        row = rows[0]

        assert row["workflow_status"] == "NEW"
        assert row["wordpress_status"] == "NOT_CREATED"
        assert row["x_status"] == "NOT_CREATED"
        assert row["affiliate_status"] == "UNCHECKED"
        assert row["image_status"] == "UNCHECKED"
        assert row["review_status"] == "NOT_REVIEWED"
        assert row["publish_ready"] is False
