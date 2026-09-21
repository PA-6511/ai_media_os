from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sqlite3
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping

from sqlalchemy import func, select, text

from app.db.models import EbookItem, StoreOffer
from app.db.session import SessionLocal
from app.services.monthly_fast_intake_shadow_adapter import (
    collect_monthly_fast_intake_shadow_handoffs,
)
from app.services.csv_import_service import CsvImportService
from app.services.rakuten_comic_calendar_parser import split_title_volume_imprint


SOURCE_NAME = "new_release_multistore"
SOURCE_DISCOVERY = "RAKUTEN_BOOKS_COMIC_CALENDAR"
SOURCE_LABEL = "rakuten_books_comic_calendar"
FAST_KOBO_PROMOTION_REASON = "CROSS_SOURCE_EXACT_KOBO_URL_PROMOTION"
AMAZON_CREATORS_MIN_REQUEST_INTERVAL_SECONDS = 1.0
DEFAULT_SOURCE_URL = (
    "https://books.rakuten.co.jp/calendar/001001/monthly/"
    "?s=14&tid={month}-01&v=2"
)
DEFAULT_EBOOK_DAILY_SOURCE_URL = (
    "https://books.rakuten.co.jp/calendar/101904/daily/"
    "?tid={day}&v=3"
)
USER_AGENT = "AI-Media-OS-MonthlyComicReleaseSync/1.0 (+https://example.invalid)"
MONTH_PATTERN = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$")
ISBN_PATTERN = re.compile(r"(?<!\d)(97[89][\d-]{10,16}\d)(?!\d)")
PRODUCT_ID_PATTERN = re.compile(r"/(rb)/([0-9]+)/?|/(rk)/([0-9a-f]{32})/?", re.IGNORECASE)
DATE_PATTERN = re.compile(r"(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
META_TAG_PATTERN = re.compile(r"<meta\b(?P<attrs>[^>]*)>", re.IGNORECASE)
HTML_ATTRIBUTE_PATTERN = re.compile(
    r"(?P<name>[-:\w]+)\s*=\s*(?:[\"'](?P<quoted>.*?)[\"']|(?P<bare>[^\s>]+))",
    re.DOTALL,
)
PRODUCT_INFO_PATTERN = re.compile(
    r"<li\b[^>]*class=[\"'][^\"']*\bproductInfo\b[^\"']*[\"'][^>]*>(?P<content>.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)
CATEGORY_PATTERN = re.compile(
    r"<span\b[^>]*class=[\"'][^\"']*\bcategory\b[^\"']*[\"'][^>]*>(?P<value>.*?)</span>",
    re.IGNORECASE | re.DOTALL,
)
CATEGORY_VALUE_PATTERN = re.compile(
    r"<span\b[^>]*class=[\"'][^\"']*\bcategoryValue\b[^\"']*[\"'][^>]*>(?P<value>.*?)</span>",
    re.IGNORECASE | re.DOTALL,
)
ANCHOR_PATTERN = re.compile(r"<a\b[^>]*>(?P<value>.*?)</a>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
CALENDAR_ITEM_PATTERN = re.compile(
    r"<li\b[^>]*class=[\"'][^\"']*\bitem\b[^\"']*[\"'][^>]*>(?P<content>.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)
EBOOK_PRODUCT_URL_PATTERN = re.compile(
    r"https://books\.rakuten\.co\.jp/rk/[0-9a-f]{32}/?",
    re.IGNORECASE,
)
EBOOK_SINGLE_CHAPTER_PATTERN = re.compile(
    r"(?:分冊版|【?単話(?:版|売)?】?|話売り|連載版|＜連載版＞|"
    r"第\s*\d+\s*話|\d+話(?:【|$)|【マイクロ】)",
    re.IGNORECASE,
)
EBOOK_MAGAZINE_PATTERN = re.compile(
    r"(?:^(?:comic\s+)?[^\n]*\bvol\.?\s*\d+|"
    r"(?:週刊|月刊|ヤングジャンプ|モーニング|コミックライド).*(?:号|no\.|vol\.))",
    re.IGNORECASE,
)
EBOOK_NON_COMIC_PATTERN = re.compile(
    r"^(?:ニュージャパニズム\s+ブランディング|"
    r"マジカルテクニック\s+コピックで)",
    re.IGNORECASE,
)


class MonthlyComicReleaseSyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class ComicReleaseRecord:
    source_item_id: str
    title: str
    release_date: date
    source_url: str
    author_name: str | None = None
    publisher_name: str | None = None
    imprint_name: str | None = None
    series_name: str | None = None
    volume_label: str | None = None
    isbn: str | None = None
    item_type: str = "tankobon"
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def catalog_source_item_id(self) -> str:
        return f"rakuten_books:{self.source_item_id}"

    @property
    def normalized_title(self) -> str:
        return normalize_identity(self.title)

    def csv_row(self) -> dict[str, str]:
        return {
            "source_name": SOURCE_NAME,
            "source_item_id": self.catalog_source_item_id,
            "source_url": self.source_url,
            "title": self.title,
            "isbn": self.isbn or "",
            "normalized_title": self.title,
            "volume_label": self.volume_label or "",
            "author_name": self.author_name or "",
            "author": self.author_name or "",
            "publisher_name": self.publisher_name or "",
            "publisher": self.publisher_name or "",
            "series_name": self.series_name or "",
            "release_date": self.release_date.isoformat(),
            "item_type": self.item_type,
            "wordpress_status": "not_created",
        }

    def audit_payload(self) -> dict[str, Any]:
        return {
            "source_name": SOURCE_LABEL,
            "source_item_id": self.source_item_id,
            "source_url": self.source_url,
            "title": self.title,
            "normalized_title": self.normalized_title,
            "author_name": self.author_name,
            "publisher_name": self.publisher_name,
            "imprint_name": self.imprint_name,
            "series_name": self.series_name,
            "volume_label": self.volume_label,
            "isbn": self.isbn,
            "release_date": self.release_date.isoformat(),
            "raw": dict(self.raw),
        }


@dataclass(frozen=True)
class PlannedChange:
    record: ComicReleaseRecord
    action: str
    existing_ebook_item_id: str | None
    changed_fields: tuple[str, ...] = ()
    reason: str | None = None


@dataclass
class SyncPlan:
    target_month: str
    source_url: str
    records: list[ComicReleaseRecord]
    changes: list[PlannedChange]

    def counts(self) -> dict[str, int]:
        counts = {key: 0 for key in ("NEW", "UPDATED", "UNCHANGED", "REVIEW_REQUIRED")}
        for change in self.changes:
            counts[change.action] = counts.get(change.action, 0) + 1
        return counts

    @property
    def actionable(self) -> list[PlannedChange]:
        return [change for change in self.changes if change.action in {"NEW", "UPDATED"}]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or "")).strip())


def normalize_identity(value: Any) -> str:
    normalized = normalize_space(value).casefold()
    return re.sub(r"[^\w]+", "", normalized, flags=re.UNICODE)


def normalize_work_identity(value: Any) -> str:
    """Normalize store-only title decorations while retaining volume identity."""

    normalized = unicodedata.normalize("NFKC", normalize_space(value)).casefold()
    normalized = re.sub(
        r"【(?:電子(?:書籍|コミック)?限定[^】]*|電子特別版|電子単行本)】",
        "",
        normalized,
    )
    normalized = re.sub(
        r"\s*[（(][^()（）]*(?:コミックス|comics|\bkc\b|コミック\s*elmo|comic\s*elmo)[^()（）]*[）)]\s*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[^\w]+", "", normalized, flags=re.UNICODE)


def normalize_isbn(value: Any) -> str | None:
    candidate = re.sub(r"[^0-9Xx]", "", str(value or ""))
    if len(candidate) in {10, 13}:
        return candidate.upper()
    return None


def parse_month(value: str) -> tuple[str, date, date]:
    matched = MONTH_PATTERN.fullmatch(str(value or "").strip())
    if not matched:
        raise MonthlyComicReleaseSyncError("month must be YYYY-MM")
    year, month = int(matched.group(1)), int(matched.group(2))
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    return start.strftime("%Y-%m"), start, end


def parse_release_date(value: Any, *, expected_month: str | None = None) -> date | None:
    raw = normalize_space(value)
    if not raw:
        return None
    matched = DATE_PATTERN.search(raw)
    if matched:
        try:
            return date(int(matched.group(1)), int(matched.group(2)), int(matched.group(3)))
        except ValueError:
            return None
    for pattern in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            pass
    month_day = re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", raw)
    if month_day and expected_month:
        year = int(expected_month[:4])
        try:
            return date(year, int(month_day.group(1)), int(month_day.group(2)))
        except ValueError:
            return None
    return None


def source_item_id_from_url(url: str) -> str:
    matched = PRODUCT_ID_PATTERN.search(url)
    if matched:
        kind = (matched.group(1) or matched.group(3)).lower()
        value = matched.group(2) or matched.group(4)
        return f"{kind}-{value.lower()}"
    return "url-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def _absolute_rakuten_url(value: str, *, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(str(value or "").strip()))


def _canonical_calendar_url(value: str) -> str:
    parts = urllib.parse.urlsplit(value)
    query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parts.query)))
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, query, "")
    )


def _extract_imprint_and_series(title: str) -> tuple[str, str | None, str | None]:
    series, volume, imprint, _ = split_title_volume_imprint(title)
    series = normalize_space(series) or title
    return series, volume, normalize_space(imprint) or None


