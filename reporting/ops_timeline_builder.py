from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from reporting.artifact_index_builder import BASE_DIR, DEFAULT_ARCHIVE_DIR, DEFAULT_REPORT_DIR


DEFAULT_LOG_DIR = BASE_DIR / "data" / "logs"
DEFAULT_OPS_CYCLE_LOG_PATH = DEFAULT_LOG_DIR / "ops_cycle.log"
DEFAULT_ANOMALY_LOG_PATH = DEFAULT_LOG_DIR / "anomaly_check.log"
DEFAULT_SMOKE_LOG_PATH = DEFAULT_LOG_DIR / "smoke_test.log"
SCHEMA_VERSION = "1.0"
LOCAL_LOG_TZ = timezone(timedelta(hours=9))

STEP_TITLE_MAP = {
    "ops_cycle": "Ops cycle completed",
    "smoke_test": "Smoke test completed",
    "anomaly_check": "Anomaly check completed",
    "archive_backup": "Archive backup created",
    "release_readiness_check": "Release readiness generated",
    "daily_report": "Daily report generated",
    "dashboard_build": "Daily dashboard generated",
    "weekly_report_build": "Weekly report generated",
    "weekly_dashboard_build": "Weekly dashboard generated",
    "monthly_report": "Monthly report generated",
    "monthly_dashboard": "Monthly dashboard generated",
}

IMPORTANT_STEPS = {
    "smoke_test",
    "anomaly_check",
    "archive_backup",
    "release_readiness_check",
    "daily_report",
    "dashboard_build",
    "weekly_report_build",
    "weekly_dashboard_build",
    "monthly_report",
    "monthly_dashboard",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _latest_log_snapshot(primary_path: Path) -> tuple[Path | None, str]:
    directory = primary_path.parent
    pattern = f"{primary_path.name}*"

    if not directory.exists() or not directory.is_dir():
        return None, ""

    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None, ""

    candidates.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
    for path in candidates:
        text = _safe_read_text(path)
        if text.strip():
            return path, text

    latest = candidates[0]
    return latest, ""


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _event(
    *,
    timestamp: str,
    category: str,
    status: str,
    title: str,
    detail: str,
    source: str | None = None,
) -> dict[str, Any]:
    payload = {
        "timestamp": timestamp,
        "category": category,
        "status": status,
        "title": title,
        "detail": detail,
    }
    if source:
        payload["source"] = source
    return payload


def _file_event(path: Path, category: str, status: str, title: str, detail: str) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    return _event(
        timestamp=timestamp,
        category=category,
        status=status,
        title=title,
        detail=detail,
        source=_normalize_path(path),
    )


def _latest_matching(directory: Path, pattern: str) -> Path | None:
    if not directory.exists() or not directory.is_dir():
        return None
    candidates = [path for path in directory.glob(pattern) if path.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.stat().st_mtime, path.name))


def _extract_final_summary(text: str) -> dict[str, Any]:
    if "FINAL SUMMARY" not in text:
        return {}
    summary_text = text.split("FINAL SUMMARY", 1)[1].strip()
    if not summary_text:
        return {}
    try:
        return json.loads(summary_text)
    except Exception:
        return {}


def _parse_ops_cycle_events(text: str) -> list[dict[str, Any]]:
    if not text:
        return []

    events: list[dict[str, Any]] = []
    header_match = re.search(r"^timestamp:\s*(.+)$", text, flags=re.MULTILINE)
    summary = _extract_final_summary(text)
    if header_match and summary:
        timestamp = header_match.group(1).strip()
        events.append(
            _event(
                timestamp=timestamp,
                category="ops_cycle",
                status=str(summary.get("overall") or "UNKNOWN"),
                title=STEP_TITLE_MAP["ops_cycle"],
                detail=f"PASS={summary.get('pass_count', 0)} FAIL={summary.get('fail_count', 0)} TOTAL={summary.get('total', 0)}",
                source=_normalize_path(DEFAULT_OPS_CYCLE_LOG_PATH),
            )
        )

    step_pattern = re.compile(
        r"\[(?P<index>\d+)\]\sstep:\s(?P<name>[^\n]+)\n"
        r"timestamp_start:\s(?P<start>[^\n]*)\n"
        r"timestamp_end:\s(?P<end>[^\n]*)\n"
        r"returncode:\s(?P<returncode>[^\n]*)\n"
        r"status:\s(?P<status>[^\n]*)\n"
        r"cmd:\s(?P<cmd>[^\n]*)",
        flags=re.MULTILINE,
    )

    for match in step_pattern.finditer(text):
        name = match.group("name").strip()
        if name not in IMPORTANT_STEPS:
            continue
        timestamp = match.group("end").strip()
        status = match.group("status").strip()
        cmd = match.group("cmd").strip()
        title = STEP_TITLE_MAP.get(name, name.replace("_", " ").title())
        events.append(
            _event(
                timestamp=timestamp,
                category=name,
                status=status,
                title=title,
                detail=f"cmd={cmd}",
                source=_normalize_path(DEFAULT_OPS_CYCLE_LOG_PATH),
            )
        )

    return events


