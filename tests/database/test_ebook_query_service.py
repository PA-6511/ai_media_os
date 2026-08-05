from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.ebook_query_service import (
    EbookQueryService,
    EbookSearchFilters,
)


def seed_database(session: Session) -> None:
    first = EbookItem(
        source_name="new_release_multistore",
        source_item_id="ITEM-001",
        title="Test Comic First",
        normalized_title="Test Comic First",
        author_name="Author A",
        publisher_name="Publisher A",
        release_date=date(2026, 7, 17),
        item_type="tankobon",
        is_excluded=False,
    )

    first.offers.append(
        StoreOffer(
            store_name="amazon",
            store_item_id="amazon:ITEM-001",
            price_yen=770,
        )
    )

    second = EbookItem(
        source_name="new_release_multistore",
        source_item_id="ITEM-002",
        title="Test Novel Second",
        normalized_title="Test Novel Second",
        author_name="Author B",
        publisher_name="Publisher B",
        release_date=date(2026, 7, 18),
        item_type="general_book",
        is_excluded=False,
    )

    second.offers.append(
        StoreOffer(
            store_name="rakuten_kobo",
            store_item_id="rakuten_kobo:ITEM-002",
            price_yen=880,
        )
    )

    excluded = EbookItem(
        source_name="new_release_multistore",
        source_item_id="ITEM-003",
        title="Excluded Comic",
        normalized_title="Excluded Comic",
        release_date=date(2026, 7, 19),
        item_type="tankobon",
        is_excluded=True,
    )

    session.add_all([first, second, excluded])
    session.commit()


def create_test_session(tmp_path):
    database_path = tmp_path / "query_test.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_search_returns_non_excluded_items(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(session).search(
            EbookSearchFilters()
        )

        assert result["status"] == "PASS"
        assert result["count"] == 2
        assert {
            item["source_item_id"]
            for item in result["items"]
        } == {"ITEM-001", "ITEM-002"}


def test_search_by_keyword(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(session).search(
            EbookSearchFilters(keyword="Comic")
        )

        assert result["count"] == 1
        assert result["items"][0]["source_item_id"] == "ITEM-001"


def test_search_by_store(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(session).search(
            EbookSearchFilters(store_name="rakuten_kobo")
        )

        assert result["count"] == 1
        assert result["items"][0]["source_item_id"] == "ITEM-002"
        assert result["items"][0]["offers"][0]["price_yen"] == 880


def test_search_by_date_and_type(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(session).search(
            EbookSearchFilters(
                release_date_from=date(2026, 7, 17),
                release_date_to=date(2026, 7, 17),
                item_type="tankobon",
            )
        )

        assert result["count"] == 1
        assert result["items"][0]["source_item_id"] == "ITEM-001"


def test_get_by_source_identity(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(
            session
        ).get_by_source_identity(
            source_name="new_release_multistore",
            source_item_id="ITEM-001",
        )

        assert result is not None
        assert result["title"] == "Test Comic First"
        assert result["offers"][0]["store_name"] == "amazon"


def test_serialized_item_contains_workflow_fields(tmp_path) -> None:
    with create_test_session(tmp_path) as session:
        seed_database(session)

        result = EbookQueryService(session).search(
            EbookSearchFilters(keyword="First")
        )

        assert result["count"] == 1

        item = result["items"][0]

        assert item["workflow_status"] == "NEW"
        assert item["wordpress_status"] == "NOT_CREATED"
        assert item["x_status"] == "NOT_CREATED"
        assert item["affiliate_status"] == "UNCHECKED"
        assert item["image_status"] == "UNCHECKED"
        assert item["review_status"] == "NOT_REVIEWED"
        assert item["publish_ready"] is False
