"""
ai_ui_judge.py
Phase0.5 UI Flags - AI判断レイヤー
- 売上・評価・割引率・新着・終了時刻からスコアを算出
- urgent: 終了24時間以内
- blink: score>=70 かつ urgent、最大3件まで
"""
from datetime import datetime, timezone
from typing import Dict, Any

MAX_BLINK_ITEMS = 3


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def hours_until(end_time: str) -> float:
    end = parse_dt(end_time)
    if not end:
        return 999999
    now = datetime.now(end.tzinfo or timezone.utc)
    return (end - now).total_seconds() / 3600


def score_item(item: Dict[str, Any]) -> int:
    metrics = item.get("metrics", {})
    sale_end = item.get("sale_end", "")
    score = 0

    # 売上加点
    if metrics.get("sales_24h", 0) >= 30:
        score += 30
    elif metrics.get("sales_24h", 0) >= 10:
        score += 15

    if metrics.get("sales_72h", 0) >= 80:
        score += 20

    # 評価平均との差分
    rating = metrics.get("rating", 0)
    avg = metrics.get("rating_avg_series", 0)
    if avg and rating >= avg * 1.03:
        score += 15

    # 割引率
    discount = metrics.get("discount_rate", 0)
    if discount >= 50:
        score += 25
    elif discount >= 30:
        score += 15

    # 新着
    if metrics.get("is_new"):
        score += 10

    # エントリー必須は訴求価値あり
    if metrics.get("is_entry_required"):
        score += 8

    # 終了間近
    h = hours_until(sale_end)
    if 0 < h <= 6:
        score += 30
    elif 0 < h <= 24:
        score += 20

    # 人間の戦略優先度
    score += int(metrics.get("manual_priority", 0))

    return score


def is_manual_override_active(item: Dict[str, Any]) -> bool:
    override = item.get("ui_flags", {}).get("manual_override", {})
    if not override.get("enabled"):
        return False
    expires_at = override.get("expires_at")
    if not expires_at:
        return False
    expires = parse_dt(expires_at)
    if not expires:
        return False
    now = datetime.now(expires.tzinfo or timezone.utc)
    return now < expires


def judge_ai_flags(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    scored = []
    for item in items:
        score = score_item(item)
        h = hours_until(item.get("sale_end", ""))
        urgent = 0 < h <= 24
        blink_candidate = score >= 70 and urgent
        item["ai_flags"] = {
            "urgent": urgent,
            "blink": blink_candidate,
            "reason": f"score={score}, hours_until_end={round(h, 2)}"
        }
        scored.append((score, item))

    # blinkは最大3件まで（スコア降順の上位を採用）
    scored.sort(key=lambda x: x[0], reverse=True)
    blink_candidates = [
        item["id"]
        for score, item in scored
        if item.get("ai_flags", {}).get("blink")
    ]
    blink_allowed_ids = set(blink_candidates[:MAX_BLINK_ITEMS])

    for _, item in scored:
        if item["id"] not in blink_allowed_ids:
            item["ai_flags"]["blink"] = False

    return [item for _, item in scored]


def resolve_ui_flags(items: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    for item in items:
        if is_manual_override_active(item):
            item["ui_flags"]["urgent"] = True
            item["ui_flags"]["blink"] = True
            item["ui_flags"]["source"] = "manual_override"
            continue
        item["ui_flags"]["urgent"] = item.get("ai_flags", {}).get("urgent", False)
        item["ui_flags"]["blink"] = item.get("ai_flags", {}).get("blink", False)
        item["ui_flags"]["source"] = "ai"
    return items
