from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo


SNAPSHOT_SCHEMA_VERSION = "x_core_advisory_snapshot_v1"
MANIFEST_SCHEMA_VERSION = "x_core_advisory_manifest_v1"
SOURCE_KPI_SCHEMA_VERSION = "x_analytics_kpi_report_v1"
REPORT_TYPES = {"x_kpi_summary", "weekly", "monthly"}
SAFE_ACTION_CONSTRAINTS = [
    "advisory_only",
    "human_review_required",
    "no_automatic_execution",
    "no_post_or_publish",
    "no_schedule_or_template_change",
]
KPI_NAMES = (
    "reach",
    "impressions_per_post",
    "engagement_rate",
    "ctr",
    "profile_visit_rate",
    "follow_conversion",
    "reported_engagement_rate",
    "epc",
    "rpmi",
)


class XCoreAdvisoryContractError(ValueError):
    pass


def strict_load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON number: {token}")
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise XCoreAdvisoryContractError(
            f"invalid JSON document: {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise XCoreAdvisoryContractError("JSON root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aware(value: Any, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise XCoreAdvisoryContractError(
            f"{field_name} must be ISO 8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise XCoreAdvisoryContractError(
            f"{field_name} must include a timezone"
        )
    return parsed.astimezone(timezone.utc)


def _unavailable_kpis(reason: str) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "value": None,
            "reason": reason,
            "numerator": None,
            "denominator": None,
            "currency": None if name in {"epc", "rpmi"} else None,
            "valid_count": 0,
            "denominator_count": 0,
        }
        for name in KPI_NAMES
    }


def _na(reason: str) -> dict[str, Any]:
    return {"value": None, "reason": reason}


def _period_from_legacy(
    report: Mapping[str, Any], report_type: str, timezone_name: str
) -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone_name)
    if report_type == "weekly":
        matched = re.fullmatch(r"(\d{4})W(\d{2})", str(report.get("report_week", "")))
        if matched is None:
            raise XCoreAdvisoryContractError("legacy weekly report_week is invalid")
        start_date = date.fromisocalendar(int(matched.group(1)), int(matched.group(2)), 1)
        end_date = start_date + timedelta(days=7)
    elif report_type == "monthly":
        matched = re.fullmatch(r"(\d{4})(\d{2})", str(report.get("report_month", "")))
        if matched is None:
            raise XCoreAdvisoryContractError("legacy monthly report_month is invalid")
        year, month = int(matched.group(1)), int(matched.group(2))
        start_date = date(year, month, 1)
        end_date = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    else:
        raise XCoreAdvisoryContractError("legacy format supports weekly/monthly only")
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=zone)
    end = datetime.combine(end_date, datetime.min.time(), tzinfo=zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _source_reference(path: Path, schema_version: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "schema_version": schema_version,
    }


def _insufficient_from_kpi(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    overall = report.get("overall", {})
    kpis = overall.get("kpis", {}) if isinstance(overall, dict) else {}
    for metric in KPI_NAMES:
        value = kpis.get(metric, {}) if isinstance(kpis, dict) else {}
        if not isinstance(value, dict) or value.get("value") is None:
            rows.append(
                {
                    "scope": "overall",
                    "metric": metric,
                    "identity": None,
                    "reason": str(
                        value.get("reason", "metric_missing")
                        if isinstance(value, dict)
                        else "metric_missing"
                    ),
                    "sample_size": int(
                        value.get("valid_count", 0)
                        if isinstance(value, dict)
                        else 0
                    ),
                    "details": [],
                }
            )
    rankings = report.get("rankings", {})
    excluded = rankings.get("excluded_patterns", []) if isinstance(rankings, dict) else []
    for item in excluded if isinstance(excluded, list) else []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "scope": "pattern",
                "metric": str(rankings.get("metric", "unknown")),
                "identity": str(item.get("identity", "unknown")),
                "reason": str(item.get("status", "insufficient_sample")),
                "details": list(item.get("reasons", [])),
                "sample_size": int(item.get("post_count", 0)),
            }
        )
    return rows


