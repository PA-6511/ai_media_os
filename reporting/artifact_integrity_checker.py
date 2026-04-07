from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from reporting.artifact_index_builder import (
    DEFAULT_ARCHIVE_DIR,
    DEFAULT_REPORT_DIR,
    build_artifact_index,
)


CHECK_LEVEL_PASS = "PASS"
CHECK_LEVEL_WARNING = "WARNING"
CHECK_LEVEL_FAIL = "FAIL"


def _result(
    *,
    check: str,
    level: str,
    message: str,
    target: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check": check,
        "level": level,
        "message": message,
        "target": target,
        "details": details or {},
    }


def check_artifact_index_paths(index: dict) -> list[dict]:
    """artifact index の latest path が実在するか確認する。"""
    checks = [
        "latest_daily_report_json",
        "latest_daily_report_txt",
        "latest_monthly_report_json",
        "latest_monthly_report_txt",
        "latest_dashboard",
        "latest_monthly_dashboard",
        "latest_archive",
    ]

    results: list[dict] = []
    for key in checks:
        path_value = index.get(key)
        check_name = f"artifact_index.{key}.exists"
        if not path_value:
            results.append(
                _result(
                    check=check_name,
                    level=CHECK_LEVEL_WARNING,
                    message=f"index key is empty: {key}",
                    target=None,
                )
            )
            continue

        path = Path(str(path_value))
        if path.exists() and path.is_file():
            results.append(
                _result(
                    check=check_name,
                    level=CHECK_LEVEL_PASS,
                    message="path exists",
                    target=str(path),
                )
            )
        else:
            results.append(
                _result(
                    check=check_name,
                    level=CHECK_LEVEL_FAIL,
                    message="path does not exist",
                    target=str(path),
                )
            )

    artifact_html_path = Path(str(index.get("report_dir", DEFAULT_REPORT_DIR))) / "artifact_index_latest.html"
    if artifact_html_path.exists() and artifact_html_path.is_file():
        results.append(
            _result(
                check="artifact_index_latest_html.exists",
                level=CHECK_LEVEL_PASS,
                message="artifact_index_latest.html exists",
                target=str(artifact_html_path),
            )
        )
    else:
        results.append(
            _result(
                check="artifact_index_latest_html.exists",
                level=CHECK_LEVEL_WARNING,
                message="artifact_index_latest.html is missing",
                target=str(artifact_html_path),
            )
        )

    return results


def check_daily_report_consistency(path: Path) -> list[dict]:
    """daily_report の report_date とファイル名整合性を確認する。"""
    check_name = "daily_report.report_date_matches_filename"
    if not path.exists() or not path.is_file():
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message="daily report json is missing",
                target=str(path),
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message=f"failed to parse json: {exc}",
                target=str(path),
            )
        ]

    filename_date = path.stem.replace("daily_report_", "", 1)
    report_date = str(payload.get("report_date", "")).replace("-", "")

    if filename_date and report_date and filename_date == report_date:
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_PASS,
                message="report_date matches filename",
                target=str(path),
                details={"filename_date": filename_date, "report_date": report_date},
            )
        ]

    return [
        _result(
            check=check_name,
            level=CHECK_LEVEL_FAIL,
            message="report_date does not match filename",
            target=str(path),
            details={"filename_date": filename_date, "report_date": report_date},
        )
    ]


def check_monthly_report_consistency(path: Path) -> list[dict]:
    """monthly_report の report_month とファイル名整合性を確認する。"""
    check_name = "monthly_report.report_month_matches_filename"
    if not path.exists() or not path.is_file():
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_WARNING,
                message="monthly report json is missing",
                target=str(path),
            )
        ]

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message=f"failed to parse json: {exc}",
                target=str(path),
            )
        ]

    filename_month = path.stem.replace("monthly_report_", "", 1)
    report_month = str(payload.get("report_month", "")).replace("-", "")

    if filename_month and report_month and filename_month == report_month:
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_PASS,
                message="report_month matches filename",
                target=str(path),
                details={"filename_month": filename_month, "report_month": report_month},
            )
        ]

    return [
        _result(
            check=check_name,
            level=CHECK_LEVEL_FAIL,
            message="report_month does not match filename",
            target=str(path),
            details={"filename_month": filename_month, "report_month": report_month},
        )
    ]


