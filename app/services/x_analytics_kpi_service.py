from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.db.models.x_analytics import XAnalyticsMetricSnapshot
from app.db.repositories.x_analytics_kpi_repository import (
    XAnalyticsKpiRepository,
)


DEFAULT_TIMEZONE = os.getenv("TZ", "Asia/Tokyo") or "Asia/Tokyo"
VALID_MODES = {"posted_latest", "activity"}
VALID_AXES = {"post_type", "time_slot", "has_cover", "store"}
VALID_RANKING_METRICS = {
    "reach",
    "ctr",
    "follow_conversion",
    "rpmi",
    "epc",
}
COUNT_FIELDS = (
    "impressions",
    "views",
    "engagements",
    "link_clicks",
    "profile_clicks",
    "likes",
    "reposts",
    "replies",
    "follows",
)
DEFAULT_MIN_POSTS = 3
DEFAULT_MIN_DENOMINATORS = {
    "reach": 0,
    "ctr": 100,
    "engagement_rate": 100,
    "profile_visit_rate": 100,
    "follow_conversion": 5,
    "rpmi": 100,
    "epc": 5,
}


class XAnalyticsKpiError(ValueError):
    pass


@dataclass(frozen=True)
class KpiPeriod:
    start: datetime
    end: datetime
    as_of: datetime
    timezone_name: str
    label: str


@dataclass(frozen=True)
class MetricUnit:
    unit_id: str
    source: str
    account_identifier: str
    post_id: str
    posted_at: datetime | None
    post_type: str
    time_slot: str
    has_cover: str
    store: str
    metrics: dict[str, int | None]
    reported_engagement_rate: Decimal | None
    reach_metric_name: str | None
    interval_start: datetime | None = None
    interval_end: datetime | None = None
    method: str = "latest_lifetime_snapshot"
    correction_fields: tuple[str, ...] = ()
    observed_at: datetime | None = None
    reported_engagement_rate_format: str | None = None

    @property
    def post_key(self) -> tuple[str, str, str]:
        return self.source, self.account_identifier, self.post_id


@dataclass
class Coverage:
    source_snapshot_count: int = 0
    selected_unit_count: int = 0
    selected_post_count: int = 0
    missing_posted_at_count: int = 0
    missing_observed_at_count: int = 0
    excluded_scope_count: int = 0
    excluded_outside_period_count: int = 0
    excluded_partial_interval_count: int = 0
    excluded_overlapping_interval_count: int = 0
    correction_decrease_count: int = 0
    explicit_interval_count: int = 0
    lifetime_delta_count: int = 0
    selected_observation_start: str | None = None
    selected_observation_end: str | None = None
    covered_seconds_total: int = 0
    posts_with_full_period_coverage: int = 0
    posts_with_partial_period_coverage: int = 0
    notes: list[str] = field(default_factory=list)


def _aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise XAnalyticsKpiError(f"unknown timezone: {name}") from exc


def parse_period_boundary(value: str, timezone_name: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise XAnalyticsKpiError("period boundary must not be empty")
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed_date = date.fromisoformat(normalized)
        except ValueError as exc:
            raise XAnalyticsKpiError(
                f"invalid ISO 8601 period boundary: {value}"
            ) from exc
        parsed = datetime.combine(parsed_date, time.min)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=_zone(timezone_name))
    return parsed.astimezone(timezone.utc)


def resolve_period(
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    last_days: int | None = None,
    start: str | None = None,
    end: str | None = None,
    as_of: str | None = None,
    now: datetime | None = None,
) -> KpiPeriod:
    zone = _zone(timezone_name)
    if last_days is not None and (start or end):
        raise XAnalyticsKpiError(
            "last_days cannot be combined with start/end"
        )
    if last_days is not None:
        if last_days not in {7, 30}:
            raise XAnalyticsKpiError("last_days must be 7 or 30")
        current = now or datetime.now(timezone.utc)
        current_utc = _aware_utc(current)
        assert current_utc is not None
        end_utc = current_utc
        start_utc = end_utc - timedelta(days=last_days)
        label = f"last_{last_days}_days"
    else:
        if not start or not end:
            raise XAnalyticsKpiError(
                "either last_days or both start and end are required"
            )
        start_utc = parse_period_boundary(start, timezone_name)
        end_utc = parse_period_boundary(end, timezone_name)
        label = "custom"
    if end_utc <= start_utc:
        raise XAnalyticsKpiError("period end must be after start")
    as_of_utc = (
        parse_period_boundary(as_of, timezone_name)
        if as_of
        else end_utc
    )
    return KpiPeriod(
        start=start_utc,
        end=end_utc,
        as_of=as_of_utc,
        timezone_name=zone.key,
        label=label,
    )