def _anomalies(report: Mapping[str, Any], freshness: Mapping[str, Any]) -> list[dict[str, Any]]:
    coverage = report.get("coverage", {})
    if not isinstance(coverage, dict):
        coverage = {}
    rules = (
        ("X_DATA_MISSING_POSTED_AT_V1", "missing_data", "missing_posted_at_count"),
        ("X_DATA_MISSING_OBSERVED_AT_V1", "missing_data", "missing_observed_at_count"),
        ("X_DATA_OVERLAPPING_INTERVAL_V1", "duplicate_suspected", "excluded_overlapping_interval_count"),
        ("X_DATA_COUNTER_DECREASE_V1", "counter_decrease", "correction_decrease_count"),
    )
    rows: list[dict[str, Any]] = []
    for rule_id, anomaly_type, field_name in rules:
        count = int(coverage.get(field_name, 0) or 0)
        if count:
            rows.append(
                {
                    "rule_id": rule_id,
                    "type": anomaly_type,
                    "severity": "warning",
                    "count": count,
                    "evidence_field": f"coverage.{field_name}",
                }
            )
    if freshness.get("status") == "stale":
        rows.append(
            {
                "rule_id": "X_DATA_STALE_V1",
                "type": "stale_data",
                "severity": "warning",
                "count": 1,
                "evidence_field": "freshness.age_seconds",
            }
        )
    return rows



def _x_feedback_pattern_evidence(
    report: Mapping[str, Any],
    winner: Mapping[str, Any],
) -> dict[str, Any] | None:
    """
    Build advisory-only structured evidence for the
    top qualified four-axis X Analytics pattern.

    This evidence never authorizes posting, scheduling,
    template changes, or any automatic execution.
    """
    identity = str(
        winner.get("identity")
        or ""
    ).strip()

    if not identity:
        return None

    dimensions: dict[str, str] = {}

    for component in identity.split("|"):
        key, sep, value = (
            component.partition("=")
        )

        if not sep:
            continue

        key = key.strip()
        value = value.strip()

        if key in {
            "post_type",
            "time_slot",
            "has_cover",
            "store",
        }:
            dimensions[key] = value

    required_axes = (
        "post_type",
        "time_slot",
        "has_cover",
        "store",
    )

    if any(
        not dimensions.get(axis)
        or dimensions.get(axis) == "unknown"
        for axis in required_axes
    ):
        return None

    rankings = report.get(
        "rankings",
        {},
    )

    if not isinstance(
        rankings,
        Mapping,
    ):
        rankings = {}

    aggregation = report.get(
        "aggregation",
        {},
    )

    if not isinstance(
        aggregation,
        Mapping,
    ):
        aggregation = {}

    return {
        "schema":
            "x_analytics_pattern_evidence_v1",
        "identity":
            identity,
        "metric":
            rankings.get("metric"),
        "value":
            winner.get("value"),
        "post_count":
            int(
                winner.get(
                    "post_count",
                    0,
                )
                or 0
            ),
        "rank":
            winner.get("rank"),
        "status":
            winner.get("status"),
        "reach_field":
            aggregation.get(
                "reach_field"
            ),
        "dimensions": {
            axis: dimensions[axis]
            for axis in required_axes
        },
        "advisory_only":
            True,
        "human_review_required":
            True,
        "execution_allowed":
            False,
    }