def check_dashboard_references_latest_daily(dashboard_path: Path, daily_json_path: Path) -> list[dict]:
    """dashboard_latest.html が最新 daily_report を参照しているか確認する。"""
    check_name = "dashboard.references_latest_daily_report"

    if not dashboard_path.exists() or not dashboard_path.is_file():
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message="dashboard_latest.html is missing",
                target=str(dashboard_path),
            )
        ]

    if not daily_json_path.exists() or not daily_json_path.is_file():
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_WARNING,
                message="latest daily json is missing; skipped dashboard reference check",
                target=str(daily_json_path),
            )
        ]

    try:
        daily_payload = json.loads(daily_json_path.read_text(encoding="utf-8"))
        report_date = str(daily_payload.get("report_date", "")).strip()
        dashboard_html = dashboard_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message=f"failed to read dashboard or daily report: {exc}",
                target=str(dashboard_path),
            )
        ]

    if not report_date:
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message="latest daily report has empty report_date",
                target=str(daily_json_path),
            )
        ]

    if report_date in dashboard_html:
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_PASS,
                message="dashboard contains latest report_date",
                target=str(dashboard_path),
                details={"report_date": report_date},
            )
        ]

    return [
        _result(
            check=check_name,
            level=CHECK_LEVEL_FAIL,
            message="dashboard does not contain latest report_date",
            target=str(dashboard_path),
            details={"report_date": report_date},
        )
    ]


def check_archive_minimum_contents(path: Path) -> list[dict]:
    """archive に reports/logs/db が含まれるか確認する。"""
    check_name = "archive.minimum_contents"

    if not path.exists() or not path.is_file():
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_WARNING,
                message="latest archive is missing",
                target=str(path),
            )
        ]

    try:
        with ZipFile(path, "r") as zf:
            names = zf.namelist()
    except Exception as exc:  # noqa: BLE001
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_FAIL,
                message=f"failed to open zip: {exc}",
                target=str(path),
            )
        ]

    has_reports = any(name.startswith("data/reports/") for name in names)
    has_logs = any(name.startswith("data/logs/") for name in names)
    has_db = any(name.startswith("data/") and name.endswith(".db") for name in names)

    missing: list[str] = []
    if not has_reports:
        missing.append("data/reports/*")
    if not has_logs:
        missing.append("data/logs/*")
    if not has_db:
        missing.append("data/*.db")

    if not missing:
        return [
            _result(
                check=check_name,
                level=CHECK_LEVEL_PASS,
                message="archive includes minimum required contents",
                target=str(path),
            )
        ]

    return [
        _result(
            check=check_name,
            level=CHECK_LEVEL_FAIL,
            message="archive missing minimum contents",
            target=str(path),
            details={"missing": missing},
        )
    ]


def _summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    pass_count = sum(1 for c in checks if c.get("level") == CHECK_LEVEL_PASS)
    warning_count = sum(1 for c in checks if c.get("level") == CHECK_LEVEL_WARNING)
    fail_count = sum(1 for c in checks if c.get("level") == CHECK_LEVEL_FAIL)

    overall = CHECK_LEVEL_PASS
    if fail_count > 0:
        overall = CHECK_LEVEL_FAIL
    elif warning_count > 0:
        overall = CHECK_LEVEL_WARNING

    return {
        "total": len(checks),
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "overall": overall,
    }


def run_integrity_checks() -> dict:
    """成果物の整合性チェックを横断実行する。"""
    index = build_artifact_index(report_dir=DEFAULT_REPORT_DIR, archive_dir=DEFAULT_ARCHIVE_DIR)

    checks: list[dict[str, Any]] = []
    checks.extend(check_artifact_index_paths(index))

    latest_daily_json = Path(str(index.get("latest_daily_report_json"))) if index.get("latest_daily_report_json") else DEFAULT_REPORT_DIR / "daily_report_missing.json"
    latest_monthly_json = Path(str(index.get("latest_monthly_report_json"))) if index.get("latest_monthly_report_json") else DEFAULT_REPORT_DIR / "monthly_report_missing.json"
    latest_dashboard = Path(str(index.get("latest_dashboard"))) if index.get("latest_dashboard") else DEFAULT_REPORT_DIR / "dashboard_latest.html"
    latest_archive = Path(str(index.get("latest_archive"))) if index.get("latest_archive") else DEFAULT_ARCHIVE_DIR / "ops_archive_missing.zip"

    checks.extend(check_daily_report_consistency(latest_daily_json))
    checks.extend(check_monthly_report_consistency(latest_monthly_json))
    checks.extend(check_dashboard_references_latest_daily(latest_dashboard, latest_daily_json))
    checks.extend(check_archive_minimum_contents(latest_archive))

    summary = _summarize(checks)

    return {
        "summary": summary,
        "artifact_index": index,
        "checks": checks,
    }
