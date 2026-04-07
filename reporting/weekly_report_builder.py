from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from monitoring.kpi_snapshot_reader import load_latest_kpi_snapshot


DAILY_REPORT_PATTERN = re.compile(r"^daily_report_(\d{8})\.json$")
WEEK_PATTERN = re.compile(r"^(\d{4})W(\d{2})$")


def _normalize_week(week_str: str) -> str:
    text = week_str.strip().upper()
    text = text.replace("-", "")
    matched = WEEK_PATTERN.match(text)
    if not matched:
        raise ValueError(f"week は YYYYWww または YYYY-Www 形式で指定してください: {week_str}")

    year = int(matched.group(1))
    week = int(matched.group(2))
    if week < 1 or week > 53:
        raise ValueError(f"week の週番号が不正です: {week_str}")

    # ISO週の妥当性チェック。存在しない週(例: 2021W53)を弾く。
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise ValueError(f"存在しない ISO week です: {week_str}") from exc

    return f"{year:04d}W{week:02d}"


def _date_to_week_key(report_date: str) -> str:
    d = date(int(report_date[:4]), int(report_date[4:6]), int(report_date[6:8]))
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year:04d}W{iso_week:02d}"


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


def detect_latest_week(report_dir: Path) -> str:
    """daily_report から最新週(YYYYWww)を検出する。"""
    if not report_dir.exists() or not report_dir.is_dir():
        raise FileNotFoundError(f"レポートディレクトリが見つかりません: {report_dir}")

    weeks: list[str] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = DAILY_REPORT_PATTERN.match(path.name)
        if not matched:
            continue
        weeks.append(_date_to_week_key(matched.group(1)))

    if not weeks:
        raise FileNotFoundError("daily_report_*.json が見つかりません")

    return sorted(weeks)[-1]


def list_daily_reports_for_week(report_dir: Path, week_str: str) -> list[dict[str, Any]]:
    """指定週の daily_report_YYYYMMDD.json を読み込んで返す。"""
    week = _normalize_week(week_str)

    if not report_dir.exists() or not report_dir.is_dir():
        return []

    selected: list[tuple[str, Path]] = []
    for path in report_dir.glob("daily_report_*.json"):
        matched = DAILY_REPORT_PATTERN.match(path.name)
        if not matched:
            continue
        report_date = matched.group(1)
        if _date_to_week_key(report_date) == week:
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


def build_weekly_report(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """日次レポート群を週次レポートに集約する。"""
    if not reports:
        raise ValueError("集約対象の日次レポートがありません")

    first_date = str(reports[0].get("report_date", "")).replace("-", "")
    if len(first_date) != 8 or not first_date.isdigit():
        raise ValueError("先頭日次レポートの report_date が不正です")
    report_week = _date_to_week_key(first_date)

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
        "report_week": report_week,
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
