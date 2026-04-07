from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# しきい値は最小版の固定値。将来は環境変数化しやすい構成にしている。
MIN_PRICE_DROP_YEN = 50.0
MIN_PRICE_DROP_RATE = 10.0
MIN_DISCOUNT_RATE_POINT_UP = 5.0
MIN_DISCOUNT_RATE = 10.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def detect_price_change(
    previous_record: dict[str, Any] | None,
    current_record: dict[str, Any],
) -> dict[str, Any]:
    """前回値と今回値を比較し、価格変動イベントを返す。"""
    previous_price = _to_float((previous_record or {}).get("current_price"), default=0.0)
    current_price = _to_float(current_record.get("current_price"), default=0.0)

    previous_discount_rate = _to_float((previous_record or {}).get("discount_rate"), default=0.0)
    current_discount_rate = _to_float(current_record.get("discount_rate"), default=0.0)

    price_diff = current_price - previous_price
    price_drop_amount = previous_price - current_price
    price_drop_rate = (price_drop_amount / previous_price * 100.0) if previous_price > 0 else 0.0
    discount_rate_diff = current_discount_rate - previous_discount_rate

    # 初回観測は比較対象がないため no_change 扱いにする。
    if previous_record is None:
        return {
            "work_id": str(current_record.get("work_id", "")).strip(),
            "keyword": str(current_record.get("keyword", "")).strip(),
            "article_type": str(current_record.get("article_type", "")).strip(),
            "previous_price": None,
            "current_price": current_price,
            "discount_rate": current_discount_rate,
            "checked_at": str(current_record.get("checked_at", datetime.now(timezone.utc).isoformat())),
            "price_diff": None,
            "price_drop_rate": 0.0,
            "discount_rate_diff": None,
            "price_changed": False,
            "change_reason": "first_observation",
        }

    reasons: list[str] = []
    if current_price < previous_price:
        reasons.append("price_down")
    if discount_rate_diff >= MIN_DISCOUNT_RATE_POINT_UP:
        reasons.append("discount_rate_up")
    if price_drop_amount >= MIN_PRICE_DROP_YEN:
        reasons.append("price_drop_amount_threshold")
    if price_drop_rate >= MIN_PRICE_DROP_RATE:
        reasons.append("price_drop_rate_threshold")
    if current_discount_rate >= MIN_DISCOUNT_RATE:
        reasons.append("discount_rate_threshold")

    price_changed = len(reasons) > 0
    change_reason = "|".join(reasons) if reasons else "no_change"

    return {
        "work_id": str(current_record.get("work_id", "")).strip(),
        "keyword": str(current_record.get("keyword", "")).strip(),
        "article_type": str(current_record.get("article_type", "")).strip(),
        "previous_price": previous_price,
        "current_price": current_price,
        "discount_rate": current_discount_rate,
        "checked_at": str(current_record.get("checked_at", datetime.now(timezone.utc).isoformat())),
        "price_diff": price_diff,
        "price_drop_rate": round(price_drop_rate, 2),
        "discount_rate_diff": round(discount_rate_diff, 2),
        "price_changed": price_changed,
        "change_reason": change_reason,
    }


def is_significant_change(change: dict[str, Any]) -> bool:
    """価格変動イベントが再生成トリガーとして有意か判定する。"""
    if not bool(change.get("price_changed", False)):
        return False

    reason = str(change.get("change_reason", ""))
    if reason == "first_observation":
        return False
    return True