def _object_candidates(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _object_candidates(child)
    elif isinstance(value, list):
        for child in value:
            yield from _object_candidates(child)


def _json_ld_records(
    html_text: str,
    *,
    expected_month: str,
    page_url: str,
) -> list[ComicReleaseRecord]:
    records: list[ComicReleaseRecord] = []
    for raw_json in re.findall(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        try:
            payload = json.loads(html.unescape(raw_json).strip())
        except json.JSONDecodeError:
            continue
        for candidate in _object_candidates(payload):
            title = normalize_space(candidate.get("name") or candidate.get("title"))
            url = _absolute_rakuten_url(
                str(candidate.get("url") or candidate.get("@id") or ""),
                base_url=page_url,
            )
            release_date = parse_release_date(
                candidate.get("releaseDate") or candidate.get("datePublished"),
                expected_month=expected_month,
            )
            if not title or not url or release_date is None:
                continue
            if not url.startswith("https://books.rakuten.co.jp/"):
                continue
            series, volume, imprint = _extract_imprint_and_series(title)
            author = candidate.get("author")
            if isinstance(author, list):
                author = "|".join(normalize_space(x.get("name") if isinstance(x, Mapping) else x) for x in author)
            elif isinstance(author, Mapping):
                author = author.get("name")
            publisher = candidate.get("publisher")
            if isinstance(publisher, Mapping):
                publisher = publisher.get("name")
            records.append(
                ComicReleaseRecord(
                    source_item_id=source_item_id_from_url(url),
                    title=title,
                    release_date=release_date,
                    source_url=url,
                    author_name=normalize_space(author) or None,
                    publisher_name=normalize_space(publisher) or None,
                    imprint_name=imprint,
                    series_name=series,
                    volume_label=volume,
                    isbn=normalize_isbn(candidate.get("isbn")),
                    raw={"parser": "json_ld", "page_url": page_url},
                )
            )
    return records


def _anchor_records(
    html_text: str,
    *,
    expected_month: str,
    page_url: str,
) -> list[ComicReleaseRecord]:
    records: list[ComicReleaseRecord] = []
    anchor_pattern = re.compile(
        r"<a\b(?P<attrs>[^>]*)href=[\"'](?P<href>[^\"']+/rb/[^\"']+)[\"'][^>]*>(?P<title>.*?)</a>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for card_match in CALENDAR_ITEM_PATTERN.finditer(html_text):
        card_html = card_match.group("content")
        release_date = parse_release_date(
            _calendar_class_text(card_html, "item-release"),
            expected_month=expected_month,
        )
        if release_date is None:
            continue
        context = re.sub(r"<[^>]+>", "\n", card_html)
        for match in anchor_pattern.finditer(card_html):
            title = normalize_space(re.sub(r"<[^>]+>", " ", match.group("title")))
            if not title:
                continue
            source_url = _absolute_rakuten_url(match.group("href"), base_url=page_url)
            lines = [normalize_space(line) for line in context.splitlines()]
            lines = [line for line in lines if line and line != title]
            author = None
            publisher = None
            for line in lines:
                if not author and re.search(r"(?:著者|作者)\s*[:：]", line):
                    author = re.split(r"[:：]", line, maxsplit=1)[-1]
                if not publisher and re.search(r"出版社\s*[:：]", line):
                    publisher = re.split(r"[:：]", line, maxsplit=1)[-1]
            series, volume, imprint = _extract_imprint_and_series(title)
            isbn_match = ISBN_PATTERN.search(context)
            records.append(
                ComicReleaseRecord(
                    source_item_id=source_item_id_from_url(source_url),
                    title=title,
                    release_date=release_date,
                    source_url=source_url,
                    author_name=normalize_space(author) or None,
                    publisher_name=normalize_space(publisher) or None,
                    imprint_name=imprint,
                    series_name=series,
                    volume_label=volume,
                    isbn=normalize_isbn(isbn_match.group(1)) if isbn_match else None,
                    raw={"parser": "anchor", "page_url": page_url},
                )
            )
    return records


def _calendar_class_text(content: str, class_name: str) -> str:
    matched = re.search(
        rf"<[^>]+class=[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>"
        r"(?P<value>.*?)</[^>]+>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _html_to_text(matched.group("value")) if matched else ""


def _ebook_item_type(*, title: str, price_yen: int | None) -> str:
    """Classify the Kobo comic calendar without importing serial episodes."""

    if EBOOK_MAGAZINE_PATTERN.search(title):
        return "magazine_episode"
    if EBOOK_SINGLE_CHAPTER_PATTERN.search(title):
        return "single_chapter"
    # Some publishers expose a numbered episode as if it were a volume.  A
    # current-release comic volume is not sold at this single-episode price.
    if price_yen is not None and price_yen <= 300:
        return "single_chapter"
    if EBOOK_NON_COMIC_PATTERN.search(title):
        return "general_book"
    return "tankobon"


def _ebook_calendar_records(
    html_text: str,
    *,
    expected_month: str,
    page_url: str,
) -> list[ComicReleaseRecord]:
    records: list[ComicReleaseRecord] = []
    for matched in CALENDAR_ITEM_PATTERN.finditer(html_text):
        content = matched.group("content")
        product_match = EBOOK_PRODUCT_URL_PATTERN.search(html.unescape(content))
        title = _calendar_class_text(content, "item-title__text")
        release_date = parse_release_date(
            _calendar_class_text(content, "item-release__date"),
            expected_month=expected_month,
        )
        if not product_match or not title or release_date is None:
            continue
        source_url = _absolute_rakuten_url(product_match.group(0), base_url=page_url)
        author = _calendar_class_text(content, "item-author__name")
        publisher = _calendar_class_text(content, "item-publisher")
        price_text = _calendar_class_text(content, "item-pricing__price")
        price_digits = re.sub(r"\D", "", price_text)
        price_yen = int(price_digits) if price_digits else None
        image_match = re.search(
            r"<img\b[^>]*src=[\"'](?P<url>[^\"']+)[\"']",
            content,
            flags=re.IGNORECASE,
        )
        image_url = (
            _absolute_rakuten_url(image_match.group("url"), base_url=page_url)
            if image_match
            else ""
        )
        item_number_match = re.search(r"(?<!\d)(\d{13})(?!\d)", image_url)
        source_item_id = (
            f"rk-{item_number_match.group(1)}"
            if item_number_match
            else source_item_id_from_url(source_url)
        )
        series, volume, imprint = _extract_imprint_and_series(title)
        item_type = _ebook_item_type(title=title, price_yen=price_yen)
        records.append(
            ComicReleaseRecord(
                source_item_id=source_item_id,
                title=title,
                release_date=release_date,
                source_url=source_url,
                author_name=(
                    "|".join(normalize_space(value) for value in author.split(",") if normalize_space(value))
                    or None
                ),
                publisher_name=publisher or None,
                imprint_name=imprint,
                series_name=series,
                volume_label=volume,
                item_type=item_type,
                raw={
                    "parser": "ebook_calendar",
                    "page_url": page_url,
                    "price_yen": price_yen,
                    "store_item_id": item_number_match.group(1) if item_number_match else None,
                    "cover_candidate_url": image_url or None,
                    "cover_candidate_source": "RAKUTEN_KOBO_CALENDAR",
                },
            )
        )
    return records


def parse_calendar_html(
    html_text: str,
    *,
    expected_month: str,
    page_url: str,
) -> list[ComicReleaseRecord]:
    records = _ebook_calendar_records(
        html_text,
        expected_month=expected_month,
        page_url=page_url,
    )
    records.extend(_json_ld_records(html_text, expected_month=expected_month, page_url=page_url))
    records.extend(_anchor_records(html_text, expected_month=expected_month, page_url=page_url))
    unique: dict[str, ComicReleaseRecord] = {}
    for record in records:
        if record.release_date.strftime("%Y-%m") != expected_month:
            continue
        previous = unique.get(record.source_item_id)
        if previous is None or _prefer_record(record, previous):
            unique[record.source_item_id] = record
    return sorted(
        (
            record
            for record in unique.values()
            if not _is_non_book_calendar_item(record)
            and record.item_type == "tankobon"
        ),
        key=lambda record: (record.release_date, record.source_item_id),
    )


def _html_to_text(value: str) -> str:
    """Decode a small, known fragment from Rakuten's server-rendered HTML."""
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    return normalize_space(HTML_TAG_PATTERN.sub(" ", value))


def _meta_content(html_text: str, property_name: str) -> str | None:
    wanted = property_name.casefold()
    for match in META_TAG_PATTERN.finditer(html_text):
        attrs = {
            attr.group("name").casefold(): html.unescape(
                attr.group("quoted") if attr.group("quoted") is not None else attr.group("bare")
            )
            for attr in HTML_ATTRIBUTE_PATTERN.finditer(match.group("attrs"))
        }
        if attrs.get("property", "").casefold() == wanted or attrs.get("name", "").casefold() == wanted:
            return normalize_space(attrs.get("content")) or None
    return None


def _product_info_values(html_text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for item_match in PRODUCT_INFO_PATTERN.finditer(html_text):
        item_html = item_match.group("content")
        category_match = CATEGORY_PATTERN.search(item_html)
        value_match = CATEGORY_VALUE_PATTERN.search(item_html)
        if category_match is None or value_match is None:
            continue
        category = _html_to_text(category_match.group("value"))
        value = value_match.group("value")
        if category and value:
            values[category] = value
    return values


def _authors_from_product_html(value: str | None) -> str | None:
    if not value:
        return None
    # The official product page marks each contributor as an anchor followed by
    # a role such as "(著)".  Preserve a stable, importer-compatible separator.
    authors = [
        _html_to_text(anchor.group("value"))
        for anchor in ANCHOR_PATTERN.finditer(value)
        if _html_to_text(anchor.group("value"))
    ]
    if authors:
        return "|".join(dict.fromkeys(authors))
    text_value = _html_to_text(value)
    text_value = re.sub(r"\s*[（(][^()（）]*(?:著|編|原作|作画|監修|訳)[^()（）]*[）)]", "", text_value)
    return normalize_space(text_value) or None


def parse_rakuten_product_html(
    html_text: str,
    *,
    record: ComicReleaseRecord,
) -> ComicReleaseRecord:
    """Merge public product-page metadata without replacing a known value by blank data.

    Calendar pages are intentionally lightweight and often omit contributors,
    publishers and ISBNs.  A product page is the authoritative public detail
    record for the calendar item, so it is used only to fill or correct those
    fields.  The discovered cover URL stays in the audit payload; presentation
    cover fields remain governed by the existing official-store cover service.
    """
    values = _product_info_values(html_text)
    detail_author = _authors_from_product_html(values.get("著者／編集"))
    detail_publisher = _html_to_text(values.get("出版社", "")) or None
    detail_imprint = _html_to_text(values.get("レーベル", "")) or None
    detail_series = _html_to_text(values.get("シリーズ", "")) or None
    detail_isbn = normalize_isbn(
        _meta_content(html_text, "books:isbn") or _html_to_text(values.get("ISBN", ""))
    )
    detail_release_date = parse_release_date(
        _html_to_text(values.get("発売日", "")),
        expected_month=record.release_date.strftime("%Y-%m"),
    )
    raw = dict(record.raw)
    raw["detail_parser"] = "rakuten_product_page"
    cover_url = _meta_content(html_text, "og:image")
    if cover_url:
        raw["cover_candidate_url"] = cover_url
        raw["cover_candidate_source"] = "RAKUTEN_BOOKS_PRODUCT_PAGE"
    return replace(
        record,
        author_name=detail_author or record.author_name,
        publisher_name=detail_publisher or record.publisher_name,
        imprint_name=detail_imprint or record.imprint_name,
        series_name=detail_series or record.series_name,
        isbn=detail_isbn or record.isbn,
        release_date=detail_release_date or record.release_date,
        raw=raw,
    )


def enrich_rakuten_product_metadata(
    records: Iterable[ComicReleaseRecord],
    *,
    detail_limit: int = 1000,
    detail_workers: int = 3,
    cache_dir: Path | None = None,
    cache_ttl_hours: int = 168,
    fetch: Callable[[str], str] | None = None,
) -> list[ComicReleaseRecord]:
    """Fill rich metadata from the canonical Rakuten product pages.

    Individual page failures remain attached to their record as audit evidence
    and do not discard the calendar candidate.  The bounded worker count keeps
    scheduled reconciliation polite while retaining a practical runtime.
    """
    if detail_limit < 0 or detail_limit > 2000:
        raise MonthlyComicReleaseSyncError("detail_limit must be between 0 and 2000")
    if detail_workers < 1 or detail_workers > 4:
        raise MonthlyComicReleaseSyncError("detail_workers must be between 1 and 4")
    if cache_ttl_hours < 1 or cache_ttl_hours > 24 * 31:
        raise MonthlyComicReleaseSyncError("cache_ttl_hours must be between 1 and 744")
    selected = list(records)
    request_fetch = fetch or _http_get_text
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    def enrich(record: ComicReleaseRecord) -> ComicReleaseRecord:
        try:
            cache_path = (
                cache_dir / f"{re.sub(r'[^A-Za-z0-9_.-]+', '_', record.source_item_id)}.html"
                if cache_dir is not None
                else None
            )
            cache_is_fresh = bool(
                cache_path
                and cache_path.is_file()
                and (utc_now().timestamp() - cache_path.stat().st_mtime) <= cache_ttl_hours * 3600
            )
            if cache_is_fresh:
                detail_html = cache_path.read_text(encoding="utf-8", errors="replace")
                enriched_record = parse_rakuten_product_html(detail_html, record=record)
                raw = dict(enriched_record.raw)
                raw["detail_cache"] = "HIT"
                return replace(enriched_record, raw=raw)
            detail_html = request_fetch(record.source_url)
            if cache_path is not None:
                temporary_path = cache_path.with_suffix(".tmp")
                temporary_path.write_text(detail_html, encoding="utf-8")
                temporary_path.replace(cache_path)
            enriched_record = parse_rakuten_product_html(detail_html, record=record)
            raw = dict(enriched_record.raw)
            raw["detail_cache"] = "MISS"
            return replace(enriched_record, raw=raw)
        except Exception as exc:
            raw = dict(record.raw)
            raw["detail_parser"] = "rakuten_product_page_failed"
            raw["detail_error"] = type(exc).__name__
            return replace(record, raw=raw)

    if detail_limit:
        # Kobo calendar cards already contain the release metadata required by
        # this pipeline.  The physical /rb/ product parser is intentionally not
        # run against /rk/ pages, whose identity and cover are verified later
        # through the Kobo API.
        detail_indexes = [
            index
            for index, record in enumerate(selected)
            if "/rb/" in record.source_url
        ][:detail_limit]
        detail_records = [selected[index] for index in detail_indexes]
        with ThreadPoolExecutor(max_workers=min(detail_workers, len(detail_records) or 1)) as executor:
            enriched = list(executor.map(enrich, detail_records))
        for index, record in zip(detail_indexes, enriched):
            selected[index] = record
    return _dedupe_records(selected)


def _record_score(record: ComicReleaseRecord) -> int:
    return sum(
        bool(value)
        for value in (
            record.isbn,
            record.author_name,
            record.publisher_name,
            record.imprint_name,
            record.series_name,
            record.volume_label,
        )
    )


def _parser_priority(record: ComicReleaseRecord) -> int:
    return {
        "ebook_calendar": 30,
        "json_ld": 20,
        "anchor": 10,
    }.get(str(record.raw.get("parser") or ""), 0)


def _prefer_record(candidate: ComicReleaseRecord, previous: ComicReleaseRecord) -> bool:
    candidate_priority = _parser_priority(candidate)
    previous_priority = _parser_priority(previous)
    if candidate_priority != previous_priority:
        return candidate_priority > previous_priority
    return _record_score(candidate) > _record_score(previous)


def _page_links(
    html_text: str,
    *,
    page_url: str,
    expected_month: str,
) -> set[str]:
    links: set[str] = set()
    source_parts = urllib.parse.urlsplit(page_url)
    source_path = source_parts.path
    source_dates = urllib.parse.parse_qs(source_parts.query).get("tid", [])
    source_date = source_dates[0] if source_dates else ""
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", html_text, flags=re.IGNORECASE):
        url = _canonical_calendar_url(
            _absolute_rakuten_url(href, base_url=page_url)
        )
        if urllib.parse.urlsplit(url).path != source_path:
            continue
        target_query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        target_dates = target_query.get("tid", [])
        # The page links to adjacent months too.  Following them turns one
        # monthly collection into a broad crawl, so retain only pagination
        # URLs explicitly bound to the requested month.
        if not target_dates or not target_dates[0].startswith(expected_month):
            continue
        if "/daily/" in source_path and target_dates[0] != source_date:
            continue
        links.add(url)
    return links


def collect_rakuten_calendar(
    *,
    month: str,
    source_url: str = DEFAULT_SOURCE_URL,
    max_pages: int = 60,
    page_workers: int = 3,
    detail_limit: int = 1000,
    detail_workers: int = 3,
    detail_cache_dir: Path | None = None,
    detail_cache_ttl_hours: int = 168,
    fetch: Callable[[str], str] | None = None,
) -> list[ComicReleaseRecord]:
    if max_pages < 1 or max_pages > 100:
        raise MonthlyComicReleaseSyncError("max_pages must be between 1 and 100")
    if page_workers < 1 or page_workers > 4:
        raise MonthlyComicReleaseSyncError("page_workers must be between 1 and 4")
    _, _, _ = parse_month(month)
    start_url = _canonical_calendar_url(source_url.format(month=month))
    request_fetch = fetch or _http_get_text
    queue = [start_url]
    seen: set[str] = set()
    combined: dict[str, ComicReleaseRecord] = {}
    while queue and len(seen) < max_pages:
        batch: list[str] = []
        while queue and len(batch) < min(page_workers, max_pages - len(seen)):
            page_url = queue.pop(0)
            if page_url not in seen:
                seen.add(page_url)
                batch.append(page_url)
        if not batch:
            continue
        # Three concurrent GETs keeps the monthly job bounded without turning
        # a normal calendar refresh into an aggressive crawl.  Each page is
        # requested only once and every downstream write remains serialized.
        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            fetched = zip(batch, executor.map(request_fetch, batch))
            for page_url, html_text in fetched:
                for record in parse_calendar_html(html_text, expected_month=month, page_url=page_url):
                    previous = combined.get(record.source_item_id)
                    if previous is None or _prefer_record(record, previous):
                        combined[record.source_item_id] = record
                for linked_page in sorted(
                    _page_links(
                        html_text,
                        page_url=page_url,
                        expected_month=month,
                    )
                ):
                    if linked_page not in seen and linked_page not in queue:
                        queue.append(linked_page)
    if not combined:
        raise MonthlyComicReleaseSyncError(
            "RAKUTEN_CALENDAR_NO_RECORDS: save the public page as --input-csv "
            "only when the source HTML has changed, then update the parser fixture"
        )
    return enrich_rakuten_product_metadata(
        sorted(combined.values(), key=lambda record: (record.release_date, record.source_item_id)),
        detail_limit=detail_limit,
        detail_workers=detail_workers,
        cache_dir=detail_cache_dir,
        cache_ttl_hours=detail_cache_ttl_hours,
        fetch=fetch,
    )


def _http_get_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.7"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise MonthlyComicReleaseSyncError(f"SOURCE_HTTP_{response.status}")
            return response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception as exc:
        if isinstance(exc, MonthlyComicReleaseSyncError):
            raise
        raise MonthlyComicReleaseSyncError(f"SOURCE_FETCH_FAILED: {type(exc).__name__}") from exc


def load_records_csv(path: Path, *, month: str) -> list[ComicReleaseRecord]:
    _, start, end = parse_month(month)
    rows: list[ComicReleaseRecord] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise MonthlyComicReleaseSyncError("input CSV header is missing")
        for row_number, row in enumerate(reader, start=2):
            title = normalize_space(row.get("title"))
            source_item_id = normalize_space(row.get("source_item_id") or row.get("item_id"))
            if source_item_id.startswith("rakuten_books:"):
                source_item_id = source_item_id.removeprefix("rakuten_books:")
            source_url = normalize_space(row.get("source_url"))
            release_date = parse_release_date(row.get("release_date"), expected_month=month)
            if not title or not source_item_id or not source_url or release_date is None:
                raise MonthlyComicReleaseSyncError(f"input CSV row {row_number} is missing title, source_item_id, source_url, or release_date")
            if not start <= release_date < end:
                continue
            series, title_volume, title_imprint = _extract_imprint_and_series(title)
            rows.append(
                ComicReleaseRecord(
                    source_item_id=source_item_id,
                    title=title,
                    release_date=release_date,
                    source_url=source_url,
                    author_name=normalize_space(row.get("author_name") or row.get("author")) or None,
                    publisher_name=normalize_space(row.get("publisher_name") or row.get("publisher")) or None,
                    imprint_name=normalize_space(row.get("imprint_name") or row.get("label") or title_imprint) or None,
                    series_name=normalize_space(row.get("series_name") or series) or None,
                    volume_label=normalize_space(row.get("volume_label") or title_volume) or None,
                    isbn=normalize_isbn(row.get("isbn") or row.get("isbn13")),
                    raw={"parser": "csv", "row_number": row_number},
                )
            )
    return _dedupe_records(rows)


def _dedupe_records(records: Iterable[ComicReleaseRecord]) -> list[ComicReleaseRecord]:
    result: dict[str, ComicReleaseRecord] = {}
    for record in records:
        old = result.get(record.source_item_id)
        if old is None or _prefer_record(record, old):
            result[record.source_item_id] = record
    return sorted(
        (
            record
            for record in result.values()
            if not _is_non_book_calendar_item(record)
        ),
        key=lambda record: (record.release_date, record.source_item_id),
    )


def _dedupe_work_records(records: Iterable[ComicReleaseRecord]) -> list[ComicReleaseRecord]:
    """Prefer a direct Kobo record when paper and ebook calendars overlap."""

    result: dict[tuple[str, date], ComicReleaseRecord] = {}
    for record in records:
        key = (normalize_work_identity(record.title), record.release_date)
        old = result.get(key)
        if old is None:
            result[key] = record
            continue
        old_is_kobo = old.raw.get("parser") == "ebook_calendar"
        record_is_kobo = record.raw.get("parser") == "ebook_calendar"
        if record_is_kobo and not old_is_kobo:
            result[key] = record
        elif record_is_kobo == old_is_kobo and _record_score(record) > _record_score(old):
            result[key] = record
    return _dedupe_records(result.values())


def _is_non_book_calendar_item(record: ComicReleaseRecord) -> bool:
    title = normalize_space(record.title)
    return (
        title.startswith(("【特典】", "[特典]", "特典："))
        or "お風呂ポスター" in title
        or record.item_type != "tankobon"
    )


def _existing_fields(item: EbookItem) -> dict[str, Any]:
    return {
        "title": str(item.title or ""),
        "isbn": str(item.isbn or "") or None,
        "volume_label": str(item.volume_label or "") or None,
        "author_name": str(item.author_name or "") or None,
        "publisher_name": str(item.publisher_name or "") or None,
        "series_name": str(item.series_name or "") or None,
        "release_date": item.release_date.isoformat() if item.release_date else None,
    }


def _changed_fields(item: EbookItem, record: ComicReleaseRecord) -> tuple[str, ...]:
    proposed = record.csv_row()
    before = _existing_fields(item)
    fields = ("title", "isbn", "volume_label", "author_name", "publisher_name", "series_name", "release_date")
    if (
        str(
            getattr(
                item,
                "wordpress_status",
                "",
            )
            or ""
        ).upper()
        == "PUBLISHED"
    ):
        fields = tuple(
            field
            for field in fields
            if field not in {
                "title",
                "volume_label",
            }
        )
    return tuple(
        field for field in fields
        if str(before[field] or "") != str(proposed.get(field) or "") and str(proposed.get(field) or "")
    )


def build_sync_plan(
    records: list[ComicReleaseRecord],
    *,
    month: str,
    source_url: str,
    items: Iterable[EbookItem],
) -> SyncPlan:
    by_identity = {
        str(item.source_item_id): item
        for item in items
        if str(item.source_name) == SOURCE_NAME
    }
    by_isbn = {
        normalize_isbn(item.isbn): item
        for item in items
        if normalize_isbn(item.isbn)
    }
    by_title_volume: dict[tuple[str, str | None], EbookItem] = {}
    by_work_identity: dict[tuple[str, date | None], EbookItem] = {}
    by_fast_kobo_url: dict[str, EbookItem] = {}
    for item in items:
        title_key = normalize_identity(item.normalized_title or item.title)
        volume = normalize_space(item.volume_label) or None
        if title_key:
            by_title_volume.setdefault((title_key, volume), item)
        work_key = normalize_work_identity(item.title)
        if work_key:
            by_work_identity.setdefault((work_key, item.release_date), item)

        if item.source_name == "rakuten_kobo_fast_intake":
            fast_kobo_url = normalize_space(
                item.source_item_id
            )
            if fast_kobo_url.startswith(
                "https://books.rakuten.co.jp/rk/"
            ):
                by_fast_kobo_url.setdefault(
                    fast_kobo_url,
                    item,
                )

    changes: list[PlannedChange] = []
    for record in records:
        item = by_identity.get(record.catalog_source_item_id)
        if item is not None:
            fields = _changed_fields(item, record)
            changes.append(PlannedChange(record, "UPDATED" if fields else "UNCHANGED", item.id, fields))
            continue
        exact_fast_kobo = by_fast_kobo_url.get(
            normalize_space(
                record.source_url
            )
        )

        if exact_fast_kobo is not None:
            changes.append(
                PlannedChange(
                    record,
                    "UPDATED",
                    exact_fast_kobo.id,
                    _changed_fields(
                        exact_fast_kobo,
                        record,
                    ),
                    reason=FAST_KOBO_PROMOTION_REASON,
                )
            )
            continue

        cross_source = by_isbn.get(record.isbn) if record.isbn else None
        if cross_source is None:
            cross_source = by_title_volume.get((record.normalized_title, record.volume_label))
        if cross_source is None:
            cross_source = by_work_identity.get(
                (normalize_work_identity(record.title), record.release_date)
            )
        if cross_source is not None:
            changes.append(PlannedChange(record, "REVIEW_REQUIRED", cross_source.id, reason="CROSS_SOURCE_DUPLICATE"))
            continue
        changes.append(PlannedChange(record, "NEW", None))
    return SyncPlan(target_month=month, source_url=source_url, records=records, changes=changes)


def write_canonical_csv(path: Path, changes: Iterable[PlannedChange]) -> int:
    fieldnames = [
        "source_name", "source_item_id", "source_url", "title", "isbn", "normalized_title",
        "volume_label", "author_name", "author", "publisher_name", "publisher",
        "series_name", "release_date", "item_type", "wordpress_status",
    ]
    selected = [
        change
        for change in changes
        if change.action in {"NEW", "UPDATED"}
        and change.reason != FAST_KOBO_PROMOTION_REASON
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(change.record.csv_row() for change in selected)
    return len(selected)


def _require_metadata_schema(session: Any) -> None:
    result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='comic_release_sync_runs'"))
    if result.scalar_one_or_none() is None:
        raise MonthlyComicReleaseSyncError("DATABASE_SCHEMA_OUTDATED: run .venv/bin/alembic upgrade head before --execute")


def _store_metadata(
    session: Any,
    *,
    run_id: str,
    change: PlannedChange,
    item: EbookItem,
    observed_at: datetime,
) -> None:
    payload = change.record.audit_payload()
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    session.execute(
        text(
            """
            INSERT INTO comic_release_metadata (
                ebook_item_id, imprint_name, source_name, source_item_id, source_url,
                source_discovery, payload_sha256, payload_json, first_seen_at, last_seen_at
            ) VALUES (
                :ebook_item_id, :imprint_name, :source_name, :source_item_id, :source_url,
                :source_discovery, :payload_sha256, :payload_json, :observed_at, :observed_at
            )
            ON CONFLICT(ebook_item_id) DO UPDATE SET
                imprint_name=excluded.imprint_name,
                source_name=excluded.source_name,
                source_item_id=excluded.source_item_id,
                source_url=excluded.source_url,
                source_discovery=excluded.source_discovery,
                payload_sha256=excluded.payload_sha256,
                payload_json=excluded.payload_json,
                last_seen_at=excluded.last_seen_at
            """
        ),
        {
            "ebook_item_id": item.id,
            "imprint_name": change.record.imprint_name,
            "source_name": SOURCE_LABEL,
            "source_item_id": change.record.source_item_id,
            "source_url": change.record.source_url,
            "source_discovery": SOURCE_DISCOVERY,
            "payload_sha256": payload_hash,
            "payload_json": payload_json,
            "observed_at": observed_at,
        },
    )
    session.execute(
        text(
            """
            INSERT INTO comic_release_sync_events (
                id, run_id, ebook_item_id, change_type, changed_fields, before_json, after_json, observed_at
            ) VALUES (
                :id, :run_id, :ebook_item_id, :change_type, :changed_fields, :before_json, :after_json, :observed_at
            )
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "ebook_item_id": item.id,
            "change_type": change.action,
            "changed_fields": json.dumps(list(change.changed_fields), ensure_ascii=False),
            "before_json": None,
            "after_json": payload_json,
            "observed_at": observed_at,
        },
    )


def backup_database(*, repository_root: Path, run_id: str) -> Path:
    source = repository_root / "data" / "database" / "ebook_affiliate.db"
    if not source.is_file():
        raise MonthlyComicReleaseSyncError(f"database not found: {source}")
    destination = repository_root / "backups" / f"monthly_comic_release_sync_{run_id}" / "ebook_affiliate_before.db"
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    return destination


def _promote_exact_fast_kobo_item(
    session,
    *,
    change: PlannedChange,
    run_id: str,
    observed_at,
) -> EbookItem:
    """Promote one exact-URL fast Kobo row to monthly identity in-place."""

    if change.reason != FAST_KOBO_PROMOTION_REASON:
        raise MonthlyComicReleaseSyncError(
            "invalid fast Kobo promotion reason"
        )

    existing_id = str(
        change.existing_ebook_item_id
        or ""
    )

    if not existing_id:
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion missing existing ebook item id"
        )

    item = session.get(
        EbookItem,
        existing_id,
    )

    if item is None:
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion target not found"
        )

    if item.source_name != "rakuten_kobo_fast_intake":
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion target source mismatch"
        )

    record = change.record

    exact_url = normalize_space(
        record.source_url
    )

    if not exact_url.startswith(
        "https://books.rakuten.co.jp/rk/"
    ):
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion URL is not official Kobo URL"
        )

    if normalize_space(
        item.source_item_id
    ) != exact_url:
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion source URL mismatch"
        )

    offers = list(
        session.scalars(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id
                == item.id,
                StoreOffer.store_name
                == "rakuten_kobo",
                StoreOffer.product_url
                == exact_url,
            )
        )
    )

    if len(offers) != 1:
        raise MonthlyComicReleaseSyncError(
            "fast Kobo promotion requires exactly one matching Kobo offer"
        )

    identity_owner = session.scalar(
        select(EbookItem)
        .where(
            EbookItem.source_name
            == SOURCE_NAME,
            EbookItem.source_item_id
            == record.catalog_source_item_id,
            EbookItem.id
            != item.id,
        )
        .limit(1)
    )

    if identity_owner is not None:
        raise MonthlyComicReleaseSyncError(
            "monthly identity already belongs to another ebook item"
        )

    published = (
        str(
            item.wordpress_status
            or ""
        ).upper()
        == "PUBLISHED"
    )

    if not published:
        item.title = record.title
        item.normalized_title = record.title
        item.volume_label = (
            record.volume_label
            or item.volume_label
        )

    if record.isbn:
        item.isbn = record.isbn

    if record.author_name:
        item.author_name = (
            record.author_name
        )

    if record.publisher_name:
        item.publisher_name = (
            record.publisher_name
        )

    if record.series_name:
        item.series_name = (
            record.series_name
        )

    if record.release_date:
        item.release_date = (
            record.release_date
        )

    if record.item_type:
        item.item_type = record.item_type

    item.source_name = SOURCE_NAME
    item.source_item_id = (
        record.catalog_source_item_id
    )
    item.source_discovery = (
        SOURCE_DISCOVERY
    )
    item.source_url = exact_url

    _store_metadata(
        session,
        run_id=run_id,
        change=change,
        item=item,
        observed_at=observed_at,
    )

    session.flush()

    return item


def apply_plan(
    *,
    plan: SyncPlan,
    canonical_csv: Path,
    run_id: str,
    execute: bool,
    selected_changes: list[PlannedChange],
) -> dict[str, Any]:
    if not execute:
        with SessionLocal() as session:
            summary = CsvImportService(session).import_file(canonical_csv, dry_run=True, commit=False)
        return {"mode": "DRY_RUN", "database_write_performed": False, **asdict(summary)}
    observed_at = utc_now()
    with SessionLocal() as session:
        _require_metadata_schema(session)
        session.execute(
            text(
                """
                INSERT INTO comic_release_sync_runs (
                    id, target_month, source_url, mode, started_at, status, summary_json
                ) VALUES (:id, :target_month, :source_url, 'EXECUTE', :started_at, 'RUNNING', '{}')
                """
            ),
            {"id": run_id, "target_month": plan.target_month, "source_url": plan.source_url, "started_at": observed_at},
        )
        promotion_changes = [
            change
            for change in selected_changes
            if change.reason
            == FAST_KOBO_PROMOTION_REASON
        ]

        standard_changes = [
            change
            for change in selected_changes
            if change.reason
            != FAST_KOBO_PROMOTION_REASON
        ]

        summary = CsvImportService(session).import_file(
            canonical_csv,
            dry_run=False,
            commit=False,
        )

        by_identity = {
            str(item.source_item_id): item
            for item in session.scalars(
                select(EbookItem).where(
                    EbookItem.source_name
                    == SOURCE_NAME
                )
            )
        }

        item_ids: list[str] = []

        for change in standard_changes:
            item = by_identity.get(
                change.record.catalog_source_item_id
            )

            if item is None:
                raise MonthlyComicReleaseSyncError(
                    "import did not produce expected ebook item"
                )

            item.source_discovery = (
                SOURCE_DISCOVERY
            )

            item.source_url = (
                change.record.source_url
            )

            _store_metadata(
                session,
                run_id=run_id,
                change=change,
                item=item,
                observed_at=observed_at,
            )

            item_ids.append(
                item.id
            )

        for change in promotion_changes:
            item = (
                _promote_exact_fast_kobo_item(
                    session,
                    change=change,
                    run_id=run_id,
                    observed_at=observed_at,
                )
            )

            item_ids.append(
                item.id
            )
        result = {"mode": "EXECUTE", "database_write_performed": True, **asdict(summary), "ebook_item_ids": item_ids}
        session.execute(
            text("UPDATE comic_release_sync_runs SET completed_at=:completed_at, status='PASS', summary_json=:summary_json WHERE id=:id"),
            {"completed_at": utc_now(), "summary_json": json.dumps(result, ensure_ascii=False, sort_keys=True), "id": run_id},
        )
        session.commit()
    return result


def _kobo_enrich(ebook_item_id: str, *, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"ebook_item_id": ebook_item_id, "status": "SKIPPED_DRY_RUN"}
    from app.services.manual_store_offer_service import ManualStoreOfferService
    from app.services.rakuten_kobo_manual_offer_resolver import fetch_official_kobo_items_by_title
    from scripts.database.import_new_release_from_asin_fast import kobo_offer_kwargs, select_high_confidence_kobo_candidate
    with SessionLocal() as session:
        item = session.get(EbookItem, ebook_item_id)
        if item is None:
            return {"ebook_item_id": ebook_item_id, "status": "ITEM_NOT_FOUND"}
        existing = session.scalar(select(StoreOffer).where(StoreOffer.ebook_item_id == item.id, StoreOffer.store_name == "rakuten_kobo").limit(1))
        if existing is not None:
            return {"ebook_item_id": item.id, "status": "NOOP_ALREADY_PRESENT", "store_item_id": existing.store_item_id}
        try:
            direct_match = re.fullmatch(
                r"rakuten_books:rk-(\d{13})",
                str(item.source_item_id or ""),
            )
            direct_url = str(item.source_url or "").strip()
            if direct_match and EBOOK_PRODUCT_URL_PATTERN.fullmatch(direct_url):
                from app.services.affiliate_account_settings_service import (
                    AffiliateAccountSettingsService,
                )
                from app.services.rakuten_kobo_affiliate_link_service import (
                    RakutenKoboAffiliateLinkService,
                )

                affiliate_id = AffiliateAccountSettingsService(
                    session
                ).get_affiliate_id(service_name="rakuten_kobo")
                if affiliate_id:
                    metadata_json = session.execute(
                        text(
                            "SELECT payload_json FROM comic_release_metadata "
                            "WHERE ebook_item_id=:item_id LIMIT 1"
                        ),
                        {"item_id": item.id},
                    ).scalar_one_or_none()
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    price_yen = (metadata.get("raw") or {}).get("price_yen")
                    result = ManualStoreOfferService(session).create_offer(
                        ebook_item_id=item.id,
                        store_name="rakuten_kobo",
                        product_url=direct_url,
                        affiliate_url=RakutenKoboAffiliateLinkService().generate(
                            product_url=direct_url,
                            affiliate_id=affiliate_id,
                        ).affiliate_url,
                        price=str(price_yen or ""),
                        currency="JPY",
                        availability_status="FOUND",
                        observed_at=None,
                        operator="system:monthly_comic_release_sync",
                        canonical_store_item_id=direct_match.group(1),
                    )
                    session.commit()
                    return {
                        "ebook_item_id": item.id,
                        "status": "SAVED",
                        "offer_id": result.offer_id,
                        "store_item_id": direct_match.group(1),
                        "selection": {"method": "Kobo calendar direct identity"},
                    }
            candidates = fetch_official_kobo_items_by_title(item.title, hits=5)
            selected, diagnostic = select_high_confidence_kobo_candidate(
                title=item.title, item_type=item.item_type, volume_label=item.volume_label,
                release_date=item.release_date, publisher_name=item.publisher_name, candidates=candidates,
            )
            if selected is None:
                return {"ebook_item_id": item.id, "status": "REVIEW_REQUIRED", "selection": diagnostic}
            result = ManualStoreOfferService(session).create_offer(ebook_item_id=item.id, **kobo_offer_kwargs(selected))
            session.commit()
            return {"ebook_item_id": item.id, "status": "SAVED", "offer_id": result.offer_id, "selection": diagnostic}
        except Exception as exc:
            session.rollback()
            reason_code = str(exc) or type(exc).__name__
            status = "SKIPPED_NOT_CONFIGURED" if reason_code == "KOBO_OFFICIAL_API_NOT_CONFIGURED" else "FAILED"
            result = {"ebook_item_id": item.id, "status": status, "reason_code": reason_code}
            safe_summary = getattr(getattr(exc, "__cause__", None), "safe_summary", None)
            if safe_summary:
                result["diagnostic_code"] = safe_summary
            return result


def _dmm_enrich(ebook_item_id: str, *, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"ebook_item_id": ebook_item_id, "status": "SKIPPED_DRY_RUN"}
    from app.services.dmm_initial_discovery_service import DmmInitialDiscoveryService
    with SessionLocal() as session:
        try:
            result = DmmInitialDiscoveryService(session).run(ebook_item_id)
            if result.changed:
                session.commit()
            else:
                session.rollback()
            return {"ebook_item_id": ebook_item_id, "status": result.status, "reason_code": result.reason_code, "store_item_id": result.store_item_id}
        except Exception as exc:
            session.rollback()
            return {"ebook_item_id": ebook_item_id, "status": "FAILED", "reason_code": type(exc).__name__}


def _kindle_enrich(
    ebook_item_id: str,
    *,
    execute: bool,
    client: Any | None = None,
    client_error: Exception | None = None,
) -> dict[str, Any]:
    if not execute:
        return {"ebook_item_id": ebook_item_id, "status": "SKIPPED_DRY_RUN"}
    # Creators API is the only automated Amazon title-search path.  When its
    # separate credentials are absent, retain the prior non-scraping review
    # path instead of attempting public-page automation.
    from app.integrations.amazon_creators_api_client import (
        AmazonCreatorsApiClient,
        AmazonCreatorsApiError,
    )
    from app.services.amazon_creators_kindle_resolver import (
        AmazonCreatorsKindleResolver,
    )
    with SessionLocal() as session:
        try:
            item = session.get(EbookItem, ebook_item_id)
            if item is None:
                return {"ebook_item_id": ebook_item_id, "status": "ITEM_NOT_FOUND"}
            existing = session.scalar(select(StoreOffer).where(StoreOffer.ebook_item_id == item.id, StoreOffer.store_name == "amazon").limit(1))
            if existing is not None:
                return {"ebook_item_id": item.id, "status": "NOOP_ALREADY_PRESENT", "store_item_id": existing.store_item_id}
            if client_error is not None:
                raise client_error
            active_client = client or AmazonCreatorsApiClient.from_environment()
            result = AmazonCreatorsKindleResolver(session, active_client).resolve(
                ebook_item_id=item.id,
                execute=execute,
            )
            if execute and result.status == "SAVED":
                session.commit()
            else:
                session.rollback()
            return {
                "ebook_item_id": item.id,
                "status": result.status,
                "candidate_count": result.candidate_count,
                "asin": result.asin,
                "cover_status": "COVER_FOUND" if result.cover_url else "COVER_MISSING",
                "match_score": result.score,
                "match_classification": result.classification,
                "match_reasons": list(getattr(result, "reasons", ())),
                "offer_id": result.offer_id,
            }
        except AmazonCreatorsApiError as exc:
            session.rollback()
            if exc.code == "CREATORS_CREDENTIALS_NOT_CONFIGURED":
                return {"ebook_item_id": item.id, "status": "REVIEW_REQUIRED_NO_CREATORS_CREDENTIAL"}
            return {
                "ebook_item_id": item.id,
                "status": "API_ERROR",
                "reason_code": exc.safe_summary,
            }
        except Exception as exc:
            session.rollback()
            return {
                "ebook_item_id": ebook_item_id,
                "status": "FAILED",
                "reason_code": type(exc).__name__,
            }
        finally:
            if client is None and "active_client" in locals():
                active_client.close()


def _cover_reconcile(ebook_item_id: str, *, execute: bool) -> dict[str, Any]:
    if not execute:
        return {"ebook_item_id": ebook_item_id, "status": "SKIPPED_DRY_RUN"}
    from app.services.official_cover_automation_service import RakutenKoboCoverReconciliationService
    with SessionLocal() as session:
        try:
            result = RakutenKoboCoverReconciliationService(session).reconcile_item(ebook_item_id)
            return {"ebook_item_id": ebook_item_id, "status": result.status, "reason_code": result.reason_code, "api_called": result.api_called}
        except Exception as exc:
            session.rollback()
            return {"ebook_item_id": ebook_item_id, "status": "FAILED", "reason_code": type(exc).__name__}


def enrich_items(
    item_ids: Iterable[str],
    *,
    execute: bool,
    kobo_limit: int,
    dmm_limit: int,
    kindle_limit: int,
    cover_limit: int,
    target_ids: Mapping[str, Iterable[str]] | None = None,
    kobo_pacing_seconds: float = 0,
    dmm_pacing_seconds: float = 0,
    cover_pacing_seconds: float = 0,
) -> dict[str, list[dict[str, Any]]]:
    unique_ids = list(dict.fromkeys(item_ids))
    targets = {
        name: list(dict.fromkeys(values))
        for name, values in (target_ids or {}).items()
    }
    kobo_ids = targets.get("rakuten_kobo", unique_ids)[:kobo_limit]
    dmm_ids = targets.get("dmm", unique_ids)[:dmm_limit]
    kindle_ids = targets.get("kindle", unique_ids)[:kindle_limit]
    cover_ids = targets.get("covers")
    kobo: list[dict[str, Any]] = []
    kobo_rate_limited = False
    for index, ebook_item_id in enumerate(kobo_ids):
        if kobo_rate_limited:
            kobo.append(
                {
                    "ebook_item_id": ebook_item_id,
                    "status": "DEFERRED_RATE_LIMIT",
                    "reason_code": "KOBO_OFFICIAL_API_RATE_LIMIT",
                }
            )
            continue
        if execute and index and kobo_pacing_seconds:
            time.sleep(kobo_pacing_seconds)
        result = _kobo_enrich(ebook_item_id, execute=execute)
        if result.get("diagnostic_code") == "HTTP_STATUS_ERROR;status=429":
            result["status"] = "DEFERRED_RATE_LIMIT"
            result["reason_code"] = "KOBO_OFFICIAL_API_RATE_LIMIT"
            kobo_rate_limited = True
        kobo.append(result)
    dmm: list[dict[str, Any]] = []
    for index, item_id in enumerate(dmm_ids):
        if execute and index and dmm_pacing_seconds:
            time.sleep(dmm_pacing_seconds)
        dmm.append(_dmm_enrich(item_id, execute=execute))
    kindle: list[dict[str, Any]] = []
    kindle_client: Any | None = None
    kindle_client_error: Exception | None = None
    if execute and kindle_ids:
        from app.integrations.amazon_creators_api_client import (
            AmazonCreatorsApiClient,
            AmazonCreatorsApiError,
        )
        try:
            kindle_client = AmazonCreatorsApiClient.from_environment(
                minimum_request_interval_seconds=AMAZON_CREATORS_MIN_REQUEST_INTERVAL_SECONDS,
            )
        except AmazonCreatorsApiError as exc:
            kindle_client_error = exc
    try:
        for item_id in kindle_ids:
            try:
                kindle.append(
                    _kindle_enrich(
                        item_id,
                        execute=execute,
                        client=kindle_client,
                        client_error=kindle_client_error,
                    )
                )
            except Exception as exc:
                kindle.append(
                    {
                        "ebook_item_id": item_id,
                        "status": "FAILED",
                        "reason_code": type(exc).__name__,
                    }
                )
    finally:
        if kindle_client is not None:
            kindle_client.close()
    newly_saved_kobo = [
        entry["ebook_item_id"]
        for entry in kobo
        if entry.get("status") == "SAVED"
    ]
    cover_candidates = list(dict.fromkeys(
        (cover_ids or []) + newly_saved_kobo
    )) if cover_ids is not None else [
        entry["ebook_item_id"]
        for entry in kobo
        if entry.get("status") in {"SAVED", "NOOP_ALREADY_PRESENT"}
    ]
    covers: list[dict[str, Any]] = []
    for index, item_id in enumerate(cover_candidates[:cover_limit]):
        if execute and index and cover_pacing_seconds:
            time.sleep(cover_pacing_seconds)
        covers.append(_cover_reconcile(item_id, execute=execute))
    return {"rakuten_kobo": kobo, "dmm": dmm, "kindle": kindle, "covers": covers}


def monthly_sync_item_ids(*, month: str) -> list[str]:
    """Resume store/cover enrichment after a completed import or prior failure."""
    _, start, end = parse_month(month)
    with SessionLocal() as session:
        return list(
            session.scalars(
                select(EbookItem.id)
                .where(
                    EbookItem.source_name == SOURCE_NAME,
                    EbookItem.source_item_id.like("rakuten_books:%"),
                    EbookItem.release_date >= start,
                    EbookItem.release_date < end,
                )
                .order_by(EbookItem.release_date, EbookItem.id)
            )
        )


def monthly_enrichment_target_ids(
    *, month: str, reference_date: date | None = None,
) -> dict[str, list[str]]:
    """Select independent retry backlogs without consuming limits on NOOPs."""
    _, start, end = parse_month(month)
    operational_date = reference_date or date.today()
    # The final days of a month may have next-month releases inside P1.
    selection_end = (
        max(end, operational_date + timedelta(days=8))
        if start <= operational_date < end
        else end
    )
    with SessionLocal() as session:
        base = (
            EbookItem.source_name == SOURCE_NAME,
            EbookItem.source_item_id.like("rakuten_books:%"),
            EbookItem.release_date >= start,
            EbookItem.release_date < selection_end,
        )

        def missing_offer(store_name: str) -> list[str]:
            offer_exists = select(StoreOffer.id).where(
                StoreOffer.ebook_item_id == EbookItem.id,
                StoreOffer.store_name == store_name,
            ).exists()
            return list(
                session.scalars(
                    select(EbookItem.id)
                    .where(*base, EbookItem.is_excluded.is_(False), ~offer_exists)
                    .order_by(EbookItem.release_date, EbookItem.id)
                )
            )

        kobo_offer_exists = select(StoreOffer.id).where(
            StoreOffer.ebook_item_id == EbookItem.id,
            StoreOffer.store_name == "rakuten_kobo",
        ).exists()
        covers = list(
            session.scalars(
                select(EbookItem.id)
                .where(
                    *base,
                    kobo_offer_exists,
                    EbookItem.cover_status != "AUTO_ALLOWED",
                    EbookItem.release_date < end,
                )
                .order_by(EbookItem.release_date, EbookItem.id)
            )
        )
        return {
            "rakuten_kobo": missing_offer("rakuten_kobo"),
            "dmm": missing_offer("dmm"),
            "kindle": missing_offer("amazon"),
            "covers": covers,
        }


def monthly_enrichment_candidate_dates(
    *, month: str, reference_date: date,
) -> dict[str, date | None]:
    """Read release dates for candidates selected by the existing source scope."""
    _, start, end = parse_month(month)
    selection_end = (
        max(end, reference_date + timedelta(days=8))
        if start <= reference_date < end
        else end
    )
    with SessionLocal() as session:
        return {
            item_id: release_date
            for item_id, release_date in session.execute(
                select(EbookItem.id, EbookItem.release_date).where(
                    EbookItem.source_name == SOURCE_NAME,
                    EbookItem.source_item_id.like("rakuten_books:%"),
                    EbookItem.release_date >= start,
                    EbookItem.release_date < selection_end,
                )
            )
        }


def rotate_daily_backlog(
    values: Iterable[str], *, limit: int, reference_date: date | None = None,
) -> list[str]:
    ordered = list(values)
    if not ordered or limit <= 0:
        return ordered
    offset = ((reference_date or date.today()).toordinal() * limit) % len(ordered)
    return ordered[offset:] + ordered[:offset]


def prioritize_enrichment_candidates(
    candidates: Iterable[tuple[str, date | None]],
    *, reference_date: date, sync_month: str, limit: int,
    rotate: bool, rotation_date: date | None = None,
) -> list[str]:
    """Order already eligible candidates; retain rotation inside each band."""
    bands: list[list[str]] = [[], [], [], []]
    undated: list[str] = []
    next_week = reference_date + timedelta(days=7)
    for item_id, release_date in candidates:
        if release_date is None:
            undated.append(item_id)
            continue
        if release_date == reference_date:
            band = 0
        elif reference_date < release_date <= next_week:
            band = 1
        elif release_date.strftime("%Y-%m") == sync_month and release_date > reference_date:
            band = 2
        else:
            band = 3
        bands[band].append(item_id)
    ordered = [
        item_id
        for band in bands
        for item_id in (
            rotate_daily_backlog(
                band, limit=limit, reference_date=rotation_date or reference_date,
            ) if rotate else band
        )
    ]
    ordered.extend(undated)
    return ordered[:max(0, limit)]


def summarize_enrichment(
    enrichment: Mapping[str, Iterable[Mapping[str, Any]]],
) -> dict[str, Any]:
    materialized = {name: list(entries) for name, entries in enrichment.items()}
    statuses = {
        name: Counter(str(entry.get("status") or "UNKNOWN") for entry in entries)
        for name, entries in materialized.items()
    }
    dmm_no_match = sum(
        entry.get("reason_code") == "DMM_PRODUCT_NOT_FOUND"
        for entry in materialized.get("dmm", [])
    )
    failed = sum(
        counts.get("FAILED", 0) + counts.get("API_ERROR", 0)
        for counts in statuses.values()
    )
    return {
        "KOBO_TARGET": sum(statuses.get("rakuten_kobo", {}).values()),
        "KOBO_FOUND": statuses.get("rakuten_kobo", {}).get("SAVED", 0),
        "KOBO_PENDING": statuses.get("rakuten_kobo", {}).get("SKIPPED_DRY_RUN", 0),
        "KOBO_AMBIGUOUS": statuses.get("rakuten_kobo", {}).get("REVIEW_REQUIRED", 0),
        "KOBO_REVIEW_REQUIRED": statuses.get("rakuten_kobo", {}).get("REVIEW_REQUIRED", 0),
        "KOBO_RATE_LIMITED": statuses.get("rakuten_kobo", {}).get("DEFERRED_RATE_LIMIT", 0),
        "KOBO_RATE_LIMIT": statuses.get("rakuten_kobo", {}).get("DEFERRED_RATE_LIMIT", 0),
        "DMM_TARGET": sum(statuses.get("dmm", {}).values()),
        "DMM_FOUND": statuses.get("dmm", {}).get("READY", 0),
        "DMM_INCOMPLETE": statuses.get("dmm", {}).get("INCOMPLETE", 0) - dmm_no_match,
        "DMM_NO_MATCH": dmm_no_match,
        "KINDLE_TARGET": sum(statuses.get("kindle", {}).values()),
        "KINDLE_FOUND": statuses.get("kindle", {}).get("SAVED", 0),
        "KINDLE_REVIEW_REQUIRED": statuses.get("kindle", {}).get("REVIEW_REQUIRED", 0),
        "KINDLE_NO_MATCH": statuses.get("kindle", {}).get("NO_MATCH", 0),
        "COVER_TARGET": sum(statuses.get("covers", {}).values()),
        "COVER_OK": statuses.get("covers", {}).get("AUTO_ALLOWED", 0),
        "COVER_PENDING": statuses.get("covers", {}).get("HIDDEN_UNVERIFIED", 0),
        "COVER_API_FAILURE": sum(
            entry.get("reason_code") == "API_FAILURE"
            for entry in materialized.get("covers", [])
        ),
        "COVER_NO_SOURCE": sum(
            entry.get("reason_code") == "NO_OFFICIAL_STORE_OFFER"
            for entry in materialized.get("covers", [])
        ),
        "FAILED": failed,
        "status_counts": {
            name: dict(sorted(counts.items())) for name, counts in statuses.items()
        },
    }


def monthly_completion_metrics(
    *,
    total_month_items: int,
    backlog_counts: Mapping[str, int],
    any_store_found: int,
    cover_ok: int,
) -> dict[str, Any]:
    """Return month-wide rates from retry backlogs without changing selection."""
    total = max(0, int(total_month_items))

    def rate(found: int) -> float:
        return round(found / total, 6) if total else 0.0

    return {
        "TOTAL_MONTH_ITEMS": total,
        "KOBO_FOUND_RATE": rate(total - int(backlog_counts["rakuten_kobo"])),
        "DMM_FOUND_RATE": rate(total - int(backlog_counts["dmm"])),
        "KINDLE_FOUND_RATE": rate(total - int(backlog_counts["kindle"])),
        "ANY_STORE_FOUND_RATE": rate(any_store_found),
        "COVER_OK_RATE": rate(cover_ok),
    }


def monthly_any_store_found_count(*, month: str) -> int:
    _, start, end = parse_month(month)
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count(func.distinct(EbookItem.id)))
                .join(StoreOffer)
                .where(
                    EbookItem.source_name == SOURCE_NAME,
                    EbookItem.source_item_id.like("rakuten_books:%"),
                    EbookItem.release_date >= start,
                    EbookItem.release_date < end,
                )
            )
            or 0
        )


def monthly_cover_ok_count(*, month: str) -> int:
    _, start, end = parse_month(month)
    with SessionLocal() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(EbookItem)
                .where(
                    EbookItem.source_name == SOURCE_NAME,
                    EbookItem.source_item_id.like("rakuten_books:%"),
                    EbookItem.release_date >= start,
                    EbookItem.release_date < end,
                    EbookItem.cover_status == "AUTO_ALLOWED",
                )
            )
            or 0
        )


def enrichment_database_write_performed(
    enrichment: Mapping[str, Iterable[Mapping[str, Any]]],
) -> bool:
    write_statuses = {
        "rakuten_kobo": {"SAVED"},
        "dmm": {"READY"},
        "kindle": {"SAVED"},
        # Cover reconciliation commits both verified covers and durable,
        # deduplicated audit-queue state for unresolved outcomes.
        "covers": {"AUTO_ALLOWED", "HIDDEN_UNVERIFIED", "UNAVAILABLE"},
    }
    return any(
        str(entry.get("status") or "") in write_statuses.get(name, set())
        for name, entries in enrichment.items()
        for entry in entries
    )


def write_report(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def run_monthly_sync(
    *,
    repository_root: Path,
    month: str,
    execute: bool,
    phase: str,
    input_csv: Path | None = None,
    source_url: str = DEFAULT_SOURCE_URL,
    max_pages: int = 60,
    page_workers: int = 3,
    detail_limit: int = 1000,
    detail_workers: int = 3,
    detail_cache_ttl_hours: int = 168,
    sample_size: int | None = None,
    create_backup: bool = True,
    kobo_limit: int = 100,
    dmm_limit: int = 100,
    kindle_limit: int = 100,
    cover_limit: int = 100,
    kobo_pacing_seconds: float = 0,
    dmm_pacing_seconds: float = 0,
    cover_pacing_seconds: float = 0,
    rotate_backlog: bool = False,
) -> dict[str, Any]:
    if phase not in {"plan", "apply", "enrich", "all"}:
        raise MonthlyComicReleaseSyncError("phase must be plan, apply, enrich, or all")
    normalized_month, _, _ = parse_month(month)
    operational_date = date.today()
    run_id = f"{normalized_month.replace('-', '')}_{uuid.uuid4().hex[:12]}"
    runtime_dir = repository_root / "exchange" / "runtime" / "monthly_comic_release_sync" / normalized_month / run_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if input_csv:
        records = load_records_csv(input_csv, month=normalized_month)
    else:
        records = collect_rakuten_calendar(
            month=normalized_month,
            source_url=source_url,
            max_pages=max_pages,
            page_workers=page_workers,
            detail_limit=detail_limit,
            detail_workers=detail_workers,
            detail_cache_dir=(repository_root / "exchange" / "runtime" / "monthly_comic_release_sync" / normalized_month / "product_detail_cache"),
            detail_cache_ttl_hours=detail_cache_ttl_hours,
        )
        today = operational_date
        if today.strftime("%Y-%m") == normalized_month:
            ebook_daily_url = DEFAULT_EBOOK_DAILY_SOURCE_URL.format(
                day=today.isoformat()
            )
            ebook_records = collect_rakuten_calendar(
                month=normalized_month,
                source_url=ebook_daily_url,
                max_pages=max_pages,
                page_workers=page_workers,
                detail_limit=0,
                detail_workers=detail_workers,
            )
            records = _dedupe_work_records([*records, *ebook_records])
    with SessionLocal() as session:
        # Rollback would expire ORM attributes.  The plan is intentionally
        # evaluated after the read-only session closes, so retain only scalar
        # values instead of detached ORM instances.
        items = [
            SimpleNamespace(
                id=item.id,
                source_name=item.source_name,
                source_item_id=item.source_item_id,
                title=item.title,
                normalized_title=item.normalized_title,
                isbn=item.isbn,
                volume_label=item.volume_label,
                wordpress_status=item.wordpress_status,
                author_name=item.author_name,
                publisher_name=item.publisher_name,
                series_name=item.series_name,
                release_date=item.release_date,
            )
            for item in session.scalars(select(EbookItem))
        ]
    resolved_source_url = source_url.format(month=normalized_month)
    plan = build_sync_plan(records, month=normalized_month, source_url=resolved_source_url, items=items)
    selected = plan.actionable[:sample_size] if sample_size is not None else plan.actionable
    canonical_csv = runtime_dir / "canonical_import.csv"
    canonical_count = write_canonical_csv(canonical_csv, selected)
    payload: dict[str, Any] = {
        "status": "PASS", "mode": "EXECUTE" if execute else "DRY_RUN", "phase": phase,
        "run_id": run_id, "target_month": normalized_month, "source_url": resolved_source_url,
        "record_count": len(records), "plan_counts": plan.counts(), "selected_count": len(selected),
        "canonical_csv": str(canonical_csv), "canonical_count": canonical_count,
        "database_write_performed": False, "external_store_requests_performed": False,
        "changes": [{"source_item_id": c.record.source_item_id, "title": c.record.title, "action": c.action, "existing_ebook_item_id": c.existing_ebook_item_id, "changed_fields": list(c.changed_fields), "reason": c.reason} for c in plan.changes],
    }
    write_report(runtime_dir / "plan.json", payload)
    if phase == "plan":
        return payload
    if phase in {"apply", "all"}:
        if execute and create_backup:
            payload["backup_path"] = str(backup_database(repository_root=repository_root, run_id=run_id))
        import_result = apply_plan(plan=plan, canonical_csv=canonical_csv, run_id=run_id, execute=execute, selected_changes=selected)
        payload["import"] = import_result
        payload["database_write_performed"] = bool(import_result.get("database_write_performed"))
    if phase in {"enrich", "all"}:
        imported_item_ids = payload.get("import", {}).get("ebook_item_ids", []) if execute else []
        target_ids = monthly_enrichment_target_ids(
            month=normalized_month, reference_date=operational_date,
        )
        backlog_counts = {name: len(values) for name, values in target_ids.items()}
        release_dates = monthly_enrichment_candidate_dates(
            month=normalized_month, reference_date=operational_date,
        )
        month_backlog_counts = {
            name: sum(
                release_dates.get(item_id) is not None
                and release_dates[item_id].strftime("%Y-%m") == normalized_month
                for item_id in values
            )
            for name, values in target_ids.items()
        }
        completion_metrics = monthly_completion_metrics(
            total_month_items=len(monthly_sync_item_ids(month=normalized_month)),
            backlog_counts=month_backlog_counts,
            any_store_found=monthly_any_store_found_count(month=normalized_month),
            cover_ok=monthly_cover_ok_count(month=normalized_month),
        )
        limits = {
            "rakuten_kobo": kobo_limit, "dmm": dmm_limit,
            "kindle": kindle_limit,
        }
        cover_candidates = target_ids["covers"]
        target_ids = {
            store: prioritize_enrichment_candidates(
                ((item_id, release_dates.get(item_id)) for item_id in values),
                reference_date=operational_date, sync_month=normalized_month,
                limit=limits[store], rotate=rotate_backlog,
                rotation_date=operational_date,
            )
            for store, values in target_ids.items() if store in limits
        }
        target_ids["covers"] = (
            rotate_daily_backlog(
                cover_candidates,
                limit=cover_limit, reference_date=operational_date,
            ) if rotate_backlog else cover_candidates
        )
        item_ids = list(dict.fromkeys(
            imported_item_ids
            + [item_id for values in target_ids.values() for item_id in values]
        ))
        payload["enrichment_item_count"] = len(item_ids)
        payload["enrichment_backlog_counts"] = backlog_counts
        payload["enrichment"] = enrich_items(
            item_ids,
            execute=execute,
            kobo_limit=kobo_limit,
            dmm_limit=dmm_limit,
            kindle_limit=kindle_limit,
            cover_limit=cover_limit,
            target_ids=target_ids,
            kobo_pacing_seconds=kobo_pacing_seconds,
            dmm_pacing_seconds=dmm_pacing_seconds,
            cover_pacing_seconds=cover_pacing_seconds,
        )
        try:
            with SessionLocal() as shadow_session:
                payload["fast_intake_shadow"] = (
                    collect_monthly_fast_intake_shadow_handoffs(
                        shadow_session,
                        payload["enrichment"],
                    )
                )
        except Exception as exc:
            payload["fast_intake_shadow"] = {
                "status": "ERROR",
                "reason_code": (
                    type(exc).__name__
                ),
                "row_count": 0,
                "ready_count": 0,
                "stores": {},
            }

        payload["enrichment_summary"] = {
            **summarize_enrichment(payload["enrichment"]),
            **completion_metrics,
        }
        payload["database_write_performed"] = bool(
            payload["database_write_performed"]
            or enrichment_database_write_performed(payload["enrichment"])
        )
        payload["external_store_requests_performed"] = bool(execute and item_ids)
    write_report(runtime_dir / "result.json", payload)
    return payload
