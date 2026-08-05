from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import DailySummarySelection, EbookItem
from app.services.daily_summary_selection_service import (
    AUTO_INCLUDED,
    HUMAN_EXCLUDED,
    HUMAN_INCLUDED,
    DailySummarySelectionService,
)


SUMMARY_DATE = date(2026, 8, 3)


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def add_item(session: Session, item_id: str = "item-1", **overrides) -> EbookItem:
    values = {
        "id": item_id,
        "source_name": "test",
        "source_item_id": item_id,
        "title": f"Title {item_id}",
        "release_date": SUMMARY_DATE,
        "is_excluded": False,
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "wordpress_status": "PUBLISHED",
        "wordpress_post_id": "301",
    }
    values.update(overrides)
    item = EbookItem(**values)
    session.add(item)
    session.flush()
    return item


@pytest.mark.parametrize(
    "overrides",
    [
        {"review_status": "IN_REVIEW"},
        {"wordpress_status": "DRAFT"},
        {"wordpress_post_id": None},
        {"is_excluded": True},
    ],
)
def test_auto_selection_requires_every_condition(session: Session, overrides) -> None:
    add_item(session, **overrides)
    service = DailySummarySelectionService(session)
    service.sync_auto_candidates(summary_date=SUMMARY_DATE)
    assert service.repository.list_for_date(SUMMARY_DATE) == []


def test_auto_selection_includes_eligible_item(session: Session) -> None:
    add_item(session)
    service = DailySummarySelectionService(session)
    service.sync_auto_candidates(summary_date=SUMMARY_DATE)
    selection = service.repository.list_for_date(SUMMARY_DATE)[0]
    assert selection.inclusion_state == AUTO_INCLUDED
    assert selection.selection_source == "AUTO"


@pytest.mark.parametrize("included,expected", [(True, HUMAN_INCLUDED), (False, HUMAN_EXCLUDED)])
def test_human_state_is_persisted_and_not_overwritten_by_auto(
    session: Session, included: bool, expected: str
) -> None:
    add_item(session)
    service = DailySummarySelectionService(session)
    service.set_human_selection(
        ebook_item_id="item-1",
        summary_date=SUMMARY_DATE,
        included=included,
        selected_by="operator",
    )
    service.sync_auto_candidates(summary_date=SUMMARY_DATE)
    selection = service.repository.get(
        ebook_item_id="item-1", summary_date=SUMMARY_DATE
    )
    assert selection is not None
    assert selection.inclusion_state == expected
    assert selection.selection_source == "HUMAN"


def test_duplicate_item_and_date_is_rejected(session: Session) -> None:
    add_item(session)
    session.add_all(
        [
            DailySummarySelection(
                ebook_item_id="item-1",
                summary_date=SUMMARY_DATE,
                inclusion_state=AUTO_INCLUDED,
                selection_source="AUTO",
                selected_by="auto",
            ),
            DailySummarySelection(
                ebook_item_id="item-1",
                summary_date=SUMMARY_DATE,
                inclusion_state=HUMAN_INCLUDED,
                selection_source="HUMAN",
                selected_by="operator",
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_repeated_checkbox_update_is_idempotent(session: Session) -> None:
    add_item(session)
    service = DailySummarySelectionService(session)
    first = service.set_human_selection(
        ebook_item_id="item-1",
        summary_date=SUMMARY_DATE,
        included=True,
        selected_by="operator",
    )
    second = service.set_human_selection(
        ebook_item_id="item-1",
        summary_date=SUMMARY_DATE,
        included=True,
        selected_by="operator",
    )
    assert first.changed is True
    assert second.changed is False
    assert len(session.scalars(select(DailySummarySelection)).all()) == 1