def _recommended_actions(
    report: Mapping[str, Any],
    period: Mapping[str, Any],
    anomalies: list[dict[str, Any]],
    insufficient: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rankings = report.get("rankings", {})
    patterns = rankings.get("patterns", []) if isinstance(rankings, dict) else []
    actions: list[dict[str, Any]] = []
    if isinstance(patterns, list) and patterns:
        winner = patterns[0] if isinstance(patterns[0], dict) else {}
        evidence = _x_feedback_pattern_evidence(
            report,
            winner,
        )
        action = {
            "rule_id": "X_KPI_TOP_PATTERN_REVIEW_V1",
            "kind": "review_candidate",
            "summary": "Review the top qualified pattern as evidence for a future experiment.",
            "rationale": {
                "ranking_metric": rankings.get("metric"),
                "pattern_identity": winner.get("identity"),
                "metric_value": winner.get("value"),
            },
            "target_period": dict(period),
            "sample_size": int(winner.get("post_count", 0)),
            "constraints": list(SAFE_ACTION_CONSTRAINTS),
            "advisory_only": True,
            "execution_allowed": False,
        }
        if evidence is not None:
            action["evidence"] = evidence
        actions.append(action)
    if anomalies:
        actions.append(
            {
                "rule_id": "X_KPI_DATA_QUALITY_REVIEW_V1",
                "kind": "data_quality_review",
                "summary": "Review the listed measurement anomalies before drawing conclusions.",
                "rationale": {"anomaly_rule_ids": [row["rule_id"] for row in anomalies]},
                "target_period": dict(period),
                "sample_size": int(report.get("overall", {}).get("post_count", 0)),
                "constraints": list(SAFE_ACTION_CONSTRAINTS),
                "advisory_only": True,
                "execution_allowed": False,
            }
        )
    if insufficient and not actions:
        actions.append(
            {
                "rule_id": "X_KPI_INSUFFICIENT_DATA_REVIEW_V1",
                "kind": "collect_more_measurements",
                "summary": "Collect additional measurements before selecting a pattern.",
                "rationale": {"insufficient_item_count": len(insufficient)},
                "target_period": dict(period),
                "sample_size": int(report.get("overall", {}).get("post_count", 0)),
                "constraints": list(SAFE_ACTION_CONSTRAINTS),
                "advisory_only": True,
                "execution_allowed": False,
            }
        )
    return actions


def build_advisory_snapshot(
    source_report: Mapping[str, Any],
    *,
    report_type: str,
    source_path: Path,
    generated_at: datetime | None = None,
    max_age_hours: int = 48,
    legacy_timezone: str = "Asia/Tokyo",
) -> dict[str, Any]:
    if report_type not in REPORT_TYPES:
        raise XCoreAdvisoryContractError("unsupported report_type")
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    source_schema = str(source_report.get("schema_version") or "legacy_operational_report")

    if source_schema == SOURCE_KPI_SCHEMA_VERSION:
        aggregation = source_report.get("aggregation")
        if not isinstance(aggregation, dict):
            raise XCoreAdvisoryContractError("KPI report aggregation is required")
        start = _aware(aggregation.get("start"), "aggregation.start")
        end = _aware(aggregation.get("end"), "aggregation.end")
        as_of = _aware(aggregation.get("as_of"), "aggregation.as_of")
        timezone_name = str(aggregation.get("timezone") or "")
        mode = str(aggregation.get("mode") or "")
        basis = "lifetime_cohort" if mode == "posted_latest" else "interval_activity"
        overall = source_report.get("overall", {})
        overall_kpis = deepcopy(
            overall.get("kpis", {}) if isinstance(overall, dict) else {}
        )
        patterns = source_report.get("patterns", [])
        patterns = patterns if isinstance(patterns, list) else []
        dimensions = source_report.get("dimension_kpis", {})
        dimensions = dimensions if isinstance(dimensions, dict) else {}
        store_kpis = deepcopy(
            dimensions.get("store")
            if isinstance(dimensions.get("store"), list)
            else [
                row for row in patterns
                if isinstance(row, dict) and "store" in row.get("group", {})
            ]
        )
        post_type_kpis = deepcopy(
            dimensions.get("post_type")
            if isinstance(dimensions.get("post_type"), list)
            else [
                row for row in patterns
                if isinstance(row, dict) and "post_type" in row.get("group", {})
            ]
        )
        rankings = source_report.get("rankings", {})
        ranked = rankings.get("patterns", []) if isinstance(rankings, dict) else []
        ranked = ranked if isinstance(ranked, list) else []
        source_best = source_report.get("best_patterns")
        source_worst = source_report.get("worst_patterns")
        top_patterns = deepcopy(
            source_best if isinstance(source_best, list) else ranked[:3]
        )
        bottom_patterns = deepcopy(
            source_worst
            if isinstance(source_worst, list)
            else list(reversed(ranked[-3:]))
        )
        coverage = deepcopy(dict(source_report.get("coverage", {})))
        insufficient = _insufficient_from_kpi(source_report)
        period_strategy = deepcopy(
            source_report.get("period_strategy")
            if isinstance(source_report.get("period_strategy"), dict)
            else {
                "mode": "unspecified",
                "reference_at": aggregation.get("as_of"),
            }
        )
        comparison = deepcopy(
            source_report.get("comparison")
            if isinstance(source_report.get("comparison"), dict)
            else {
                "available": False,
                "reason": "comparison_not_present_in_source_report",
            }
        )
        operational_metrics = deepcopy(
            source_report.get("operational_metrics")
            if isinstance(source_report.get("operational_metrics"), dict)
            else {
                name: _na("operational_metric_not_present_in_source_report")
                for name in (
                    "new_release_registrations",
                    "wordpress_published",
                    "x_post_success",
                    "failure_events",
                    "current_pending",
                )
            }
        )
        business_metrics = deepcopy(
            source_report.get("business_metrics")
            if isinstance(source_report.get("business_metrics"), dict)
            else {}
        )
    else:
        if report_type not in {"weekly", "monthly"}:
            raise XCoreAdvisoryContractError(
                "x_kpi_summary requires x_analytics_kpi_report_v1"
            )
        start, end = _period_from_legacy(source_report, report_type, legacy_timezone)
        generated_source = source_report.get("kpi_summary", {})
        generated_source = generated_source if isinstance(generated_source, dict) else {}
        as_of = _aware(generated_source.get("generated_at") or end.isoformat(), "as_of")
        timezone_name = legacy_timezone
        mode = "legacy_operational_report"
        basis = "operational_counts_not_x_metrics"
        overall_kpis = _unavailable_kpis("x_kpi_not_present_in_legacy_periodic_report")
        store_kpis = []
        post_type_kpis = []
        top_patterns = []
        bottom_patterns = []
        coverage = {
            "daily_report_count": int(source_report.get("daily_report_count", 0)),
            "legacy_operational_report": True,
        }
        insufficient = [
            {
                "scope": "overall",
                "metric": "all_x_kpis",
                "identity": None,
                "reason": "x_kpi_not_present_in_legacy_periodic_report",
                "sample_size": 0,
                "details": [],
            }
        ]
        period_strategy = {
            "mode": "calendar",
            "reference_at": as_of.isoformat(),
        }
        comparison = {
            "available": False,
            "reason": "comparison_not_present_in_legacy_periodic_report",
        }
        operational_metrics = {
            name: _na("operational_metric_not_present_in_legacy_periodic_report")
            for name in (
                "new_release_registrations",
                "wordpress_published",
                "x_post_success",
                "failure_events",
                "current_pending",
            )
        }
        business_metrics = {}

    period = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": timezone_name,
        "semantics": "half_open_start_inclusive_end_exclusive",
    }
    age_seconds = max(0, int((generated - as_of).total_seconds()))
    freshness = {
        "basis": "as_of",
        "status": "fresh" if age_seconds <= max_age_hours * 3600 else "stale",
        "age_seconds": age_seconds,
        "max_age_seconds": max_age_hours * 3600,
    }
    anomalies = _anomalies(source_report, freshness)
    recommended = _recommended_actions(source_report, period, anomalies, insufficient)
    source_digest = sha256_file(source_path)
    identifier_material = "\0".join(
        (report_type, generated.isoformat(), source_digest)
    )
    snapshot_id = "xadv-" + hashlib.sha256(
        identifier_material.encode("utf-8")
    ).hexdigest()[:24]
    report_id = str(
        source_report.get("report_id")
        or source_report.get("report_week")
        or source_report.get("report_month")
        or snapshot_id
    )
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "report_id": report_id,
        "report_type": report_type,
        "generated_at": generated.isoformat(),
        "as_of": as_of.isoformat(),
        "period": period,
        "measurement_basis": {
            "source_schema_version": source_schema,
            "mode": mode,
            "basis": basis,
            "recalculated": False,
        },
        "overall_kpis": overall_kpis,
        "store_kpis": store_kpis,
        "post_type_kpis": post_type_kpis,
        "top_patterns": top_patterns,
        "bottom_patterns": bottom_patterns,
        "anomalies": anomalies,
        "insufficient_data": insufficient,
        "recommended_actions": recommended,
        "evidence": {
            "source_references": [_source_reference(source_path, source_schema)],
            "source_content_treated_as_data": True,
            "source_content_treated_as_instruction": False,
        },
        "coverage": coverage,
        "freshness": freshness,
        "period_strategy": period_strategy,
        "comparison": comparison,
        "operational_metrics": operational_metrics,
        "business_metrics": business_metrics,
        "advisory_only": True,
        "safety": {
            "operation_mode": "OBSERVE",
            "database_write_allowed": False,
            "post_to_x_allowed": False,
            "wordpress_publish_allowed": False,
            "job_start_allowed": False,
            "automatic_change_allowed": False,
            "external_text_is_instruction": False,
        },
    }
    validate_advisory_snapshot(snapshot)
    return snapshot


