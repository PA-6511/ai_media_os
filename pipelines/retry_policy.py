from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from config.core_runtime_config import get_retry_max_retry_count


def classify_error(error_message: str) -> dict[str, str]:
    """エラーメッセージから再試行可否の種別を判定する。"""
    message = (error_message or "").strip().lower()

    if not message:
        return {"retryable": "false", "reason": "empty_error_message"}

    # 非再試行系: 認証・権限・バリデーションなど恒久エラー
    non_retryable_patterns = [
        r"\b401\b",
        r"\b403\b",
        r"unauthorized",
        r"forbidden",
        r"permission",
        r"validation",
        r"invalid",
        r"slug.*(exists|duplicate)",
        r"already\s+exists",
    ]
    if any(re.search(pattern, message) for pattern in non_retryable_patterns):
        return {"retryable": "false", "reason": "non_retryable_permanent_error"}

    # 再試行系: 一時的ネットワーク・サーバエラー
    retryable_patterns = [
        r"timeout",
        r"connection",
        r"temporar",
        r"\b429\b",
        r"\b500\b",
        r"\b502\b",
        r"\b503\b",
        r"\b504\b",
        r"server error",
        r"wordpress.*failed",
        r"api.*error",
    ]
    if any(re.search(pattern, message) for pattern in retryable_patterns):
        return {"retryable": "true", "reason": "temporary_server_error"}

    # 未知エラーは保守的に再試行可とする（運用回復優先）。
    return {"retryable": "true", "reason": "unknown_but_retryable"}


def _next_retry_minutes(next_retry_count: int) -> int:
    """簡易バックオフ（分）を返す。"""
    if next_retry_count <= 1:
        return 10
    if next_retry_count == 2:
        return 30
    return 60


def should_retry(error_message: str, retry_count: int, max_retry_count: int | None = None) -> dict[str, object]:
    """再試行可否と次回時刻を返す。"""
    if max_retry_count is None:
        resolved_max_retry_count = get_retry_max_retry_count()
    else:
        try:
            resolved_max_retry_count = int(max_retry_count)
        except (TypeError, ValueError):
            resolved_max_retry_count = get_retry_max_retry_count()
    classified = classify_error(error_message)
    retryable = classified["retryable"] == "true"

    if retry_count >= resolved_max_retry_count:
        return {
            "retryable": False,
            "reason": "max_retry_exceeded",
            "max_retry_count": resolved_max_retry_count,
            "next_retry_at": None,
        }

    if not retryable:
        return {
            "retryable": False,
            "reason": classified["reason"],
            "max_retry_count": resolved_max_retry_count,
            "next_retry_at": None,
        }

    minutes = _next_retry_minutes(retry_count)
    next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return {
        "retryable": True,
        "reason": classified["reason"],
        "max_retry_count": resolved_max_retry_count,
        "next_retry_at": next_retry_at.isoformat(),
    }