def _parse_anomaly_events(text: str, source_path: Path | None = None) -> list[dict[str, Any]]:
    if not text:
        return []

    matches = re.findall(
        r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \| INFO \| monitoring\.anomaly_check \| anomaly_check finished overall=(?P<overall>\w+) alerts=(?P<alerts>\d+) warning=(?P<warning>\d+) critical=(?P<critical>\d+) latest_report=(?P<report>\S+) smoke_failed_count=(?P<smoke>\d+)$",
        text,
        flags=re.MULTILINE,
    )
    if not matches:
        return []

    timestamp_raw, overall, alerts, warning, critical, report, smoke = matches[-1]
    timestamp = (
        datetime.strptime(timestamp_raw, "%Y-%m-%d %H:%M:%S,%f")
        .replace(tzinfo=LOCAL_LOG_TZ)
        .astimezone(timezone.utc)
        .isoformat()
    )
    return [
        _event(
            timestamp=timestamp,
            category="anomaly_check",
            status=overall,
            title="Anomaly check completed",
            detail=f"alerts={alerts} warning={warning} critical={critical} smoke_failed={smoke} report={report}",
            source=_normalize_path(source_path or DEFAULT_ANOMALY_LOG_PATH),
        )
    ]


def _artifact_events() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    mappings = [
        (_latest_matching(DEFAULT_ARCHIVE_DIR, "ops_archive_*.zip"), "archive", "PASS", "Archive backup created", "Latest archive snapshot"),
        (_latest_matching(DEFAULT_REPORT_DIR, "daily_report_*.json"), "report", "PASS", "Daily report generated", "Latest daily report artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "weekly_report_*.json"), "report", "PASS", "Weekly report generated", "Latest weekly report artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "monthly_report_*.json"), "report", "PASS", "Monthly report generated", "Latest monthly report artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "dashboard_latest.html"), "dashboard", "PASS", "Daily dashboard generated", "Latest daily dashboard artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "weekly_dashboard_latest.html"), "dashboard", "PASS", "Weekly dashboard generated", "Latest weekly dashboard artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "monthly_dashboard_latest.html"), "dashboard", "PASS", "Monthly dashboard generated", "Latest monthly dashboard artifact"),
        (_latest_matching(DEFAULT_REPORT_DIR, "release_readiness_latest.json"), "readiness", "PASS", "Release readiness generated", "Latest release readiness artifact"),
    ]

    for path, category, status, title, detail in mappings:
        if path is None:
            continue
        event = _file_event(path, category, status, title, detail)
        if event is not None:
            candidates.append(event)

    return candidates


def build_ops_timeline(limit: int = 20) -> dict[str, Any]:
    ops_cycle_text = _safe_read_text(DEFAULT_OPS_CYCLE_LOG_PATH)
    anomaly_log_path, anomaly_text = _latest_log_snapshot(DEFAULT_ANOMALY_LOG_PATH)
    smoke_log_path, smoke_text = _latest_log_snapshot(DEFAULT_SMOKE_LOG_PATH)

    events: list[dict[str, Any]] = []
    events.extend(_parse_ops_cycle_events(ops_cycle_text))
    events.extend(_parse_anomaly_events(anomaly_text, anomaly_log_path))
    events.extend(_artifact_events())

    if smoke_log_path is not None and smoke_text.strip():
        events.append(
            _file_event(
                smoke_log_path,
                "smoke_test",
                "INFO",
                "Smoke test log updated",
                "Latest smoke test log artifact",
            )
        )

    events = [event for event in events if event is not None and _parse_iso(str(event.get("timestamp") or "")) is not None]
    events.sort(key=lambda event: _parse_iso(str(event.get("timestamp"))) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    limited_events = events[: max(limit, 0)]

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "events": limited_events,
        "summary": {
            "event_count": len(limited_events),
            "source_log_exists": {
                "ops_cycle": DEFAULT_OPS_CYCLE_LOG_PATH.exists(),
                "anomaly_check": DEFAULT_ANOMALY_LOG_PATH.exists(),
                "smoke_test": DEFAULT_SMOKE_LOG_PATH.exists(),
            },
        },
        "status": {
            "fail_safe": True,
        },
    }