def validate_advisory_snapshot(snapshot: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "snapshot_id", "report_id", "report_type",
        "generated_at", "as_of", "period", "measurement_basis",
        "overall_kpis", "store_kpis", "post_type_kpis", "top_patterns",
        "bottom_patterns", "anomalies", "insufficient_data",
        "recommended_actions", "evidence", "coverage", "freshness",
        "period_strategy", "comparison", "operational_metrics",
        "advisory_only", "safety",
    }
    missing = sorted(required - set(snapshot))
    if missing:
        raise XCoreAdvisoryContractError(f"snapshot fields missing: {missing}")
    allowed = required | {"business_metrics"}
    extra = sorted(set(snapshot) - allowed)
    if extra:
        raise XCoreAdvisoryContractError(f"snapshot fields unsupported: {extra}")
    if snapshot.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise XCoreAdvisoryContractError("snapshot schema_version is unsupported")
    if not re.fullmatch(r"xadv-[0-9a-f]{24}", str(snapshot.get("snapshot_id", ""))):
        raise XCoreAdvisoryContractError("snapshot_id is invalid")
    if snapshot.get("report_type") not in REPORT_TYPES:
        raise XCoreAdvisoryContractError("snapshot report_type is unsupported")
    if snapshot.get("advisory_only") is not True:
        raise XCoreAdvisoryContractError("snapshot must be advisory_only")
    generated_at = _aware(snapshot.get("generated_at"), "generated_at")
    as_of = _aware(snapshot.get("as_of"), "as_of")
    if as_of > generated_at:
        raise XCoreAdvisoryContractError("as_of must not be after generated_at")
    period = snapshot.get("period")
    if not isinstance(period, Mapping):
        raise XCoreAdvisoryContractError("period must be an object")
    start = _aware(period.get("start"), "period.start")
    end = _aware(period.get("end"), "period.end")
    if end <= start:
        raise XCoreAdvisoryContractError("period end must be after start")
    if period.get("semantics") != "half_open_start_inclusive_end_exclusive":
        raise XCoreAdvisoryContractError("period semantics is invalid")
    for field_name in (
        "overall_kpis", "measurement_basis", "evidence", "coverage",
        "freshness", "safety",
        "period_strategy", "comparison", "operational_metrics",
    ):
        if not isinstance(snapshot.get(field_name), Mapping):
            raise XCoreAdvisoryContractError(f"{field_name} must be an object")
    if (
        "business_metrics" in snapshot
        and not isinstance(
            snapshot.get("business_metrics"),
            Mapping,
        )
    ):
        raise XCoreAdvisoryContractError(
            "business_metrics must be an object"
        )
    for field_name in (
        "store_kpis", "post_type_kpis", "top_patterns", "bottom_patterns",
        "anomalies", "insufficient_data", "recommended_actions",
    ):
        if not isinstance(snapshot.get(field_name), list):
            raise XCoreAdvisoryContractError(f"{field_name} must be an array")
    basis = snapshot["measurement_basis"]
    if basis.get("recalculated") is not False:
        raise XCoreAdvisoryContractError("Phase 4 must not recalculate KPI")
    safety = snapshot["safety"]
    expected_safety = {
        "operation_mode": "OBSERVE",
        "database_write_allowed": False,
        "post_to_x_allowed": False,
        "wordpress_publish_allowed": False,
        "job_start_allowed": False,
        "automatic_change_allowed": False,
        "external_text_is_instruction": False,
    }
    if dict(safety) != expected_safety:
        raise XCoreAdvisoryContractError("snapshot safety contract is invalid")
    missing_kpis = sorted(set(KPI_NAMES) - set(snapshot["overall_kpis"]))
    if missing_kpis:
        raise XCoreAdvisoryContractError(
            f"overall_kpis fields missing: {missing_kpis}"
        )
    for metric_name, metric in snapshot["overall_kpis"].items():
        if not isinstance(metric, Mapping):
            raise XCoreAdvisoryContractError(
                f"overall_kpis.{metric_name} must be an object"
            )
        if metric.get("value") is None and not str(metric.get("reason") or "").strip():
            raise XCoreAdvisoryContractError(
                f"overall_kpis.{metric_name} null value requires reason"
            )
        if metric_name in {"epc", "rpmi"} and metric.get("value") is not None and not metric.get("currency"):
            raise XCoreAdvisoryContractError(f"{metric_name} requires currency")
    for action in snapshot["recommended_actions"]:
        if not isinstance(action, Mapping):
            raise XCoreAdvisoryContractError("recommended action must be an object")
        if action.get("advisory_only") is not True or action.get("execution_allowed") is not False:
            raise XCoreAdvisoryContractError("recommended action must be non-executable")
        if any(key in action for key in ("command", "argv", "shell", "execute")):
            raise XCoreAdvisoryContractError("recommended action contains an execution field")
        for key in ("rule_id", "rationale", "target_period", "sample_size", "constraints"):
            if key not in action:
                raise XCoreAdvisoryContractError(f"recommended action missing {key}")
        if not isinstance(action.get("rationale"), Mapping):
            raise XCoreAdvisoryContractError(
                "recommended action rationale must be an object"
            )
        if action.get("target_period") != period:
            raise XCoreAdvisoryContractError(
                "recommended action period mismatch"
            )
        if (
            not isinstance(action.get("sample_size"), int)
            or action["sample_size"] < 0
        ):
            raise XCoreAdvisoryContractError(
                "recommended action sample_size is invalid"
            )
        constraints = action.get("constraints")
        if not isinstance(constraints, list) or not set(
            SAFE_ACTION_CONSTRAINTS
        ).issubset(set(constraints)):
            raise XCoreAdvisoryContractError(
                "recommended action safety constraints are incomplete"
            )
    for field_name in ("top_patterns", "bottom_patterns"):
        for pattern in snapshot[field_name]:
            if not isinstance(pattern, Mapping) or pattern.get("status") != "eligible":
                raise XCoreAdvisoryContractError(
                    f"{field_name} may contain eligible patterns only"
                )
    for field_name in ("store_kpis", "post_type_kpis"):
        for row in snapshot[field_name]:
            required_group_fields = {
                "group", "group_key", "post_count", "unit_count", "kpis"
            }
            if (
                not isinstance(row, Mapping)
                or not required_group_fields.issubset(row)
            ):
                raise XCoreAdvisoryContractError(
                    f"{field_name} item structure is invalid"
                )
            if int(row["post_count"]) < 0 or int(row["unit_count"]) < 0:
                raise XCoreAdvisoryContractError(
                    f"{field_name} counts must be non-negative"
                )
    allowed_anomaly_types = {
        "missing_data",
        "duplicate_suspected",
        "counter_decrease",
        "stale_data",
    }
    for anomaly in snapshot["anomalies"]:
        required_anomaly_fields = {
            "rule_id", "type", "severity", "count", "evidence_field"
        }
        if (
            not isinstance(anomaly, Mapping)
            or not required_anomaly_fields.issubset(anomaly)
        ):
            raise XCoreAdvisoryContractError("anomaly structure is invalid")
        if anomaly.get("type") not in allowed_anomaly_types:
            raise XCoreAdvisoryContractError("anomaly type is invalid")
        if anomaly.get("severity") not in {"warning", "error"}:
            raise XCoreAdvisoryContractError("anomaly severity is invalid")
        if (
            not isinstance(anomaly.get("count"), int)
            or anomaly["count"] < 1
        ):
            raise XCoreAdvisoryContractError("anomaly count is invalid")
    for item in snapshot["insufficient_data"]:
        required_insufficient_fields = {
            "scope", "metric", "identity", "reason", "sample_size", "details"
        }
        if (
            not isinstance(item, Mapping)
            or not required_insufficient_fields.issubset(item)
        ):
            raise XCoreAdvisoryContractError(
                "insufficient_data structure is invalid"
            )
        if item.get("scope") not in {"overall", "pattern"}:
            raise XCoreAdvisoryContractError(
                "insufficient_data scope is invalid"
            )
        if not str(item.get("reason") or "").strip():
            raise XCoreAdvisoryContractError(
                "insufficient_data reason is required"
            )
        if (
            not isinstance(item.get("sample_size"), int)
            or item["sample_size"] < 0
        ):
            raise XCoreAdvisoryContractError(
                "insufficient_data sample_size is invalid"
            )
        if not isinstance(item.get("details"), list):
            raise XCoreAdvisoryContractError(
                "insufficient_data details must be an array"
            )
        if (
            item.get("scope") == "pattern"
            and not str(item.get("identity") or "").strip()
        ):
            raise XCoreAdvisoryContractError(
                "pattern insufficient_data requires identity"
            )
    evidence = snapshot["evidence"]
    references = evidence.get("source_references")
    if not isinstance(references, list) or not references:
        raise XCoreAdvisoryContractError("evidence source_references is required")
    for reference in references:
        if (
            not isinstance(reference, Mapping)
            or not str(reference.get("path") or "").strip()
            or not str(reference.get("schema_version") or "").strip()
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(reference.get("sha256", ""))
            )
        ):
            raise XCoreAdvisoryContractError("evidence sha256 is invalid")
    if (
        evidence.get("source_content_treated_as_data") is not True
        or evidence.get("source_content_treated_as_instruction") is not False
    ):
        raise XCoreAdvisoryContractError(
            "external source content handling is invalid"
        )
    freshness = snapshot["freshness"]
    if freshness.get("status") not in {"fresh", "stale"}:
        raise XCoreAdvisoryContractError("freshness status is invalid")
    if (
        not isinstance(freshness.get("age_seconds"), int)
        or not isinstance(freshness.get("max_age_seconds"), int)
        or freshness.get("age_seconds", -1) < 0
        or freshness.get("max_age_seconds", 0) <= 0
    ):
        raise XCoreAdvisoryContractError("freshness age values are invalid")