def _dimensions(
    snapshot: XAnalyticsMetricSnapshot,
    zone: ZoneInfo,
) -> tuple[str, str, str, str]:
    posted_at = _aware_utc(snapshot.posted_at)
    if posted_at is None:
        time_slot = "unknown"
    else:
        hour = posted_at.astimezone(zone).hour
        time_slot = (
            "00-05"
            if hour < 6
            else "06-11"
            if hour < 12
            else "12-17"
            if hour < 18
            else "18-23"
        )
    has_cover = (
        "unknown"
        if snapshot.has_cover is None
        else "with_cover"
        if snapshot.has_cover
        else "without_cover"
    )
    return (
        snapshot.post_type or "unknown",
        time_slot,
        has_cover,
        snapshot.store_name or "unknown",
    )


def _metrics(snapshot: XAnalyticsMetricSnapshot) -> dict[str, int | None]:
    return {name: getattr(snapshot, name) for name in COUNT_FIELDS}


def _unit_from_snapshot(
    snapshot: XAnalyticsMetricSnapshot,
    zone: ZoneInfo,
    *,
    method: str,
) -> MetricUnit:
    post_type, time_slot, has_cover, store = _dimensions(snapshot, zone)
    return MetricUnit(
        unit_id=snapshot.id,
        source=snapshot.source,
        account_identifier=snapshot.account_identifier,
        post_id=snapshot.post_id,
        posted_at=_aware_utc(snapshot.posted_at),
        post_type=post_type,
        time_slot=time_slot,
        has_cover=has_cover,
        store=store,
        metrics=_metrics(snapshot),
        reported_engagement_rate=snapshot.engagement_rate,
        reach_metric_name=snapshot.reach_metric_name,
        interval_start=_aware_utc(snapshot.interval_start_at),
        interval_end=_aware_utc(snapshot.interval_end_at),
        method=method,
        observed_at=_aware_utc(snapshot.observed_at),
        reported_engagement_rate_format=snapshot.engagement_rate_format,
    )


def _posted_latest_units(
    snapshots: Sequence[XAnalyticsMetricSnapshot],
    period: KpiPeriod,
    coverage: Coverage,
) -> list[MetricUnit]:
    zone = _zone(period.timezone_name)
    candidates: dict[tuple[str, str, str], XAnalyticsMetricSnapshot] = {}
    for snapshot in snapshots:
        if snapshot.metric_scope != "lifetime":
            coverage.excluded_scope_count += 1
            continue
        posted_at = _aware_utc(snapshot.posted_at)
        observed_at = _aware_utc(snapshot.observed_at)
        if posted_at is None:
            coverage.missing_posted_at_count += 1
            continue
        if not (period.start <= posted_at < period.end):
            coverage.excluded_outside_period_count += 1
            continue
        if posted_at > period.as_of:
            coverage.excluded_outside_period_count += 1
            continue
        if observed_at is None:
            coverage.missing_observed_at_count += 1
            continue
        if observed_at > period.as_of:
            coverage.excluded_outside_period_count += 1
            continue
        key = (
            snapshot.source,
            snapshot.account_identifier,
            snapshot.post_id,
        )
        current = candidates.get(key)
        current_observed = _aware_utc(current.observed_at) if current else None
        if current is None or (observed_at, snapshot.id) > (
            current_observed,
            current.id,
        ):
            candidates[key] = snapshot
    return [
        _unit_from_snapshot(snapshot, zone, method="latest_lifetime_snapshot")
        for _, snapshot in sorted(candidates.items())
    ]


def _lifetime_delta(
    previous: XAnalyticsMetricSnapshot,
    current: XAnalyticsMetricSnapshot,
    zone: ZoneInfo,
) -> MetricUnit:
    base = _unit_from_snapshot(current, zone, method="lifetime_snapshot_delta")
    metrics: dict[str, int | None] = {}
    corrections: list[str] = []
    for name in COUNT_FIELDS:
        before = getattr(previous, name)
        after = getattr(current, name)
        if before is None or after is None:
            metrics[name] = None
        elif after < before:
            metrics[name] = None
            corrections.append(name)
        else:
            metrics[name] = after - before
    return MetricUnit(
        **{
            **base.__dict__,
            "unit_id": f"{previous.id}:{current.id}",
            "metrics": metrics,
            "reported_engagement_rate": None,
            "reported_engagement_rate_format": None,
            "interval_start": _aware_utc(previous.observed_at),
            "interval_end": _aware_utc(current.observed_at),
            "correction_fields": tuple(corrections),
        }
    )


