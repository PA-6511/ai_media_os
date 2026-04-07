from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "ops_settings.json"
SCHEMA_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_path(path: Path) -> str:
    try:
        return str(path.relative_to(BASE_DIR)).replace("\\", "/")
    except ValueError:
        return str(path)


def _safe_read_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _pick(*values: Any, default: Any = None) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return default


def build_ops_config_summary() -> dict[str, Any]:
    settings = _safe_read_json(DEFAULT_CONFIG_PATH)

    ops = settings.get("ops") if isinstance(settings.get("ops"), dict) else {}
    ops_cycle = settings.get("ops_cycle") if isinstance(settings.get("ops_cycle"), dict) else {}
    anomaly = settings.get("anomaly") if isinstance(settings.get("anomaly"), dict) else {}
    dashboard = settings.get("dashboard") if isinstance(settings.get("dashboard"), dict) else {}
    scheduler = settings.get("scheduler") if isinstance(settings.get("scheduler"), dict) else {}
    archive = settings.get("archive") if isinstance(settings.get("archive"), dict) else {}
    log_rotation = settings.get("log_rotation") if isinstance(settings.get("log_rotation"), dict) else {}
    smoke_test = settings.get("smoke_test") if isinstance(settings.get("smoke_test"), dict) else {}

    ops_cycle_enabled_steps = ops_cycle.get("enabled_steps") if isinstance(ops_cycle.get("enabled_steps"), list) else []
    smoke_enabled_steps = smoke_test.get("enabled_steps") if isinstance(smoke_test.get("enabled_steps"), list) else []
    target_logs = log_rotation.get("target_logs") if isinstance(log_rotation.get("target_logs"), list) else []

    required_sections = ["ops", "ops_cycle", "anomaly", "dashboard"]
    missing_sections = [section for section in required_sections if not isinstance(settings.get(section), dict)]

    sources = {
        "ops_settings": {
            "path": _normalize_path(DEFAULT_CONFIG_PATH),
            "exists": DEFAULT_CONFIG_PATH.exists(),
            "loaded": bool(settings),
        }
    }

    return {
        "generated_at": _now_iso(),
        "schema_version": SCHEMA_VERSION,
        "ops": {
            "default_dry_run": bool(ops.get("default_dry_run", True)),
        },
        "ops_cycle": {
            "continue_on_error": bool(ops_cycle.get("continue_on_error", False)),
            "enable_gui_assets": bool(ops_cycle.get("enable_gui_assets", False)),
            "enabled_steps_count": len(ops_cycle_enabled_steps),
            "enabled_steps": [str(step) for step in ops_cycle_enabled_steps],
            "run_weekly_report": bool(ops_cycle.get("run_weekly_report", False)),
            "run_weekly_dashboard": bool(ops_cycle.get("run_weekly_dashboard", False)),
            "run_monthly_report": bool(ops_cycle.get("run_monthly_report", False)),
            "run_monthly_dashboard": bool(ops_cycle.get("run_monthly_dashboard", False)),
        },
        "dashboard": {
            "history_days": _coerce_int(dashboard.get("history_days"), 0),
        },
        "anomaly": {
            "failed_count_warning": _coerce_int(anomaly.get("failed_count_warning"), 0),
            "failed_count_critical": _coerce_int(anomaly.get("failed_count_critical"), 0),
            "retry_queued_warning": _coerce_int(anomaly.get("retry_queued_warning"), 0),
            "retry_queued_critical": _coerce_int(anomaly.get("retry_queued_critical"), 0),
            "all_signal_zero_warning_days": _coerce_int(anomaly.get("all_signal_zero_warning_days"), 0),
            "smoke_failed_warning": _coerce_int(anomaly.get("smoke_failed_warning"), 0),
            "smoke_failed_critical": _coerce_int(anomaly.get("smoke_failed_critical"), 0),
            "notify_on_ok": bool(anomaly.get("notify_on_ok", False)),
            "notify_on_warning": bool(anomaly.get("notify_on_warning", True)),
            "notify_on_critical": bool(anomaly.get("notify_on_critical", True)),
        },
        "scheduler": {
            "run_daily_report_after_job": bool(scheduler.get("run_daily_report_after_job", True)),
            "run_daily_report_on_success_only": bool(scheduler.get("run_daily_report_on_success_only", False)),
        },
        "archive": {
            "keep_generations": _coerce_int(archive.get("keep_generations"), 0),
        },
        "log_rotation": {
            "enabled": bool(log_rotation.get("enabled", False)),
            "keep_generations": _coerce_int(log_rotation.get("keep_generations"), 0),
            "compress_rotated": bool(log_rotation.get("compress_rotated", False)),
            "target_logs_count": len(target_logs),
        },
        "smoke_test": {
            "enabled_steps_count": len(smoke_enabled_steps),
            "enabled_steps": [str(step) for step in smoke_enabled_steps],
        },
        "summary": {
            "config_section_count": len([key for key in settings.keys() if isinstance(settings.get(key), dict)]),
            "missing_sections": missing_sections,
            "partial": not bool(settings) or len(missing_sections) > 0,
        },
        "status": {
            "ready": bool(settings),
            "fail_safe": True,
        },
        "sources": sources,
    }