def validate_manifest(manifest: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "generated_at", "advisory_only", "latest", "snapshots"
    }
    if set(manifest) != required:
        raise XCoreAdvisoryContractError("manifest fields are invalid")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise XCoreAdvisoryContractError("manifest schema_version is unsupported")
    if manifest.get("advisory_only") is not True:
        raise XCoreAdvisoryContractError("manifest must be advisory_only")
    _aware(manifest.get("generated_at"), "manifest.generated_at")
    latest = manifest.get("latest")
    if not isinstance(latest, Mapping) or set(latest) != REPORT_TYPES:
        raise XCoreAdvisoryContractError("manifest latest keys are invalid")
    snapshots = manifest.get("snapshots")
    if not isinstance(snapshots, list):
        raise XCoreAdvisoryContractError("manifest snapshots must be an array")
    seen: set[str] = set()
    for reference in snapshots:
        if not isinstance(reference, Mapping):
            raise XCoreAdvisoryContractError("manifest reference must be an object")
        snapshot_id = str(reference.get("snapshot_id", ""))
        if not snapshot_id or snapshot_id in seen:
            raise XCoreAdvisoryContractError("manifest snapshot IDs must be unique")
        seen.add(snapshot_id)
        if reference.get("report_type") not in REPORT_TYPES:
            raise XCoreAdvisoryContractError("manifest report_type is invalid")
        if reference.get("status") != "VALID":
            raise XCoreAdvisoryContractError("manifest may reference VALID snapshots only")
        for field_name in (
            "snapshot_id", "report_id", "report_type", "path", "sha256",
            "generated_at", "as_of", "status",
        ):
            if field_name not in reference:
                raise XCoreAdvisoryContractError(
                    f"manifest reference missing {field_name}"
                )
        if not re.fullmatch(r"[0-9a-f]{64}", str(reference.get("sha256", ""))):
            raise XCoreAdvisoryContractError("manifest sha256 is invalid")
    for report_type, reference in latest.items():
        if reference is None:
            continue
        if not isinstance(reference, Mapping) or reference.get("report_type") != report_type:
            raise XCoreAdvisoryContractError("manifest latest reference is invalid")
        if str(reference.get("snapshot_id", "")) not in seen:
            raise XCoreAdvisoryContractError("manifest latest snapshot is absent from history")