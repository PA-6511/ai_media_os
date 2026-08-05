from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import EbookItem, StoreOffer


@dataclass(frozen=True)
class DashboardDateRange:
    today: date
    tomorrow: date
    week_end: date
    month_start: date
    month_end: date


def build_date_range(today: date | None = None) -> DashboardDateRange:
    base = today or date.today()
    tomorrow = base + timedelta(days=1)
    week_end = base + timedelta(days=(6 - base.weekday()))

    if base.month == 12:
        next_month = date(base.year + 1, 1, 1)
    else:
        next_month = date(base.year, base.month + 1, 1)

    return DashboardDateRange(
        today=base,
        tomorrow=tomorrow,
        week_end=week_end,
        month_start=date(base.year, base.month, 1),
        month_end=next_month - timedelta(days=1),
    )


class EbookDashboardService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_summary(
        self,
        *,
        today: date | None = None,
    ) -> dict[str, Any]:
        dates = build_date_range(today)

        active_condition = EbookItem.is_excluded.is_(False)

        today_count = self._count_items(
            active_condition,
            EbookItem.release_date == dates.today,
        )

        tomorrow_count = self._count_items(
            active_condition,
            EbookItem.release_date == dates.tomorrow,
        )

        this_week_count = self._count_items(
            active_condition,
            EbookItem.release_date >= dates.today,
            EbookItem.release_date <= dates.week_end,
        )

        this_month_count = self._count_items(
            active_condition,
            EbookItem.release_date >= dates.month_start,
            EbookItem.release_date <= dates.month_end,
        )

        missing_price_count = self._count_missing_price()
        missing_affiliate_count = self._count_missing_affiliate()
        excluded_count = self._count_items(EbookItem.is_excluded.is_(True))

        total_items = self.session.scalar(
            select(func.count()).select_from(EbookItem)
        ) or 0

        store_count = self.session.scalar(
            select(func.count(func.distinct(StoreOffer.store_name)))
        ) or 0

        latest_import_at = self.session.scalar(
            select(func.max(EbookItem.updated_at))
        )

        return {
            "status": "PASS",
            "dates": {
                "today": dates.today.isoformat(),
                "tomorrow": dates.tomorrow.isoformat(),
                "week_end": dates.week_end.isoformat(),
                "month_start": dates.month_start.isoformat(),
                "month_end": dates.month_end.isoformat(),
            },
            "cards": {
                "today_release": today_count,
                "tomorrow_release": tomorrow_count,
                "this_week_release": this_week_count,
                "this_month_release": this_month_count,
                "missing_price": missing_price_count,
                "missing_affiliate": missing_affiliate_count,
                "excluded": excluded_count,
            },
            "database": {
                "total_items": total_items,
                "store_count": store_count,
                "latest_import_at": (
                    latest_import_at.isoformat()
                    if latest_import_at is not None
                    else None
                ),
            },
        }

    def _count_items(self, *conditions: Any) -> int:
        statement = (
            select(func.count())
            .select_from(EbookItem)
            .where(*conditions)
        )

        return int(self.session.scalar(statement) or 0)

    def _count_missing_price(self) -> int:
        priced_item_ids = (
            select(StoreOffer.ebook_item_id)
            .where(
                or_(
                    StoreOffer.price_amount.is_not(None),
                    StoreOffer.price_yen.is_not(None),
                )
            )
            .distinct()
        )

        statement = (
            select(func.count())
            .select_from(EbookItem)
            .where(
                EbookItem.is_excluded.is_(False),
                EbookItem.id.not_in(priced_item_ids),
            )
        )

        return int(self.session.scalar(statement) or 0)

    def _count_missing_affiliate(self) -> int:
        affiliate_item_ids = (
            select(StoreOffer.ebook_item_id)
            .where(
                StoreOffer.affiliate_url.is_not(None),
                func.trim(StoreOffer.affiliate_url) != "",
            )
            .distinct()
        )

        statement = (
            select(func.count())
            .select_from(EbookItem)
            .where(
                EbookItem.is_excluded.is_(False),
                EbookItem.id.not_in(affiliate_item_ids),
            )
        )

        return int(self.session.scalar(statement) or 0)
