"""
manual_override.py
Phase0.5 UI Flags - manual_override管理
- apply_manual_override(item_id, hours, reason)
- clear_manual_override(item_id, reason)
- hours は 6 / 24 / 48 のみ許可
- reason 必須
- 同時 manual_override は最大3件
- logs/manual_override.log へ JSON Lines で記録
"""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

DATA_PATH = Path(__file__).parent.parent / "data" / "campaign_items.json"
LOG_PATH = Path(__file__).parent.parent / "logs" / "manual_override.log"
MAX_ACTIVE_OVERRIDES = 3
ALLOWED_HOURS = {6, 24, 48}


def load_items() -> list[Dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_items(items: list[Dict[str, Any]]) -> None:
    with DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def now_jst() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def is_active_override(item: Dict[str, Any]) -> bool:
    override = item.get("ui_flags", {}).get("manual_override", {})
    if not override.get("enabled"):
        return False
    expires_at = override.get("expires_at")
    if not expires_at:
        return False
    try:
        expires = datetime.fromisoformat(expires_at)
    except Exception:
        return False
    return now_jst() < expires


def count_active_overrides(items: list[Dict[str, Any]]) -> int:
    return sum(1 for item in items if is_active_override(item))


def find_item(items: list[Dict[str, Any]], item_id: str) -> Dict[str, Any] | None:
    for item in items:
        if item.get("id") == item_id:
            return item
    return None


def write_log(action: str, item_id: str, reason: str = "") -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": now_jst().isoformat(),
        "action": action,
        "item_id": item_id,
        "reason": reason
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def apply_manual_override(item_id: str, hours: int, reason: str) -> None:
    if hours not in ALLOWED_HOURS:
        raise ValueError(f"hours は {sorted(ALLOWED_HOURS)} のみ許可")
    if not reason.strip():
        raise ValueError("reason は必須")

    items = load_items()
    item = find_item(items, item_id)
    if not item:
        raise ValueError(f"item_id が見つかりません: {item_id}")

    already_active = is_active_override(item)
    active_count = count_active_overrides(items)
    if not already_active and active_count >= MAX_ACTIVE_OVERRIDES:
        raise RuntimeError(f"manual_override は同時に最大{MAX_ACTIVE_OVERRIDES}件までです")

    expires_at = (now_jst() + timedelta(hours=hours)).isoformat()
    item.setdefault("ui_flags", {})
    item["ui_flags"]["manual_override"] = {
        "enabled": True,
        "expires_at": expires_at,
        "reason": reason.strip()
    }
    item["ui_flags"]["urgent"] = True
    item["ui_flags"]["blink"] = True
    item["ui_flags"]["source"] = "manual_override"

    save_items(items)
    write_log("apply_manual_override", item_id, reason)


def clear_manual_override(item_id: str, reason: str = "manual clear") -> None:
    items = load_items()
    item = find_item(items, item_id)
    if not item:
        raise ValueError(f"item_id が見つかりません: {item_id}")

    item.setdefault("ui_flags", {})
    item["ui_flags"].setdefault("manual_override", {})
    item["ui_flags"]["manual_override"]["enabled"] = False
    item["ui_flags"]["source"] = "ai"

    save_items(items)
    write_log("clear_manual_override", item_id, reason)
