from __future__ import annotations

import json
import re
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import and_, distinct, func, or_, select
from sqlalchemy.orm import Session

from analytics.x_core_advisory.store import atomic_write_bytes
from app.services.x_analytics_kpi_service import (
    DEFAULT_TIMEZONE,
    XAnalyticsKpiError,
    XAnalyticsKpiService,
    canonical_report_json,
    render_kpi_report_text,
    resolve_period,
)
from app.services.x_analytics_api_budget_service import (
    BASE_MONTHLY_LIMIT_USD,
    XAnalyticsApiBudgetService,
)
from app.db.models import EbookItem, WorkflowHistory
from app.db.models.sale_roundup import (
    SaleCampaign,
    SaleMetricSnapshot,
    SaleOffer,
)


DEFAULT_REPORT_DIR = Path(__file__).resolve().parents[1] / "data" / "reports" / "x_analytics"


@dataclass(frozen=True)
class PeriodicWindows:
    strategy: str
    reference_at: datetime
    current_start: datetime
    current_end: datetime
    previous_start: datetime
    previous_end: datetime
    period_key: str


def _aware(value: datetime, timezone_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=ZoneInfo(timezone_name))
    return value.astimezone(ZoneInfo(timezone_name))


def subtract_calendar_month(value: datetime) -> datetime:
    year = value.year if value.month > 1 else value.year - 1
    month = value.month - 1 if value.month > 1 else 12
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def resolve_periodic_windows(
    report_type: str,
    *,
    period_mode: str,
    timezone_name: str = DEFAULT_TIMEZONE,
    reference_at: datetime,
    period_key: str | None = None,
) -> PeriodicWindows:
    zone = ZoneInfo(timezone_name)
    reference = _aware(reference_at, timezone_name)
    if period_mode == "rolling":
        if period_key:
            raise XAnalyticsKpiError(
                "period_key is only valid for calendar reports"
            )
        current_end = reference
        if report_type == "weekly":
            current_start = current_end - timedelta(days=7)
            previous_start = current_start - timedelta(days=7)
        elif report_type == "monthly":
            current_start = subtract_calendar_month(current_end)
            previous_start = subtract_calendar_month(current_start)
        else:
            raise XAnalyticsKpiError("report_type must be weekly or monthly")
        normalized = "rolling-" + current_end.strftime("%Y%m%dT%H%M%S%z")
        return PeriodicWindows(
            strategy="rolling",
            reference_at=reference,
            current_start=current_start,
            current_end=current_end,
            previous_start=previous_start,
            previous_end=current_start,
            period_key=normalized,
        )
    if period_mode != "calendar":
        raise XAnalyticsKpiError("period_mode must be rolling or calendar")
    selected_key = period_key or default_period_key(
        report_type, timezone_name=timezone_name, now=reference
    )
    start_text, end_text, normalized = resolve_periodic_range(
        report_type, selected_key, timezone_name
    )
    current_start = datetime.combine(
        date.fromisoformat(start_text), datetime.min.time(), tzinfo=zone
    )
    current_end = datetime.combine(
        date.fromisoformat(end_text), datetime.min.time(), tzinfo=zone
    )
    if report_type == "weekly":
        previous_start = current_start - timedelta(days=7)
    else:
        previous_start = current_start.replace(day=1) - timedelta(days=1)
        previous_start = previous_start.replace(day=1)
    return PeriodicWindows(
        strategy="calendar",
        reference_at=reference,
        current_start=current_start,
        current_end=current_end,
        previous_start=previous_start,
        previous_end=current_start,
        period_key=normalized,
    )


