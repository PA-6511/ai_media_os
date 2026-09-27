from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


COUNT_FIELDS = (
    "impressions",
    "views",
    "engagements",
    "link_clicks",
    "profile_clicks",
    "likes",
    "reposts",
    "replies",
    "follows",
)

HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "post_id": (
        "post id",
        "tweet id",
        "ツイートid",
        "投稿id",
        "ポストid",
    ),
    "posted_at": (
        "posted at",
        "post time",
        "tweet date",
        "tweet time",
        "投稿日時",
        "ポスト日時",
        "ツイート日時",
    ),
    "text": (
        "text",
        "post text",
        "tweet text",
        "本文",
        "投稿本文",
        "ポスト本文",
        "ツイート本文",
    ),
    "post_type": (
        "post type",
        "tweet type",
        "投稿タイプ",
        "ポストタイプ",
    ),
    "impressions": (
        "impressions",
        "impression count",
        "インプレッション",
        "インプレッション数",
    ),
    "views": (
        "views",
        "view count",
        "post views",
        "表示回数",
        "閲覧数",
    ),
    "engagements": (
        "engagements",
        "total engagements",
        "engagement count",
        "エンゲージメント",
        "エンゲージメント数",
    ),
    "engagement_rate": (
        "engagement rate",
        "engagement rate %",
        "エンゲージメント率",
    ),
    "link_clicks": (
        "link clicks",
        "url clicks",
        "リンククリック",
        "リンククリック数",
        "urlクリック数",
    ),
    "profile_clicks": (
        "profile clicks",
        "profile visits",
        "プロフィールクリック",
        "プロフィールクリック数",
        "プロフィールへのアクセス",
    ),
    "likes": (
        "likes",
        "like count",
        "いいね",
        "いいね数",
    ),
    "reposts": (
        "reposts",
        "repost count",
        "retweets",
        "retweet count",
        "リポスト",
        "リポスト数",
        "リツイート",
        "リツイート数",
    ),
    "replies": (
        "replies",
        "reply count",
        "返信",
        "返信数",
    ),
    "follows": (
        "follows",
        "follow count",
        "new follows",
        "フォロー",
        "フォロー数",
        "新しいフォロー",
    ),
}


class XAnalyticsCsvError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedXAnalyticsRow:
    row_number: int
    post_id: str
    posted_at: datetime | None
    text: str | None
    post_type: str | None
    metrics: dict[str, int | Decimal | None]
    present_fields: frozenset[str]
    source_headers: dict[str, str]
    raw_payload: dict[str, str | None]
    unknown_payload: dict[str, str | None]
    engagement_rate_format: str | None


@dataclass(frozen=True)
class ParsedXAnalyticsCsv:
    headers: tuple[str, ...]
    rows: tuple[ParsedXAnalyticsRow, ...]


def normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value.lstrip("\ufeff"))
    normalized = normalized.strip().casefold()
    return re.sub(r"[\s_-]+", " ", normalized)


def _alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in HEADER_ALIASES.items():
        for alias in (canonical, *aliases):
            normalized = normalize_header(alias)
            existing = lookup.get(normalized)
            if existing is not None and existing != canonical:
                raise RuntimeError(f"ambiguous X Analytics alias: {alias}")
            lookup[normalized] = canonical
    return lookup


ALIAS_LOOKUP = _alias_lookup()


def _parse_count(value: str | None, field_name: str) -> int | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    compact = normalized.replace(",", "")
    if compact.casefold() in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        raise XAnalyticsCsvError(f"{field_name} must be a finite integer")
    if not re.fullmatch(r"[+-]?\d+", compact):
        raise XAnalyticsCsvError(f"{field_name} must be an integer")
    parsed = int(compact)
    if parsed < 0:
        raise XAnalyticsCsvError(f"{field_name} must be non-negative")
    return parsed


def _parse_engagement_rate(
    value: str | None,
) -> tuple[Decimal | None, str | None]:
    normalized = str(value or "").strip()
    if not normalized:
        return None, None
    is_percent = normalized.endswith("%")
    compact = normalized[:-1].strip() if is_percent else normalized
    compact = compact.replace(",", "")
    try:
        parsed = Decimal(compact)
    except InvalidOperation as exc:
        raise XAnalyticsCsvError(
            "engagement_rate must be a finite non-negative number"
        ) from exc
    if not parsed.is_finite() or parsed < 0:
        raise XAnalyticsCsvError(
            "engagement_rate must be a finite non-negative number"
        )
    return parsed, "PERCENT" if is_percent else "SOURCE_NUMBER"