def _activity_units(
    snapshots: Sequence[XAnalyticsMetricSnapshot],
    period: KpiPeriod,
    coverage: Coverage,
) -> list[MetricUnit]:
    zone = _zone(period.timezone_name)
    grouped: dict[tuple[str, str, str], list[XAnalyticsMetricSnapshot]] = defaultdict(list)
    explicit: list[MetricUnit] = []
    for snapshot in snapshots:
        key = (snapshot.source, snapshot.account_identifier, snapshot.post_id)
        if snapshot.metric_scope == "lifetime":
            snapshot_observed = _aware_utc(snapshot.observed_at)
            if snapshot_observed is None:
                coverage.missing_observed_at_count += 1
            elif snapshot_observed > period.as_of:
                coverage.excluded_outside_period_count += 1
            else:
                grouped[key].append(snapshot)
        elif snapshot.metric_scope == "interval":
            unit = _unit_from_snapshot(snapshot, zone, method="explicit_interval")
            if unit.observed_at is None:
                coverage.missing_observed_at_count += 1
            if unit.interval_start is None or unit.interval_end is None:
                coverage.excluded_partial_interval_count += 1
            elif (
                period.start <= unit.interval_start
                and unit.interval_end <= period.end
                and unit.interval_end <= period.as_of
                and (
                    unit.observed_at is None
                    or unit.observed_at <= period.as_of
                )
            ):
                explicit.append(unit)
            else:
                coverage.excluded_partial_interval_count += 1
        else:
            coverage.excluded_scope_count += 1

    derived: list[MetricUnit] = []
    for rows in grouped.values():
        ordered = sorted(
            rows,
            key=lambda item: (_aware_utc(item.observed_at), item.id),
        )
        for previous, current in zip(ordered, ordered[1:]):
            unit = _lifetime_delta(previous, current, zone)
            if (
                unit.interval_start is not None
                and unit.interval_end is not None
                and period.start <= unit.interval_start
                and unit.interval_end <= period.end
            ):
                derived.append(unit)
                coverage.correction_decrease_count += len(
                    unit.correction_fields
                )
            else:
                coverage.excluded_partial_interval_count += 1

    by_post: dict[tuple[str, str, str], list[MetricUnit]] = defaultdict(list)
    for unit in (*explicit, *derived):
        by_post[unit.post_key].append(unit)
    selected: list[MetricUnit] = []
    for units in by_post.values():
        ordered = sorted(
            units,
            key=lambda item: (
                item.interval_end,
                item.interval_start,
                0 if item.method == "explicit_interval" else 1,
                item.unit_id,
            ),
        )
        last_end: datetime | None = None
        for unit in ordered:
            assert unit.interval_start is not None
            assert unit.interval_end is not None
            if last_end is not None and unit.interval_start < last_end:
                coverage.excluded_overlapping_interval_count += 1
                continue
            selected.append(unit)
            last_end = unit.interval_end
            if unit.method == "explicit_interval":
                coverage.explicit_interval_count += 1
            else:
                coverage.lifetime_delta_count += 1
    return sorted(selected, key=lambda item: (item.post_key, item.interval_start, item.unit_id))


