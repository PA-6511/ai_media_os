from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def detect_release_change(
    previous_record: dict[str, Any] | None,
    current_record: dict[str, Any],
) -> dict[str, Any]:
    """前回と今回の新刊情報を比較してイベントを返す。"""
    prev_volume = _to_int((previous_record or {}).get("latest_volume_number"))
    curr_volume = _to_int(current_record.get("latest_volume_number"))

    prev_date = str((previous_record or {}).get("latest_release_date", "")).strip()
    curr_date = str(current_record.get("latest_release_date", "")).strip()

    prev_status = str((previous_record or {}).get("availability_status", "")).strip().lower()
    curr_status = str(current_record.get("availability_status", "")).strip().lower()

    reason = "no_change"
    release_changed = False

    if previous_record is None:
        reason = "first_observation"
    elif prev_volume is None and curr_volume is not None:
        release_changed = True
        reason = "volume_initialized"
    elif prev_volume is not None and curr_volume is not None and curr_volume > prev_volume:
        release_changed = True
        reason = "new_volume_detected"
    elif prev_date and curr_date and curr_date != prev_date:
        release_changed = True
        reason = "release_date_updated"
    elif prev_status != curr_status and curr_status:
        release_changed = True
        reason = "availability_changed"

    return {
        "work_id": str(current_record.get("work_id", "")).strip(),
        "title": str(current_record.get("title", "")).strip(),
        "release_changed": release_changed,
        "release_change_reason": reason,
        "previous_latest_volume_number": prev_volume,
        "current_latest_volume_number": curr_volume,
        "previous_latest_release_date": prev_date or None,
        "current_latest_release_date": curr_date or None,
        "previous_availability_status": prev_status or None,
        "current_availability_status": curr_status or None,
        "checked_at": str(current_record.get("checked_at", datetime.now(timezone.utc).isoformat())),
    }


def is_significant_release_change(change: dict[str, Any]) -> bool:
    """通知対象にすべき有意な新刊変化かを判定する。"""
    if not bool(change.get("release_changed", False)):
        return False

    reason = str(change.get("release_change_reason", "")).strip()
    if reason in {
        "new_volume_detected",
        "release_date_updated",
        "availability_changed",
        "volume_initialized",
    }:
        return True

    previous_volume = change.get("previous_latest_volume_number")
    current_volume = change.get("current_latest_volume_number")
    if previous_volume is not None and current_volume is not None:
        try:
            return int(current_volume) > int(previous_volume)
        except (TypeError, ValueError):
            return False

    return bool(change.get("release_changed", False))