def _parse_datetime(
    value: str | None,
    *,
    field_name: str,
    default_timezone: str | None,
) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    candidates = [normalized.replace("Z", "+00:00")]
    if normalized.endswith(" UTC"):
        candidates.insert(0, normalized[:-4] + "+00:00")
    parsed: datetime | None = None
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            break
        except ValueError:
            continue
    if parsed is None:
        for format_string in (
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ):
            try:
                parsed = datetime.strptime(normalized, format_string)
                break
            except ValueError:
                continue
    if parsed is None:
        raise XAnalyticsCsvError(f"{field_name} has an unsupported datetime")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not default_timezone:
            raise XAnalyticsCsvError(
                f"{field_name} has no timezone; --csv-timezone is required"
            )
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(default_timezone))
        except ZoneInfoNotFoundError as exc:
            raise XAnalyticsCsvError(
                f"unknown CSV timezone: {default_timezone}"
            ) from exc
    return parsed


def _header_plan(headers: list[str]) -> tuple[dict[str, str], set[str]]:
    canonical_to_source: dict[str, str] = {}
    unknown_headers: set[str] = set()
    for source_header in headers:
        canonical = ALIAS_LOOKUP.get(normalize_header(source_header))
        if canonical is None:
            unknown_headers.add(source_header)
            continue
        if canonical in canonical_to_source:
            raise XAnalyticsCsvError(
                f"multiple headers map to {canonical}: "
                f"{canonical_to_source[canonical]!r}, {source_header!r}"
            )
        canonical_to_source[canonical] = source_header
    if "post_id" not in canonical_to_source:
        raise XAnalyticsCsvError("post_id header is required")
    return canonical_to_source, unknown_headers


def parse_x_analytics_csv(
    source: Path | TextIO,
    *,
    csv_timezone: str | None = None,
) -> ParsedXAnalyticsCsv:
    should_close = isinstance(source, Path)
    handle = (
        source.open("r", encoding="utf-8-sig", newline="")
        if isinstance(source, Path)
        else source
    )
    try:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise XAnalyticsCsvError("CSV header is missing")
        headers = [str(header) for header in reader.fieldnames]
        canonical_to_source, unknown_headers = _header_plan(headers)
        parsed_rows: list[ParsedXAnalyticsRow] = []
        errors: list[str] = []

        for row_number, row in enumerate(reader, start=2):
            try:
                if None in row:
                    raise XAnalyticsCsvError(
                        "row has more values than the header"
                    )
                post_id = str(
                    row.get(canonical_to_source["post_id"]) or ""
                ).strip()
                if not post_id:
                    raise XAnalyticsCsvError("post_id is required")
                if not post_id.isdecimal():
                    raise XAnalyticsCsvError(
                        "post_id must contain decimal digits only; "
                        "scientific or floating-point IDs are not recoverable"
                    )

                present_fields = frozenset(canonical_to_source)
                metrics: dict[str, int | Decimal | None] = {
                    field: (
                        _parse_count(
                            row.get(canonical_to_source[field]), field
                        )
                        if field in canonical_to_source
                        else None
                    )
                    for field in COUNT_FIELDS
                }
                rate, rate_format = _parse_engagement_rate(
                    row.get(canonical_to_source["engagement_rate"])
                    if "engagement_rate" in canonical_to_source
                    else None
                )
                metrics["engagement_rate"] = rate
                posted_at = _parse_datetime(
                    row.get(canonical_to_source["posted_at"])
                    if "posted_at" in canonical_to_source
                    else None,
                    field_name="posted_at",
                    default_timezone=csv_timezone,
                )
                parsed_rows.append(
                    ParsedXAnalyticsRow(
                        row_number=row_number,
                        post_id=post_id,
                        posted_at=posted_at,
                        text=(
                            str(row.get(canonical_to_source["text"]) or "")
                            or None
                            if "text" in canonical_to_source
                            else None
                        ),
                        post_type=(
                            str(
                                row.get(canonical_to_source["post_type"])
                                or ""
                            ).strip()
                            or None
                            if "post_type" in canonical_to_source
                            else None
                        ),
                        metrics=metrics,
                        present_fields=present_fields,
                        source_headers={
                            canonical: source_header
                            for canonical, source_header
                            in canonical_to_source.items()
                        },
                        raw_payload={
                            header: row.get(header) for header in headers
                        },
                        unknown_payload={
                            header: row.get(header)
                            for header in unknown_headers
                        },
                        engagement_rate_format=rate_format,
                    )
                )
            except XAnalyticsCsvError as exc:
                errors.append(f"row {row_number}: {exc}")

        if errors:
            raise XAnalyticsCsvError("; ".join(errors))
        return ParsedXAnalyticsCsv(tuple(headers), tuple(parsed_rows))
    finally:
        if should_close:
            handle.close()