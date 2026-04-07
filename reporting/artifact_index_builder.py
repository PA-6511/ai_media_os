from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = BASE_DIR / "data" / "reports"
DEFAULT_ARCHIVE_DIR = BASE_DIR / "data" / "archives"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_list_files(path: Path) -> list[Path]:
    if not path.exists() or not path.is_dir():
        return []
    return sorted([p for p in path.iterdir() if p.is_file()], key=lambda p: p.name)


def find_latest_matching(paths: list[Path]) -> str | None:
    """候補群から更新時刻が最大のファイルパス文字列を返す。"""
    if not paths:
        return None

    latest = max(paths, key=lambda p: (p.stat().st_mtime, p.name))
    return str(latest)


def _path_info(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    stat = path.stat()
    return {
        "path": str(path),
        "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
    }


def _latest_info(paths: list[Path]) -> dict[str, Any] | None:
    latest_str = find_latest_matching(paths)
    if latest_str is None:
        return None
    return _path_info(Path(latest_str))


def detect_latest_release_readiness_json(report_files: list[Path]) -> str | None:
    candidates = [p for p in report_files if p.name == "release_readiness_latest.json"]
    return find_latest_matching(candidates)


def detect_latest_release_readiness_md(report_files: list[Path]) -> str | None:
    candidates = [p for p in report_files if p.name == "release_readiness_latest.md"]
    return find_latest_matching(candidates)


def detect_latest_ops_decision_dashboard(report_files: list[Path]) -> str | None:
    candidates = [p for p in report_files if p.name == "ops_decision_dashboard_latest.html"]
    return find_latest_matching(candidates)


def build_artifact_index(report_dir: Path, archive_dir: Path) -> dict:
    """reports/archives を分類し、最新成果物と件数のメタ一覧を返す。"""
    report_files = _safe_list_files(report_dir)
    archive_files = _safe_list_files(archive_dir)

    daily_json = [
        p
        for p in report_files
        if p.name.startswith("daily_report_") and p.name.endswith(".json") and len(p.stem) == 21
    ]
    daily_txt = [
        p
        for p in report_files
        if p.name.startswith("daily_report_") and p.name.endswith(".txt") and len(p.stem) == 21
    ]
    monthly_json = [
        p
        for p in report_files
        if p.name.startswith("monthly_report_") and p.name.endswith(".json") and len(p.stem) == 21
    ]
    monthly_txt = [
        p
        for p in report_files
        if p.name.startswith("monthly_report_") and p.name.endswith(".txt") and len(p.stem) == 21
    ]
    dashboard = [p for p in report_files if p.name == "dashboard_latest.html"]
    monthly_dashboard = [p for p in report_files if p.name == "monthly_dashboard_latest.html"]
    weekly_dashboard = [p for p in report_files if p.name == "weekly_dashboard_latest.html"]
    weekly_json = [
        p
        for p in report_files
        if p.name.startswith("weekly_report_") and p.name.endswith(".json")
    ]
    weekly_txt = [
        p
        for p in report_files
        if p.name.startswith("weekly_report_") and p.name.endswith(".txt")
    ]
    ops_decision_dashboard = [
        p
        for p in report_files
        if p.name == "ops_decision_dashboard_latest.html"
    ]
    release_readiness_json = [p for p in report_files if p.name == "release_readiness_latest.json"]
    release_readiness_md = [p for p in report_files if p.name == "release_readiness_latest.md"]
    archives = [
        p
        for p in archive_files
        if p.name.startswith("ops_archive_") and p.name.endswith(".zip")
    ]

    latest_daily_json = find_latest_matching(daily_json)
    latest_daily_txt = find_latest_matching(daily_txt)
    latest_monthly_json = find_latest_matching(monthly_json)
    latest_monthly_txt = find_latest_matching(monthly_txt)
    latest_weekly_json = find_latest_matching(weekly_json)
    latest_weekly_txt = find_latest_matching(weekly_txt)
    latest_dashboard = find_latest_matching(dashboard)
    latest_monthly_dashboard = find_latest_matching(monthly_dashboard)
    latest_weekly_dashboard = find_latest_matching(weekly_dashboard)
    latest_release_readiness_json = detect_latest_release_readiness_json(report_files)
    latest_release_readiness_md = detect_latest_release_readiness_md(report_files)
    latest_ops_decision_dashboard = detect_latest_ops_decision_dashboard(report_files)
    latest_archive = find_latest_matching(archives)

    return {
        "generated_at": _now_iso(),
        "report_dir": str(report_dir),
        "archive_dir": str(archive_dir),
        "latest_daily_report_json": latest_daily_json,
        "latest_daily_report_txt": latest_daily_txt,
        "latest_weekly_report_json": latest_weekly_json,
        "latest_weekly_report_txt": latest_weekly_txt,
        "latest_monthly_report_json": latest_monthly_json,
        "latest_monthly_report_txt": latest_monthly_txt,
        "latest_dashboard": latest_dashboard,
        "latest_weekly_dashboard": latest_weekly_dashboard,
        "latest_monthly_dashboard": latest_monthly_dashboard,
        "latest_ops_decision_dashboard": latest_ops_decision_dashboard,
        "latest_release_readiness_json": latest_release_readiness_json,
        "latest_release_readiness_md": latest_release_readiness_md,
        "latest_archive": latest_archive,
        "daily_report_count": len(daily_json),
        "weekly_report_count": len(weekly_json),
        "monthly_report_count": len(monthly_json),
        "archive_count": len(archives),
        "details": {
            "latest_daily_report_json": _latest_info(daily_json),
            "latest_daily_report_txt": _latest_info(daily_txt),
            "latest_weekly_report_json": _latest_info(weekly_json),
            "latest_weekly_report_txt": _latest_info(weekly_txt),
            "latest_monthly_report_json": _latest_info(monthly_json),
            "latest_monthly_report_txt": _latest_info(monthly_txt),
            "latest_dashboard": _latest_info(dashboard),
            "latest_weekly_dashboard": _latest_info(weekly_dashboard),
            "latest_monthly_dashboard": _latest_info(monthly_dashboard),
            "latest_ops_decision_dashboard": _latest_info(ops_decision_dashboard),
            "latest_release_readiness_json": _latest_info(release_readiness_json),
            "latest_release_readiness_md": _latest_info(release_readiness_md),
            "latest_archive": _latest_info(archives),
        },
    }