def _metric_result(
    units: Sequence[MetricUnit],
    *,
    numerator_name: str,
    denominator_name: str,
    multiplier: Decimal = Decimal("1"),
) -> dict[str, Any]:
    denominator_available = [
        unit for unit in units if unit.metrics.get(denominator_name) is not None
    ]
    paired = [
        unit
        for unit in denominator_available
        if unit.metrics.get(numerator_name) is not None
    ]
    if not denominator_available:
        return {
            "value": None,
            "reason": "denominator_missing",
            "numerator": None,
            "denominator": None,
            "valid_count": 0,
            "denominator_count": 0,
        }
    if not paired:
        return {
            "value": None,
            "reason": "numerator_missing",
            "numerator": None,
            "denominator": sum(
                int(unit.metrics[denominator_name])
                for unit in denominator_available
            ),
            "valid_count": 0,
            "denominator_count": len(denominator_available),
        }
    numerator = sum(int(unit.metrics[numerator_name]) for unit in paired)
    denominator = sum(int(unit.metrics[denominator_name]) for unit in paired)
    if denominator == 0:
        return {
            "value": None,
            "reason": "denominator_zero",
            "numerator": numerator,
            "denominator": denominator,
            "valid_count": len(paired),
            "denominator_count": len(paired),
        }
    return {
        "value": float(Decimal(numerator) / Decimal(denominator) * multiplier),
        "reason": None,
        "numerator": numerator,
        "denominator": denominator,
        "valid_count": len(paired),
        "denominator_count": len(paired),
    }


def _impressions_per_post(units: Sequence[MetricUnit]) -> dict[str, Any]:
    valid = [unit for unit in units if unit.metrics.get("impressions") is not None]
    if not valid:
        return {
            "value": None,
            "reason": "impressions_missing",
            "numerator": None,
            "denominator": None,
            "valid_count": 0,
            "denominator_count": 0,
        }
    post_count = len({unit.post_key for unit in valid})
    total = sum(int(unit.metrics["impressions"]) for unit in valid)
    return {
        "value": float(Decimal(total) / Decimal(post_count)),
        "reason": None,
        "numerator": total,
        "denominator": post_count,
        "valid_count": len(valid),
        "denominator_count": post_count,
    }


def _reach(units: Sequence[MetricUnit], reach_field: str) -> dict[str, Any]:
    if reach_field == "declared":
        names = {unit.reach_metric_name for unit in units if unit.reach_metric_name}
        if len(names) != 1:
            return {
                "value": None,
                "reason": "declared_reach_metric_missing_or_mixed",
                "metric_name": None,
                "valid_count": 0,
                "denominator_count": 0,
            }
        metric_name = next(iter(names))
    else:
        metric_name = reach_field
    valid = [
        unit
        for unit in units
        if unit.metrics.get(metric_name) is not None
        and (
            reach_field != "declared"
            or unit.reach_metric_name == metric_name
        )
    ]
    if not valid:
        return {
            "value": None,
            "reason": f"{metric_name}_missing",
            "metric_name": metric_name,
            "valid_count": 0,
            "denominator_count": 0,
        }
    return {
        "value": sum(int(unit.metrics[metric_name]) for unit in valid),
        "reason": None,
        "metric_name": metric_name,
        "valid_count": len(valid),
        "denominator_count": len(valid),
    }


def _reported_rate(units: Sequence[MetricUnit]) -> dict[str, Any]:
    values = [
        unit.reported_engagement_rate
        for unit in units
        if unit.reported_engagement_rate is not None
    ]
    if not values:
        return {"value": None, "reason": "reported_rate_missing", "valid_count": 0}
    if len(units) != 1:
        return {
            "value": None,
            "reason": "multiple_reported_rates_not_aggregated",
            "valid_count": len(values),
        }
    return {
        "value": float(values[0]),
        "reason": None,
        "valid_count": 1,
        "format": units[0].reported_engagement_rate_format,
    }


def _unavailable_affiliate(reason: str) -> dict[str, Any]:
    return {
        "value": None,
        "reason": reason,
        "numerator": None,
        "denominator": None,
        "currency": None,
        "valid_count": 0,
        "denominator_count": 0,
    }


def calculate_kpis(
    units: Sequence[MetricUnit], *, reach_field: str
) -> dict[str, dict[str, Any]]:
    return {
        "reach": _reach(units, reach_field),
        "impressions_per_post": _impressions_per_post(units),
        "engagement_rate": _metric_result(
            units,
            numerator_name="engagements",
            denominator_name="impressions",
        ),
        "ctr": _metric_result(
            units,
            numerator_name="link_clicks",
            denominator_name="impressions",
        ),
        "profile_visit_rate": _metric_result(
            units,
            numerator_name="profile_clicks",
            denominator_name="impressions",
        ),
        "follow_conversion": _metric_result(
            units,
            numerator_name="follows",
            denominator_name="profile_clicks",
        ),
        "reported_engagement_rate": _reported_rate(units),
        "epc": _unavailable_affiliate(
            "attributed_affiliate_revenue_and_clicks_unavailable"
        ),
        "rpmi": _unavailable_affiliate(
            "attributed_affiliate_revenue_unavailable"
        ),
    }


