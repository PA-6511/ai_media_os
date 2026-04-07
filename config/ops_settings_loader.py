from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS_PATH = BASE_DIR / "config" / "ops_settings.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _default_ops_settings() -> dict[str, Any]:
    return {
        "ops": {
            "default_dry_run": True,
        },
        "scheduler": {
            "run_daily_report_after_job": True,
            "run_daily_report_on_success_only": False,
        },
        "anomaly": {
            "failed_count_warning": 3,
            "failed_count_critical": 5,
            "retry_queued_warning": 5,
            "retry_queued_critical": 10,
            "all_signal_zero_warning_days": 2,
            "smoke_failed_warning": 1,
            "smoke_failed_critical": 2,
            "notify_on_ok": False,
            "notify_on_warning": True,
            "notify_on_critical": True,
        },
        "dashboard": {
            "history_days": 7,
        },
        "archive": {
            "keep_generations": 7,
        },
        "log_rotation": {
            "enabled": True,
            "keep_generations": 7,
            "compress_rotated": False,
            "target_logs": [
                "data/logs/anomaly_check.log",
                "data/logs/combined_signal.log",
                "data/logs/ops_cycle.log",
                "data/logs/pipeline_failures.log",
                "data/logs/price_change.log",
                "data/logs/release_change.log",
                "data/logs/scheduler.log",
                "data/logs/smoke_test.log",
            ],
        },
        "ops_summary_notify": {
            "notify_on_pass": False,
            "notify_on_fail": True,
            "notify_on_warning": True,
        },
        "smoke_test": {
            "enabled_steps": [
                "main",
                "run_price_change_refresh",
                "run_release_refresh",
                "show_retry_queue",
                "show_status_report",
            ],
        },
        "ops_cycle": {
            "continue_on_error": True,
            "enabled_steps": [
                "scheduler",
                "smoke_test",
                "anomaly_check",
                "daily_report",
                "dashboard_build",
                "archive_backup",
                "log_rotate",
            ],
        },
    }


def load_ops_settings(settings_path: Path | None = None) -> dict[str, Any]:
    """ops_settings.json を読み込む。失敗時はデフォルトを返す。"""
    defaults = _default_ops_settings()
    path = settings_path or DEFAULT_SETTINGS_PATH

    if not path.exists() or not path.is_file():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    if not isinstance(payload, dict):
        return defaults

    return _deep_merge(defaults, payload)


def get_ops_setting(path: str, default: Any = None, settings: dict[str, Any] | None = None) -> Any:
    """ドット区切りパスで設定値を取得する。"""
    source = settings if settings is not None else load_ops_settings()
    cur: Any = source
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur
