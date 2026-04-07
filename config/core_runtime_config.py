from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CORE_RUNTIME_CONFIG_PATH = BASE_DIR / "config" / "core_runtime.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _default_core_runtime_config() -> dict[str, Any]:
    return {
        "retry": {
            "max_retry_count": 3,
            "max_retry_count_clamp_min": 1,
            "max_retry_count_clamp_max": 10,
        },
        "core": {
            "default_action": "generate_article",
            "invalid_decision_fallback": "freeze",
            "invalid_transition_fallback": "review",
            "freeze_on_invalid_selected": True,
            "priority_clamp_min": 0.0,
            "priority_clamp_max": 1.0,
            "confidence_clamp_min": 0.0,
            "confidence_clamp_max": 1.0,
        },
        "logging": {
            "level": "INFO",
        },
    }


def load_core_runtime_config(config_path: Path | None = None) -> dict[str, Any]:
    defaults = _default_core_runtime_config()
    path = config_path or DEFAULT_CORE_RUNTIME_CONFIG_PATH
    if not path.exists() or not path.is_file():
        return defaults

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults

    if not isinstance(payload, dict):
        return defaults

    return _deep_merge(defaults, payload)


def get_core_runtime_setting(path: str, default: Any = None, config: dict[str, Any] | None = None) -> Any:
    source = config if config is not None else load_core_runtime_config()
    cur: Any = source
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def get_core_runtime_int(path: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = get_core_runtime_setting(path, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_core_runtime_float(path: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = get_core_runtime_setting(path, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = default

    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def get_core_runtime_bool(path: str, default: bool) -> bool:
    raw = get_core_runtime_setting(path, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
    return bool(default)


def get_core_runtime_str(path: str, default: str) -> str:
    raw = get_core_runtime_setting(path, default)
    text = str(raw or "").strip()
    return text or default


def get_retry_max_retry_count(default: int = 3) -> int:
    """retry.max_retry_count を安全に取得する。"""
    raw_clamp_max = get_core_runtime_setting("retry.max_retry_count_clamp_max", 10)
    try:
        clamp_max = int(raw_clamp_max)
    except (TypeError, ValueError):
        clamp_max = 10
    if clamp_max < 1:
        clamp_max = 10
    clamp_max = min(clamp_max, 100)

    raw_clamp_min = get_core_runtime_setting("retry.max_retry_count_clamp_min", 1)
    try:
        clamp_min = int(raw_clamp_min)
    except (TypeError, ValueError):
        clamp_min = 1
    if clamp_min < 1 or clamp_min > clamp_max:
        clamp_min = 1

    return get_core_runtime_int("retry.max_retry_count", default, minimum=clamp_min, maximum=clamp_max)
