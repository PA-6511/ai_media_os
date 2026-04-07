from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.ops_settings_loader import load_ops_settings


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_THRESHOLD_PATH = BASE_DIR / "data" / "config" / "alert_thresholds.json"


def get_default_thresholds() -> dict[str, Any]:
    """異常検知のデフォルト閾値を返す。"""
    settings = load_ops_settings()
    anomaly = settings.get("anomaly", {}) if isinstance(settings, dict) else {}

    failed_warning = int(anomaly.get("failed_count_warning", 3))
    failed_critical = int(anomaly.get("failed_count_critical", 5))
    retry_warning = int(anomaly.get("retry_queued_warning", 5))
    retry_critical = int(anomaly.get("retry_queued_critical", 10))
    all_signal_zero_days = int(anomaly.get("all_signal_zero_warning_days", 2))
    smoke_warning = int(anomaly.get("smoke_failed_warning", 1))
    smoke_critical = int(anomaly.get("smoke_failed_critical", 2))

    return {
        "failed_count": {"warning": failed_warning, "critical": failed_critical},
        "retry_queued_count": {"warning": retry_warning, "critical": retry_critical},
        "all_signal_zero_streak": {"warning_days": all_signal_zero_days},
        "smoke_test_failed": {"warning": smoke_warning, "critical": smoke_critical},
    }


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """dict を再帰的にマージする。"""
    merged = dict(base)
    for key, value in override.items():
        base_value = merged.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(base_value, value)
        else:
            merged[key] = value
    return merged


def load_thresholds(threshold_path: Path | None = None) -> dict[str, Any]:
    """閾値設定をロードする。

    設定ファイルが存在しない場合はデフォルト値を返す。

    Args:
        threshold_path: 閾値設定ファイルのパス

    Returns:
        閾値 dict
    """
    defaults = get_default_thresholds()
    path = threshold_path or DEFAULT_THRESHOLD_PATH

    if not path.exists():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"閾値設定ファイルの JSON 形式が不正です: {path} ({exc})") from exc
    except OSError as exc:
        raise OSError(f"閾値設定ファイルの読み込みに失敗しました: {path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"閾値設定ファイルの形式が不正です: {path} (dict が必要)")

    return _deep_merge(defaults, payload)