def _axis_value(unit: MetricUnit, axis: str) -> str:
    return str(getattr(unit, axis))


def _group_payload(
    units: Sequence[MetricUnit],
    *,
    axes: Sequence[str],
    reach_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[MetricUnit]] = defaultdict(list)
    for unit in units:
        grouped[tuple(_axis_value(unit, axis) for axis in axes)].append(unit)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = grouped[key]
        rows.append(
            {
                "group": dict(zip(axes, key)),
                "group_key": "|".join(f"{axis}={value}" for axis, value in zip(axes, key)),
                "post_count": len({unit.post_key for unit in members}),
                "unit_count": len(members),
                "kpis": calculate_kpis(members, reach_field=reach_field),
            }
        )
    return rows


def _post_payload(
    units: Sequence[MetricUnit], *, reach_field: str
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[MetricUnit]] = defaultdict(list)
    for unit in units:
        grouped[unit.post_key].append(unit)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        members = grouped[key]
        first = members[0]
        posted_values = sorted(
            unit.posted_at for unit in members if unit.posted_at is not None
        )
        observed_values = sorted(
            unit.observed_at for unit in members if unit.observed_at is not None
        )
        post_url = (
            f"https://x.com/i/web/status/{key[2]}"
            if key[2].isascii() and key[2].isdigit()
            else None
        )
        rows.append(
            {
                "source": key[0],
                "account_identifier": key[1],
                "post_id": key[2],
                "post_url": post_url,
                "post_url_reason": None if post_url else "post_id_not_numeric",
                "posted_at": posted_values[0].isoformat() if posted_values else None,
                "observed_at": (
                    observed_values[-1].isoformat() if observed_values else None
                ),
                "post_key": "|".join(key),
                "post_type": first.post_type,
                "time_slot": first.time_slot,
                "has_cover": first.has_cover,
                "store": first.store,
                "unit_count": len(members),
                "kpis": calculate_kpis(members, reach_field=reach_field),
            }
        )
    return rows


def _minimum_denominator(metric: str, thresholds: dict[str, int]) -> int:
    return int(thresholds.get(metric, 0))


def _rank(
    rows: Sequence[dict[str, Any]],
    *,
    metric: str,
    minimum_denominator: int,
    minimum_posts: int | None,
    identity_field: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        metric_data = row["kpis"][metric]
        value = metric_data.get("value")
        denominator = metric_data.get("denominator")
        post_count = int(row.get("post_count", 1))
        unavailable_reasons: list[str] = []
        sample_reasons: list[str] = []
        if value is None:
            unavailable_reasons.append(
                str(metric_data.get("reason") or "metric_unavailable")
            )
        if minimum_posts is not None and post_count < minimum_posts:
            sample_reasons.append("minimum_post_count_not_met")
        if denominator is not None and int(denominator) < minimum_denominator:
            sample_reasons.append("minimum_denominator_not_met")
        elif denominator is None and minimum_denominator > 0:
            unavailable_reasons.append("minimum_denominator_unavailable")
        reasons = sorted(set(unavailable_reasons + sample_reasons))
        status = (
            "unavailable"
            if unavailable_reasons
            else "insufficient_sample"
            if sample_reasons
            else "eligible"
        )
        candidate = {
            "identity": row[identity_field],
            "metric": metric,
            "value": value,
            "post_count": post_count,
            "valid_count": int(metric_data.get("valid_count", 0)),
            "denominator_count": int(metric_data.get("denominator_count", 0)),
            "denominator": denominator,
            "denominator_reason": (
                None
                if denominator is not None
                else "not_applicable_for_absolute_metric"
                if metric in {"reach"}
                else str(metric_data.get("reason") or "denominator_unavailable")
            ),
            "status": status,
            "reasons": reasons,
            "eligibility": {"status": status, "reasons": reasons},
        }
        for field in (
            "post_id",
            "post_url",
            "post_url_reason",
            "posted_at",
            "observed_at",
        ):
            if field in row:
                candidate[field] = row[field]
        if reasons:
            excluded.append(candidate)
        else:
            eligible.append(candidate)
    eligible.sort(
        key=lambda item: (-float(item["value"]), str(item["identity"]))
    )
    for index, item in enumerate(eligible, start=1):
        item["rank"] = index
    excluded.sort(key=lambda item: str(item["identity"]))
    return eligible, excluded


class XAnalyticsKpiService:
    def __init__(self, session: Session) -> None:
        self.repository = XAnalyticsKpiRepository(session)

    def build_report(
        self,
        *,
        period: KpiPeriod,
        mode: str,
        axes: Sequence[str] = ("post_type",),
        ranking_metric: str = "reach",
        reach_field: str = "impressions",
        min_posts: int = DEFAULT_MIN_POSTS,
        min_denominators: dict[str, int] | None = None,
        dimension_filters: dict[str, str] | None = None,
        source: str | None = None,
        account_identifier: str | None = None,
    ) -> dict[str, Any]:
        if mode not in VALID_MODES:
            raise XAnalyticsKpiError(f"unsupported mode: {mode}")
        if not axes or any(axis not in VALID_AXES for axis in axes):
            raise XAnalyticsKpiError("invalid or empty aggregation axes")
        if len(set(axes)) != len(axes):
            raise XAnalyticsKpiError("aggregation axes must not be duplicated")
        if ranking_metric not in VALID_RANKING_METRICS:
            raise XAnalyticsKpiError("unsupported ranking metric")
        if reach_field not in {"impressions", "views", "declared"}:
            raise XAnalyticsKpiError("reach_field must be impressions, views, or declared")
        if min_posts < 1:
            raise XAnalyticsKpiError("min_posts must be at least 1")
        filters = {
            str(name): str(value)
            for name, value in (dimension_filters or {}).items()
            if str(value) not in {"", "all"}
        }
        if any(name not in VALID_AXES for name in filters):
            raise XAnalyticsKpiError("unsupported dimension filter")
        thresholds = dict(DEFAULT_MIN_DENOMINATORS)
        if min_denominators:
            for name, value in min_denominators.items():
                if name not in thresholds or value < 0:
                    raise XAnalyticsKpiError("invalid metric denominator threshold")
                thresholds[name] = int(value)

        snapshots = self.repository.list_snapshots(
            source=source, account_identifier=account_identifier
        )
        available_sources = {snapshot.source for snapshot in snapshots}
        if (
            source is None
            and "x_api_v2" in available_sources
            and len(available_sources) > 1
        ):
            raise XAnalyticsKpiError(
                "multiple metric sources include x_api_v2; source filter is required"
            )
        coverage = Coverage(source_snapshot_count=len(snapshots))
        units = (
            _posted_latest_units(snapshots, period, coverage)
            if mode == "posted_latest"
            else _activity_units(snapshots, period, coverage)
        )
        units = [
            unit
            for unit in units
            if all(_axis_value(unit, name) == value for name, value in filters.items())
        ]
        coverage.selected_unit_count = len(units)
        coverage.selected_post_count = len({unit.post_key for unit in units})
        observations = sorted(
            unit.observed_at for unit in units if unit.observed_at is not None
        )
        if observations:
            coverage.selected_observation_start = observations[0].isoformat()
            coverage.selected_observation_end = observations[-1].isoformat()
        if mode == "activity":
            durations_by_post: dict[tuple[str, str, str], int] = defaultdict(int)
            for unit in units:
                if unit.interval_start is None or unit.interval_end is None:
                    continue
                durations_by_post[unit.post_key] += int(
                    (unit.interval_end - unit.interval_start).total_seconds()
                )
            coverage.covered_seconds_total = sum(durations_by_post.values())
            period_seconds = int((period.end - period.start).total_seconds())
            coverage.posts_with_full_period_coverage = sum(
                duration == period_seconds
                for duration in durations_by_post.values()
            )
            coverage.posts_with_partial_period_coverage = sum(
                duration < period_seconds
                for duration in durations_by_post.values()
            )
        if mode == "posted_latest":
            coverage.notes.append(
                "A: posts published in [start,end), using each post's latest lifetime snapshot at or before as_of"
            )
        else:
            coverage.notes.extend(
                [
                    "B: activity from fully-contained explicit intervals or adjacent lifetime snapshot deltas",
                    "partial intervals are not prorated; overlapping intervals are deterministically excluded",
                    "decreasing lifetime counters are treated as correction/missing for that metric",
                ]
            )
        coverage.notes.append(
            "source/account/post_id is the unique posting identity; cross-source duplicates are not merged"
        )
        if any(unit.source == "x_api_v2" for unit in units):
            coverage.notes.append(
                "x_api_v2 uses sparse lifetime observations near +1d/+7d/+28d; "
                "strict within-period activity cannot be inferred between observations"
            )

        posts = _post_payload(units, reach_field=reach_field)
        patterns = _group_payload(units, axes=axes, reach_field=reach_field)
        post_ranking, post_excluded = _rank(
            posts,
            metric=ranking_metric,
            minimum_denominator=_minimum_denominator(ranking_metric, thresholds),
            minimum_posts=None,
            identity_field="post_key",
        )
        pattern_ranking, pattern_excluded = _rank(
            patterns,
            metric=ranking_metric,
            minimum_denominator=_minimum_denominator(ranking_metric, thresholds),
            minimum_posts=min_posts,
            identity_field="group_key",
        )
        return {
            "schema_version": "x_analytics_kpi_report_v1",
            "aggregation": {
                "mode": mode,
                "period_semantics": "half_open_start_inclusive_end_exclusive",
                "start": period.start.isoformat(),
                "end": period.end.isoformat(),
                "as_of": period.as_of.isoformat(),
                "timezone": period.timezone_name,
                "period_label": period.label,
                "axes": list(axes),
                "reach_field": reach_field,
                "source_filter": source,
                "account_filter": account_identifier,
                "dimension_filters": filters,
                "measurement_limitations": (
                    [
                        "sparse_lifetime_observations_do_not_measure_strict_weekly_activity"
                    ]
                    if any(unit.source == "x_api_v2" for unit in units)
                    else []
                ),
            },
            "coverage": {
                **coverage.__dict__,
                "available_affiliate_attribution": False,
                "affiliate_limitation": (
                    "No post-attributed affiliate revenue/click fact table exists; "
                    "EPC and RPMI remain N/A and no store totals are allocated to posts."
                ),
                "affiliate_revenue_recognition_basis": None,
                "affiliate_currency_policy": (
                    "Currencies are not converted or combined without an explicit rate source."
                ),
            },
            "thresholds": {
                "alpha": True,
                "minimum_posts": min_posts,
                "minimum_denominators": thresholds,
                "reason": (
                    "Alpha defaults suppress rankings based on fewer than 3 posts, "
                    "fewer than 100 impressions, or fewer than 5 profile/affiliate clicks."
                ),
            },
            "overall": {
                "post_count": len({unit.post_key for unit in units}),
                "unit_count": len(units),
                "kpis": calculate_kpis(units, reach_field=reach_field),
            },
            "posts": posts,
            "patterns": patterns,
            "rankings": {
                "metric": ranking_metric,
                "posts": post_ranking,
                "patterns": pattern_ranking,
                "excluded_posts": post_excluded,
                "excluded_patterns": pattern_excluded,
                "tie_breaker": "metric_desc_then_identity_asc",
                "na_values_ranked": False,
            },
        }


def render_kpi_report_text(report: dict[str, Any]) -> str:
    aggregation = report["aggregation"]
    coverage = report["coverage"]
    overall = report["overall"]
    lines = [
        "X Analytics KPI Report",
        f"mode: {aggregation['mode']}",
        f"period: [{aggregation['start']}, {aggregation['end']})",
        f"timezone: {aggregation['timezone']}",
        f"as_of: {aggregation['as_of']}",
        f"posts: {overall['post_count']} units: {overall['unit_count']}",
        f"coverage: selected={coverage['selected_unit_count']} overlaps_excluded={coverage['excluded_overlapping_interval_count']} corrections={coverage['correction_decrease_count']}",
        "",
        "Overall KPI",
    ]
    for name, value in overall["kpis"].items():
        rendered = "N/A" if value.get("value") is None else str(value["value"])
        reason = f" ({value.get('reason')})" if value.get("reason") else ""
        lines.append(f"- {name}: {rendered}{reason}")
    lines.extend(["", f"Post ranking: {report['rankings']['metric']}"])
    for item in report["rankings"]["posts"]:
        lines.append(
            f"- {item['rank']}. {item['identity']}: {item['value']}"
        )
    lines.extend(["", f"Pattern ranking: {report['rankings']['metric']}"])
    for item in report["rankings"]["patterns"]:
        lines.append(
            f"- {item['rank']}. {item['identity']}: {item['value']}"
        )
    return "\n".join(lines)


def canonical_report_json(report: dict[str, Any]) -> str:
    return json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
        sort_keys=True,
    )