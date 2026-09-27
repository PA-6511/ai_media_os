from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.x_analytics import XAnalyticsMetricSnapshot


class XAnalyticsKpiRepositoryError(RuntimeError):
    pass


class XAnalyticsKpiRepository:
    """SELECT-only access to persisted X Analytics snapshots."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _assert_clean(self) -> None:
        if self.session.new or self.session.dirty or self.session.deleted:
            raise XAnalyticsKpiRepositoryError(
                "read-only KPI session contains pending mutations"
            )

    def list_snapshots(
        self,
        *,
        source: str | None = None,
        account_identifier: str | None = None,
    ) -> list[XAnalyticsMetricSnapshot]:
        self._assert_clean()
        statement = select(XAnalyticsMetricSnapshot)
        if source:
            statement = statement.where(
                XAnalyticsMetricSnapshot.source == source
            )
        if account_identifier:
            statement = statement.where(
                XAnalyticsMetricSnapshot.account_identifier
                == account_identifier
            )
        statement = statement.order_by(
            XAnalyticsMetricSnapshot.source,
            XAnalyticsMetricSnapshot.account_identifier,
            XAnalyticsMetricSnapshot.post_id,
            XAnalyticsMetricSnapshot.observed_at,
            XAnalyticsMetricSnapshot.id,
        )
        with self.session.no_autoflush:
            rows = list(self.session.scalars(statement))
        self._assert_clean()
        return rows