def resolve_periodic_range(
    report_type: str,
    period_key: str,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> tuple[str, str, str]:
    if report_type == "weekly":
        matched = re.fullmatch(r"(\d{4})-?W(\d{2})", period_key.upper())
        if matched is None:
            raise XAnalyticsKpiError("weekly period must use YYYYWww or YYYY-Www")
        start_date = date.fromisocalendar(
            int(matched.group(1)), int(matched.group(2)), 1
        )
        end_date = start_date + timedelta(days=7)
        normalized = f"{matched.group(1)}W{matched.group(2)}"
    elif report_type == "monthly":
        matched = re.fullmatch(r"(\d{4})-?(\d{2})", period_key)
        if matched is None:
            raise XAnalyticsKpiError("monthly period must use YYYYMM or YYYY-MM")
        year, month = int(matched.group(1)), int(matched.group(2))
        start_date = date(year, month, 1)
        end_date = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        normalized = f"{year:04d}{month:02d}"
    else:
        raise XAnalyticsKpiError("report_type must be weekly or monthly")
    ZoneInfo(timezone_name)
    return start_date.isoformat(), end_date.isoformat(), normalized


def default_period_key(
    report_type: str,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    now: datetime | None = None,
) -> str:
    local_date = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(timezone_name)
    ).date()
    if report_type == "weekly":
        year, week, _ = local_date.isocalendar()
        return f"{year:04d}W{week:02d}"
    if report_type == "monthly":
        return local_date.strftime("%Y%m")
    raise XAnalyticsKpiError("report_type must be weekly or monthly")


def previous_complete_period_key(
    report_type: str,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    now: datetime | None = None,
) -> str:
    local_date = (now or datetime.now(timezone.utc)).astimezone(
        ZoneInfo(timezone_name)
    ).date()
    if report_type == "weekly":
        previous_week = local_date - timedelta(days=7)
        year, week, _ = previous_week.isocalendar()
        return f"{year:04d}W{week:02d}"
    if report_type == "monthly":
        previous_month = local_date.replace(day=1) - timedelta(days=1)
        return previous_month.strftime("%Y%m")
    raise XAnalyticsKpiError("report_type must be weekly or monthly")


def _na(reason: str, **details: Any) -> dict[str, Any]:
    return {"value": None, "reason": reason, **details}


def _count_result(value: int, *, basis: str) -> dict[str, Any]:
    return {"value": int(value), "reason": None, "basis": basis}


