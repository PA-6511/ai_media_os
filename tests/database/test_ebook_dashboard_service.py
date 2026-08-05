from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.services.ebook_dashboard_service import (
    EbookDashboardService,
    build_date_range,
)


def create_session(tmp_path):
    database_path = tmp_path / "dashboard.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed(session: Session) -> None:
    today_item = EbookItem(
        source_name="test",
        source_item_id="TODAY-001",
        title="Today Book",
        release_date=date(2026, 7, 13),
        item_type="tankobon",
        is_excluded=False,
    )
    today_item.offers.append(
        StoreOffer(
            store_name="amazon",
            store_item_id="amazon:TODAY-001",
            price_yen=770,
            affiliate_url="https://example.com/affiliate",
        )
    )

    tomorrow_item = EbookItem(
        source_name="test",
        source_item_id="TOMORROW-001",
        title="Tomorrow Book",
        release_date=date(2026, 7, 14),
        item_type="tankobon",
        is_excluded=False,
    )
    tomorrow_item.offers.append(
        StoreOffer(
            store_name="rakuten_kobo",
            store_item_id="rakuten:TOMORROW-001",
            price_yen=None,
            affiliate_url=None,
        )
    )

    excluded_item = EbookItem(
        source_name="test",
        source_item_id="EXCLUDED-001",
        title="Excluded Book",
        release_date=date(2026, 7, 13),
        item_type="tankobon",
        is_excluded=True,
    )

    session.add_all(
        [
            today_item,
            tomorrow_item,
            excluded_item,
        ]
    )
    session.commit()


def test_build_date_range() -> None:
    result = build_date_range(date(2026, 7, 13))

    assert result.today == date(2026, 7, 13)
    assert result.tomorrow == date(2026, 7, 14)
    assert result.week_end == date(2026, 7, 19)
    assert result.month_start == date(2026, 7, 1)
    assert result.month_end == date(2026, 7, 31)


def test_dashboard_summary(tmp_path) -> None:
    with create_session(tmp_path) as session:
        seed(session)

        summary = EbookDashboardService(session).build_summary(
            today=date(2026, 7, 13)
        )

        assert summary["status"] == "PASS"
        assert summary["cards"]["today_release"] == 1
        assert summary["cards"]["tomorrow_release"] == 1
        assert summary["cards"]["this_week_release"] == 2
        assert summary["cards"]["this_month_release"] == 2
        assert summary["cards"]["missing_price"] == 1
        assert summary["cards"]["missing_affiliate"] == 1
        assert summary["cards"]["excluded"] == 1
        assert summary["database"]["total_items"] == 3
        assert summary["database"]["store_count"] == 2
