from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import load_latest_kpi_snapshot


DAILY_REPORT_PATTERN = re.compile(r"^daily_report_(\d{8})\.json$")


def _normalize_month(month_str: str) -> str:
    text = month_str.strip()
    if len(text) == 7 and text[4] == "-":
        text = text.replace("-", "")
    if len(text) != 6 or not text.isdigit():
        raise ValueError(f"month は YYYYMM または YYYY-MM 形式で指定してください: {month_str}")
    return text


def _load_daily_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"daily_report JSON が不正です: {path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"daily_report の読み込みに失敗しました: {path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"daily_report の形式が不正です: {path}")
    return payload


def list_daily_reports_for_month(report_dir: Path, month_str: str) -> list[dict[str, Any]]:
    """指定月の daily_report_YYYYMMDD.json を読み込んで返す。"""
    month = _normalize_month(month_str)

    if not report_dir.exists() or not report_dir.is_dir():
        return []

    selected: list[tuple[str, Path]] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = DAILY_REPORT_PATTERN.match(path.name)
        if not matched:
            continue
        report_date = matched.group(1)
        if report_date.startswith(month):
            selected.append((report_date, path))

    selected.sort(key=lambda x: x[0])
    return [_load_daily_report(path) for _, path in selected]


def _as_int(report: dict[str, Any], key: str) -> int:
    try:
        return int(report.get(key, 0))
    except (TypeError, ValueError):
        return 0


def _top_slug_counts(slugs: list[str], top_n: int = 10) -> list[dict[str, Any]]:
    counter = Counter(slugs)
    return [{"slug": slug, "count": count} for slug, count in counter.most_common(top_n)]


def attach_kpi_summary(report: dict[str, Any], snapshot: dict | None) -> dict[str, Any]:
    """最新KPI snapshotの要約を report に付与する。"""
    snap = snapshot or {}
    report["kpi_summary"] = {
        "generated_at": snap.get("generated_at"),
        "health_score": snap.get("health_score", "N/A"),
        "health_grade": snap.get("health_grade", "N/A"),
        "anomaly_overall": snap.get("anomaly_overall", "N/A"),
        "alert_total": snap.get("alert_total", 0),
        "retry_queued_count": snap.get("retry_queued_count", 0),
        "latest_archive": snap.get("latest_archive"),
    }
    return report


def build_monthly_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """日次レポート群を月次レポートに集約する。"""
    if not reports:
        raise ValueError("集約対象の日次レポートがありません")

    month = str(reports[0].get("report_date", ""))[:6]

    total_success_count = 0
    total_skipped_count = 0
    total_failed_count = 0
    total_draft_count = 0
    total_retry_queued_count = 0
    total_combined_count = 0
    total_price_only_count = 0
    total_release_only_count = 0

    failed_slug_all: list[str] = []
    skipped_slug_all: list[str] = []

    for report in reports:
        total_success_count += _as_int(report, "success_count")
        total_skipped_count += _as_int(report, "skipped_count")
        total_failed_count += _as_int(report, "failed_count")
        total_draft_count += _as_int(report, "draft_count")
        total_retry_queued_count += _as_int(report, "retry_queued_count")
        total_combined_count += _as_int(report, "combined_count")
        total_price_only_count += _as_int(report, "price_only_count")
        total_release_only_count += _as_int(report, "release_only_count")

        failed_slugs = report.get("failed_slugs", [])
        if isinstance(failed_slugs, list):
            failed_slug_all.extend(str(slug) for slug in failed_slugs if slug)

        skipped_slugs = report.get("skipped_slugs", [])
        if isinstance(skipped_slugs, list):
            skipped_slug_all.extend(str(slug) for slug in skipped_slugs if slug)

    report = {
        "report_month": month,
        "daily_report_count": len(reports),
        "total_success_count": total_success_count,
        "total_skipped_count": total_skipped_count,
        "total_failed_count": total_failed_count,
        "total_draft_count": total_draft_count,
        "total_retry_queued_count": total_retry_queued_count,
        "total_combined_count": total_combined_count,
        "total_price_only_count": total_price_only_count,
        "total_release_only_count": total_release_only_count,
        "top_failed_slugs": _top_slug_counts(failed_slug_all, top_n=10),
        "top_skipped_slugs": _top_slug_counts(skipped_slug_all, top_n=10),
    }
    return attach_kpi_summary(report, load_latest_kpi_snapshot())