def _x_post_success_count(
    repository_root: Path | None,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    if repository_root is None:
        return _na("repository_root_not_provided")
    roots = (
        repository_root / "exchange/evidence/ebook_autonomy/x_posts",
        repository_root / "exchange/approved/x_posts",
    )
    available = [root for root in roots if root.is_dir()]
    if not available:
        return _na("x_post_evidence_not_available")
    post_ids: set[str] = set()
    invalid_count = 0
    for root in available:
        for path in sorted(root.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                post_id = str(
                    payload.get("x_post_id") or payload.get("post_id") or ""
                ).strip()
                posted_at = datetime.fromisoformat(
                    str(payload.get("posted_at") or "").replace("Z", "+00:00")
                )
                if posted_at.tzinfo is None or posted_at.utcoffset() is None:
                    raise ValueError("timezone missing")
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                invalid_count += 1
                continue
            if post_id and start <= posted_at.astimezone(timezone.utc) < end:
                post_ids.add(post_id)
    return {
        "value": len(post_ids),
        "reason": None,
        "basis": "unique_x_post_id_from_posted_evidence",
        "invalid_evidence_count": invalid_count,
    }



def _number_result(
    value: int | float,
    *,
    basis: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "value": value,
        "reason": None,
        "basis": basis,
        **details,
    }


def collect_business_metrics(
    session: Session,
    *,
    start: datetime,
    end: datetime,
) -> dict[str, Any]:
    """Collect ebook business KPIs without inventing unavailable revenue data."""

    registered_filters = (
        EbookItem.created_at >= start,
        EbookItem.created_at < end,
    )

    registered_items = session.scalar(
        select(
            func.count(
                distinct(EbookItem.id)
            )
        ).where(
            *registered_filters
        )
    ) or 0

    official_cover_ready = session.scalar(
        select(
            func.count(
                distinct(EbookItem.id)
            )
        ).where(
            *registered_filters,
            EbookItem.cover_status == "AUTO_ALLOWED",
            EbookItem.image_status == "READY",
        )
    ) or 0

    wordpress_draft_current = session.scalar(
        select(
            func.count(
                distinct(EbookItem.id)
            )
        ).where(
            *registered_filters,
            EbookItem.wordpress_status == "DRAFT",
        )
    ) or 0

    wordpress_published_current = session.scalar(
        select(
            func.count(
                distinct(EbookItem.id)
            )
        ).where(
            *registered_filters,
            EbookItem.wordpress_status == "PUBLISHED",
        )
    ) or 0

    campaign_time_filters = (
        func.datetime(SaleCampaign.imported_at)
        >= func.datetime(start.isoformat()),
        func.datetime(SaleCampaign.imported_at)
        < func.datetime(end.isoformat()),
    )

    sale_campaigns = session.scalar(
        select(
            func.count(
                distinct(SaleCampaign.id)
            )
        ).where(
            *campaign_time_filters
        )
    ) or 0

    sale_offers = session.scalar(
        select(
            func.count(
                distinct(SaleOffer.id)
            )
        )
        .join(
            SaleCampaign,
            SaleOffer.campaign_id == SaleCampaign.id,
        )
        .where(
            *campaign_time_filters
        )
    ) or 0

    metric_filters = (
        SaleMetricSnapshot.attribution_basis == "exact_post",
        SaleMetricSnapshot.currency == "JPY",
        func.datetime(SaleMetricSnapshot.posted_at)
        >= func.datetime(start.isoformat()),
        func.datetime(SaleMetricSnapshot.posted_at)
        < func.datetime(end.isoformat()),
    )

    attributed_post_count = session.scalar(
        select(
            func.count(
                distinct(SaleMetricSnapshot.post_id)
            )
        ).where(
            *metric_filters
        )
    ) or 0

    metric_basis = (
        "latest_cumulative_exact_post_jpy_snapshot_"
        "for_posts_posted_in_period"
    )

    def summed_metric(
        column: Any,
        *,
        integer: bool,
    ) -> dict[str, Any]:
        observed_post_count = session.scalar(
            select(
                func.count(
                    distinct(SaleMetricSnapshot.post_id)
                )
            ).where(
                *metric_filters,
                column.is_not(None),
            )
        ) or 0

        if attributed_post_count == 0:
            return _na(
                "no_attributed_data",
                basis=metric_basis,
                attributed_post_count=0,
                observed_post_count=0,
            )

        if observed_post_count == 0:
            return _na(
                "metric_not_observed",
                basis=metric_basis,
                attributed_post_count=int(
                    attributed_post_count
                ),
                observed_post_count=0,
            )

        total = session.scalar(
            select(
                func.sum(column)
            ).where(
                *metric_filters,
                column.is_not(None),
            )
        )

        if total is None:
            return _na(
                "metric_not_observed",
                basis=metric_basis,
                attributed_post_count=int(
                    attributed_post_count
                ),
                observed_post_count=int(
                    observed_post_count
                ),
            )

        value: int | float
        if integer:
            value = int(total)
        else:
            value = float(total)

        return _number_result(
            value,
            basis=metric_basis,
            attributed_post_count=int(
                attributed_post_count
            ),
            observed_post_count=int(
                observed_post_count
            ),
        )

    attributed_clicks = summed_metric(
        SaleMetricSnapshot.clicks,
        integer=True,
    )
    attributed_orders = summed_metric(
        SaleMetricSnapshot.orders,
        integer=True,
    )
    attributed_revenue = summed_metric(
        SaleMetricSnapshot.order_revenue,
        integer=False,
    )
    attributed_fee = summed_metric(
        SaleMetricSnapshot.referral_fee,
        integer=False,
    )

    if registered_items:
        cover_rate = _number_result(
            official_cover_ready / registered_items,
            basis=(
                "current_cover_status_of_items_"
                "created_in_period_at_report_generation"
            ),
            numerator=int(official_cover_ready),
            denominator=int(registered_items),
        )
    else:
        cover_rate = _na(
            "no_registered_items",
            basis=(
                "current_cover_status_of_items_"
                "created_in_period_at_report_generation"
            ),
            numerator=0,
            denominator=0,
        )

    clicks_value = attributed_clicks.get("value")
    orders_value = attributed_orders.get("value")

    if clicks_value is None or orders_value is None:
        attributed_cvr = _na(
            "attributed_clicks_or_orders_unavailable",
            basis="attributed_orders_divided_by_attributed_clicks",
        )
    elif int(clicks_value) == 0:
        attributed_cvr = _na(
            "zero_attributed_clicks",
            basis="attributed_orders_divided_by_attributed_clicks",
            numerator=int(orders_value),
            denominator=0,
        )
    else:
        attributed_cvr = _number_result(
            float(orders_value) / float(clicks_value),
            basis="attributed_orders_divided_by_attributed_clicks",
            numerator=int(orders_value),
            denominator=int(clicks_value),
        )

    return {
        "registered_items": _count_result(
            registered_items,
            basis="unique_ebook_item_id_created_at_in_period",
        ),
        "sale_campaigns_imported": _count_result(
            sale_campaigns,
            basis="unique_sale_campaign_id_imported_at_in_period",
        ),
        "sale_offers_imported": _count_result(
            sale_offers,
            basis=(
                "unique_sale_offer_id_whose_campaign_"
                "was_imported_in_period"
            ),
        ),
        "registered_items_official_cover_ready_current": (
            _count_result(
                official_cover_ready,
                basis=(
                    "current_auto_allowed_ready_cover_of_"
                    "items_created_in_period"
                ),
            )
        ),
        "registered_item_cover_rate_current": cover_rate,
        "registered_items_wordpress_draft_current": (
            _count_result(
                wordpress_draft_current,
                basis=(
                    "current_wordpress_status_of_"
                    "items_created_in_period"
                ),
            )
        ),
        "registered_items_wordpress_published_current": (
            _count_result(
                wordpress_published_current,
                basis=(
                    "current_wordpress_status_of_"
                    "items_created_in_period"
                ),
            )
        ),
        "attributed_post_count": _count_result(
            attributed_post_count,
            basis=(
                "unique_exact_post_jpy_metric_post_"
                "posted_in_period"
            ),
        ),
        "attributed_clicks": attributed_clicks,
        "attributed_orders": attributed_orders,
        "attributed_order_revenue_jpy": attributed_revenue,
        "attributed_referral_fee_jpy": attributed_fee,
        "attributed_cvr": attributed_cvr,
    }


def collect_operational_metrics(
    session: Session,
    *,
    start: datetime,
    end: datetime,
    repository_root: Path | None,
    include_current_pending: bool,
) -> dict[str, Any]:
    new_release_count = session.scalar(
        select(func.count(distinct(EbookItem.id))).where(
            EbookItem.created_at >= start,
            EbookItem.created_at < end,
        )
    ) or 0
    wordpress_published = session.scalar(
        select(func.count(distinct(WorkflowHistory.ebook_item_id))).where(
            WorkflowHistory.field_name == "wordpress_status",
            func.upper(func.coalesce(WorkflowHistory.after_value, ""))
            == "PUBLISHED",
            WorkflowHistory.changed_at >= start,
            WorkflowHistory.changed_at < end,
        )
    ) or 0
    failure_events = session.scalar(
        select(func.count(distinct(WorkflowHistory.id))).where(
            WorkflowHistory.changed_at >= start,
            WorkflowHistory.changed_at < end,
            or_(
                and_(
                    WorkflowHistory.field_name.in_(
                        ("workflow_status", "wordpress_status", "x_status")
                    ),
                    func.upper(func.coalesce(WorkflowHistory.after_value, ""))
                    == "ERROR",
                ),
                and_(
                    WorkflowHistory.field_name == "last_error",
                    func.trim(func.coalesce(WorkflowHistory.after_value, ""))
                    != "",
                ),
            ),
        )
    ) or 0
    pending = (
        _count_result(
            session.scalar(
                select(func.count(distinct(EbookItem.id))).where(
                    or_(
                        EbookItem.wordpress_status.in_(("DRAFT", "SCHEDULED")),
                        EbookItem.x_status == "DRAFT",
                    )
                )
            )
            or 0,
            basis="current_status_snapshot_at_report_generation",
        )
        if include_current_pending
        else _na(
            "historical_pending_snapshot_unavailable",
            basis="not_inferred_from_current_state",
        )
    )
    return {
        "new_release_registrations": _count_result(
            new_release_count,
            basis="unique_ebook_item_id_created_at_in_period",
        ),
        "wordpress_published": _count_result(
            wordpress_published,
            basis="unique_ebook_item_id_with_wordpress_status_published_event",
        ),
        "x_post_success": _x_post_success_count(repository_root, start, end),
        "failure_events": _count_result(
            failure_events,
            basis="unique_workflow_history_error_event_id",
        ),
        "current_pending": pending,
    }


def _compare_value(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_value = current.get("value")
    previous_value = previous.get("value")
    if current_value is None:
        return _na("current_value_unavailable")
    if previous_value is None:
        return _na("previous_value_unavailable")
    delta = current_value - previous_value
    return {
        "value": delta,
        "reason": None,
        "current": current_value,
        "previous": previous_value,
        "percent_change": (
            None if previous_value == 0 else (delta / previous_value)
        ),
        "percent_change_reason": (
            "previous_value_zero" if previous_value == 0 else None
        ),
    }


def _kpi_comparison(
    current: dict[str, Any], previous: dict[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in sorted(set(current) | set(previous)):
        current_metric = current.get(name, {})
        previous_metric = previous.get(name, {})
        result[name] = _compare_value(current_metric, previous_metric)
    return result


def _post_type_comparison(
    current_rows: Sequence[dict[str, Any]],
    previous_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    current = {
        str(row.get("group", {}).get("post_type", "unknown")): row
        for row in current_rows
        if isinstance(row, dict)
    }
    previous = {
        str(row.get("group", {}).get("post_type", "unknown")): row
        for row in previous_rows
        if isinstance(row, dict)
    }
    return [
        {
            "post_type": name,
            "current_post_count": int(current.get(name, {}).get("post_count", 0)),
            "previous_post_count": int(previous.get(name, {}).get("post_count", 0)),
            "kpis": _kpi_comparison(
                current.get(name, {}).get("kpis", {}),
                previous.get(name, {}).get("kpis", {}),
            ),
        }
        for name in sorted(set(current) | set(previous))
    ]


def build_periodic_report(
    session: Session,
    *,
    report_type: str,
    period_key: str | None = None,
    period_mode: str = "calendar",
    reference_at: datetime | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
    mode: str = "posted_latest",
    axes: Sequence[str] = (
        "post_type",
        "time_slot",
        "has_cover",
        "store",
    ),
    ranking_metric: str = "reach",
    source: str | None = None,
    generated_at: datetime | None = None,
    repository_root: Path | None = None,
) -> dict[str, Any]:
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    )
    windows = resolve_periodic_windows(
        report_type,
        period_mode=period_mode,
        timezone_name=timezone_name,
        reference_at=reference_at or generated,
        period_key=period_key,
    )
    current_period = resolve_period(
        timezone_name=timezone_name,
        start=windows.current_start.isoformat(),
        end=windows.current_end.isoformat(),
        as_of=min(generated, windows.current_end.astimezone(timezone.utc)).isoformat(),
    )
    previous_period = resolve_period(
        timezone_name=timezone_name,
        start=windows.previous_start.isoformat(),
        end=windows.previous_end.isoformat(),
        as_of=windows.previous_end.isoformat(),
    )
    service = XAnalyticsKpiService(session)
    report = service.build_report(
        period=current_period,
        mode=mode,
        axes=axes,
        ranking_metric=ranking_metric,
        source=source,
    )
    try:
        report["coverage"]["api_collection_budget"] = (
            XAnalyticsApiBudgetService(session).current_status(
                now=generated,
                base_limit=BASE_MONTHLY_LIMIT_USD,
            )
        )
    except Exception:
        report["coverage"]["api_collection_budget"] = {
            "status": "unavailable",
            "reason": "budget_schema_or_state_unavailable",
            "month_boundary_timezone": "UTC",
            "x_actual_billing_status": "not_verified",
        }
    previous = service.build_report(
        period=previous_period,
        mode=mode,
        axes=axes,
        ranking_metric=ranking_metric,
        source=source,
    )
    current_post_types = service.build_report(
        period=current_period,
        mode=mode,
        axes=("post_type",),
        ranking_metric=ranking_metric,
        source=source,
    )
    previous_post_types = service.build_report(
        period=previous_period,
        mode=mode,
        axes=("post_type",),
        ranking_metric=ranking_metric,
        source=source,
    )
    current_stores = service.build_report(
        period=current_period,
        mode=mode,
        axes=("store",),
        ranking_metric=ranking_metric,
        source=source,
    )
    current_time_slots = service.build_report(
        period=current_period,
        mode=mode,
        axes=("time_slot",),
        ranking_metric=ranking_metric,
        source=source,
    )
    current_has_cover = service.build_report(
        period=current_period,
        mode=mode,
        axes=("has_cover",),
        ranking_metric=ranking_metric,
        source=source,
    )
    current_operations = collect_operational_metrics(
        session,
        start=current_period.start,
        end=current_period.end,
        repository_root=repository_root,
        include_current_pending=True,
    )
    previous_operations = collect_operational_metrics(
        session,
        start=previous_period.start,
        end=previous_period.end,
        repository_root=repository_root,
        include_current_pending=False,
    )
    current_business = collect_business_metrics(
        session,
        start=current_period.start,
        end=current_period.end,
    )
    previous_business = collect_business_metrics(
        session,
        start=previous_period.start,
        end=previous_period.end,
    )
    report["report_id"] = (
        f"x-analytics-{report_type}-{windows.period_key}-{mode}"
    )
    report["report_type"] = report_type
    report["report_period_key"] = windows.period_key
    report["period_strategy"] = {
        "mode": windows.strategy,
        "reference_at": windows.reference_at.isoformat(),
        "monthly_boundary_rule": (
            "subtract_one_calendar_month_and_clamp_day_to_month_end"
            if report_type == "monthly" and windows.strategy == "rolling"
            else None
        ),
    }
    report["comparison"] = {
        "period": {
            "start": previous_period.start.isoformat(),
            "end": previous_period.end.isoformat(),
            "timezone": timezone_name,
            "semantics": "half_open_start_inclusive_end_exclusive",
            "mode": windows.strategy,
        },
        "measurement_mode": mode,
        "overall_kpis": _kpi_comparison(
            report["overall"]["kpis"], previous["overall"]["kpis"]
        ),
        "post_type_kpis": _post_type_comparison(
            current_post_types["patterns"], previous_post_types["patterns"]
        ),
        "operational_metrics": {
            name: _compare_value(value, previous_operations[name])
            for name, value in current_operations.items()
            if name != "current_pending"
        },
        "business_metrics": {
            name: _compare_value(
                value,
                previous_business[name],
            )
            for name, value in current_business.items()
        },
    }
    report["operational_metrics"] = current_operations
    report["business_metrics"] = current_business
    report["dimension_kpis"] = {
        "post_type": current_post_types["patterns"],
        "time_slot": current_time_slots["patterns"],
        "has_cover": current_has_cover["patterns"],
        "store": current_stores["patterns"],
    }
    eligible_posts = list(report["rankings"]["posts"])
    report["top_posts"] = eligible_posts[:3]
    report["bottom_posts"] = list(reversed(eligible_posts[-3:]))
    eligible = list(report["rankings"]["patterns"])
    report["best_patterns"] = eligible[:3]
    report["worst_patterns"] = list(reversed(eligible[-3:]))
    report["recommended_actions"] = (
        [
            {
                "rule_id": "X_PERIOD_BEST_PATTERN_REVIEW_V1",
                "summary": "Review the qualified best patterns and period comparison before planning a future experiment.",
                "evidence": {
                    "best_pattern_ids": [
                        item["identity"] for item in report["best_patterns"]
                    ],
                    "comparison_period": report["comparison"]["period"],
                },
                "sample_size": sum(
                    int(item.get("post_count", 0))
                    for item in report["best_patterns"]
                ),
                "constraints": [
                    "advisory_only",
                    "human_review_required",
                    "no_automatic_execution",
                ],
                "execution_allowed": False,
            }
        ]
        if report["best_patterns"]
        else [
            {
                "rule_id": "X_PERIOD_INSUFFICIENT_DATA_V1",
                "summary": "Collect more observations before selecting a pattern.",
                "evidence": {
                    "excluded_pattern_count": len(
                        report["rankings"]["excluded_patterns"]
                    )
                },
                "sample_size": int(report["overall"]["post_count"]),
                "constraints": [
                    "advisory_only",
                    "human_review_required",
                    "no_automatic_execution",
                ],
                "execution_allowed": False,
            }
        ]
    )
    report["generated_at"] = generated.isoformat()
    return report


def write_periodic_report(
    report: dict[str, Any], *, output_dir: Path = DEFAULT_REPORT_DIR
) -> tuple[Path, Path]:
    report_type = str(report["report_type"])
    period_key = str(report["report_period_key"])
    mode = str(report["aggregation"]["mode"])
    stem = f"x_analytics_{report_type}_{period_key}_{mode}"
    json_path = output_dir / f"{stem}.json"
    markdown_path = output_dir / f"{stem}.md"
    atomic_write_bytes(
        json_path, (canonical_report_json(report) + "\n").encode("utf-8")
    )
    def post_lines(title: str, rows: Sequence[dict[str, Any]]) -> list[str]:
        lines = [f"## {title}", ""]
        if not rows:
            return lines + ["- 対象なし", ""]
        for row in rows:
            url = row.get("post_url") or f"N/A ({row.get('post_url_reason')})"
            lines.append(
                f"- `{row['post_id']}` | URL: {url} | posted: "
                f"`{row.get('posted_at')}` | metric: `{row['metric']}` | "
                f"value: `{row['value']}` | denominator: "
                f"`{row.get('denominator')}` | observed: "
                f"`{row.get('observed_at')}` | eligibility: "
                f"`{row['eligibility']['status']}`"
            )
        return lines + [""]

    markdown = "\n".join(
        (
            f"# X Analytics {report_type.title()} Report",
            "",
            f"- report_id: `{report['report_id']}`",
            f"- generated_at: `{report['generated_at']}`",
            f"- period: `[{report['aggregation']['start']}, {report['aggregation']['end']})`",
            f"- timezone: `{report['aggregation']['timezone']}`",
            f"- period_strategy: `{report['period_strategy']['mode']}`",
            f"- reference_at: `{report['period_strategy']['reference_at']}`",
            f"- measurement: `{mode}`",
            f"- previous_period: `[{report['comparison']['period']['start']}, {report['comparison']['period']['end']})`",
            "",
            "```text",
            render_kpi_report_text(report),
            "```",
            "",
            *post_lines("投稿別 Best 3", report["top_posts"]),
            *post_lines("投稿別 Worst 3", report["bottom_posts"]),
            "## パターン別ランキングと改善提案",
            "",
            "pattern別の順位と改善提案は上記KPI本文およびJSONの "
            "`best_patterns` / `worst_patterns` / `recommended_actions` を参照。",
            "",
        )
    )
    atomic_write_bytes(markdown_path, markdown.encode("utf-8"))
    return json_path, markdown_path