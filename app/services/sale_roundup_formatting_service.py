"""Display labels and representative ordering for eligible sale items."""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import re
from zoneinfo import ZoneInfo


JST = ZoneInfo("Asia/Tokyo")


def format_sale_datetime_jst(value):
    """Format a UTC sale timestamp for readers without changing stored values."""
    if value is None or value == "":
        return ""
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(JST).strftime("%m/%d %H:%M JST")
    except (ValueError, TypeError, OverflowError):
        return str(value)


def format_sale_period_jst(start, end):
    first = format_sale_datetime_jst(start)
    last = format_sale_datetime_jst(end)
    if first and last:
        return f"{first} ～ {last}"
    return f"{last}まで" if last else first


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() and number >= 0 else None


def integer(value):
    number = _number(value)
    return int(number) if number is not None else None


def format_yen(value):
    amount = integer(value)
    return f"{amount:,}円" if amount is not None else None


def price_labels(item):
    sale = integer(item.get("sale_price"))
    normal = integer(item.get("normal_price_evidence_only"))
    discount = integer(item.get("discount_percent"))
    percent = _number(item.get("point_percent"))
    point_count = integer(item.get("point_count"))
    if point_count is None and sale is not None and percent is not None:
        point_count = int(Decimal(sale) * percent / 100)
    points = None
    if point_count and percent and percent > 0:
        points = f"{int(percent)}%ポイント還元（{point_count}pt相当）"
    elif point_count:
        points = f"{point_count}pt還元"
    elif percent and percent > 0:
        points = f"{int(percent)}%ポイント還元"
    sale_text = format_yen(sale)
    normal_text = format_yen(normal)
    discount_amount = normal - sale if normal is not None and sale is not None else None
    return {
        "normal": f"定価 {normal_text}" if normal_text else None,
        "sale": sale_text,
        "price": (f"定価 {normal_text} → {sale_text}"
                  if normal_text and sale_text else sale_text),
        "discount": f"{discount}%OFF" if discount else None,
        "discount_amount": (f"{discount_amount:,}円引き"
                            if discount_amount is not None and discount_amount > 0 else None),
        "points": points,
        "effective": (f"実質{sale - point_count:,}円相当"
                      if sale is not None and point_count is not None and 0 < point_count <= sale else None),
    }


_TITLE_VOLUME_RE = re.compile(
    r"(?:\s+(?:第\s*)?(\d+)\s*巻|\s+(\d+)|[（(]\s*(?:第\s*)?(\d+)\s*(?:巻)?\s*[）)])$"
)
_LABEL_VOLUME_RE = re.compile(r"(?:第\s*)?(\d+)\s*(?:巻)?")
_SERIES_VOLUME_RE = re.compile(
    r"^\s*(?:第\s*)?(\d+)(?:\s*巻)?(?:$|\s+\S.*$)"
)
_SERIES_PAREN_VOLUME_RE = re.compile(
    r"^\s*[（(]\s*(?:第\s*)?(\d+)\s*(?:巻)?\s*[）)]\s*$"
)


def _title_volume_match(title):
    text = str(title or "").strip()
    match = _TITLE_VOLUME_RE.search(text)
    if match and re.search(r"\bEpisode\s*$", text[:match.start()], re.IGNORECASE):
        return None
    return match


def series_title(item):
    series = str(item.get("series_name") or "").strip()
    if series:
        return series
    title = str(item.get("title") or "").strip()
    match = _title_volume_match(title)
    return title[:match.start()].rstrip() if match else title


def volume_number(item):
    for field in ("volume_number", "volume_label"):
        value = item.get(field)
        if value is None or isinstance(value, bool):
            continue
        match = _LABEL_VOLUME_RE.fullmatch(str(value).strip())
        if match:
            return int(match.group(1))
    series = str(item.get("series_name") or "").strip()
    title = str(item.get("title") or "").strip()
    if series:
        if not title.startswith(series):
            return None
        suffix = title[len(series):]
        for pattern in (_SERIES_VOLUME_RE, _SERIES_PAREN_VOLUME_RE):
            match = pattern.fullmatch(suffix)
            if match:
                return int(match.group(1))
        return None
    match = _title_volume_match(item.get("title"))
    if match:
        return int(next(group for group in match.groups() if group is not None))
    return None


def volume_label(item):
    number = volume_number(item)
    if number is not None:
        return f"{number}巻"
    label = str(item.get("volume_label") or "").strip()
    return label or str(item.get("title") or "").strip()


def group_series_items(items):
    """Group for display with numeric volumes before deterministic unknowns."""
    groups = {}
    for item in items:
        title = series_title(item)
        key = title.casefold() or str(item.get("store_item_id") or "")
        group = groups.setdefault(key, {"title": title, "items": []})
        group["items"].append(item)
    result = []
    for group in groups.values():
        group["items"] = sorted(group["items"], key=natural_sale_item_order_key)
        result.append(group)
    return result


def natural_sale_item_order_key(item):
    """Use trustworthy volume data, then stable product identity."""
    number = volume_number(item)
    return (
        number is None,
        number if number is not None else 0,
        str(item.get("release_date") or ""),
        str(item.get("store_item_id") or ""),
        str(item.get("title") or ""),
        str(item.get("source_item_id") or ""),
    )


def volume_range_label(items):
    numbers = [volume_number(item) for item in items]
    numbers = [number for number in numbers if number is not None]
    if not numbers:
        return "セール対象"
    if len(numbers) == 1:
        return f"{numbers[0]}巻 セール対象"
    if numbers == list(range(numbers[0], numbers[-1] + 1)):
        return f"{numbers[0]}〜{numbers[-1]}巻 セール対象"
    return "・".join(str(number) for number in numbers) + "巻 セール対象"


def _series_key(item):
    return series_title(item).casefold() or str(item.get("store_item_id") or "")


def select_representatives(items, *, limit=5):
    """Show one strong offer per series before adding further volumes."""
    ranked = sorted(items, key=lambda item: (
        -(integer(item.get("discount_percent")) or 0),
        -(integer(item.get("point_percent")) or 0),
        str(item.get("store_item_id") or "")))
    first, rest, seen = [], [], set()
    for item in ranked:
        key = _series_key(item)
        if key in seen:
            rest.append(item)
        else:
            first.append(item)
            seen.add(key)
    return (first + rest)[:limit] if limit is not None else first + rest
