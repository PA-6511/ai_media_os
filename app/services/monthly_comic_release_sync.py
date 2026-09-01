from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import sqlite3
import tempfile
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Mapping

from sqlalchemy import select, text

from app.db.models import EbookItem, StoreOffer
from app.db.session import SessionLocal
from app.services.csv_import_service import CsvImportService
from app.services.rakuten_comic_calendar_parser import split_title_volume_imprint


SOURCE_NAME = "new_release_multistore"
SOURCE_DISCOVERY = "RAKUTEN_BOOKS_COMIC_CALENDAR"
SOURCE_LABEL = "rakuten_books_comic_calendar"
DEFAULT_SOURCE_URL = (
    "https://books.rakuten.co.jp/calendar/001001/monthly/"
    "?s=14&tid={month}-01&v=2"
)
USER_AGENT = "AI-Media-OS-MonthlyComicReleaseSync/1.0 (+https://example.invalid)"
MONTH_PATTERN = re.compile(r"^(20\d{2})-(0[1-9]|1[0-2])$")
ISBN_PATTERN = re.compile(r"(?<!\d)(97[89][\d-]{10,16}\d)(?!\d)")
PRODUCT_ID_PATTERN = re.compile(r"/rb/([0-9]+)/?")
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
            "item_type": "tankobon",
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
        return f"rb-{matched.group(1)}"
    return "url-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]


def _absolute_rakuten_url(value: str, *, base_url: str) -> str:
    return urllib.parse.urljoin(base_url, html.unescape(str(value or "").strip()))


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
    for match in anchor_pattern.finditer(html_text):
        title = normalize_space(re.sub(r"<[^>]+>", " ", match.group("title")))
        if not title:
            continue
        source_url = _absolute_rakuten_url(match.group("href"), base_url=page_url)
        context = re.sub(r"<[^>]+>", "\n", html_text[match.start():match.end() + 1800])
        release_date = parse_release_date(context, expected_month=expected_month)
        if release_date is None:
            # A monthly calendar page may omit the year in each card.
            release_date = parse_release_date(context, expected_month=expected_month)
        if release_date is None:
            continue
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


def parse_calendar_html(
    html_text: str,
    *,
    expected_month: str,
    page_url: str,
) -> list[ComicReleaseRecord]:
    records = _json_ld_records(html_text, expected_month=expected_month, page_url=page_url)
    records.extend(_anchor_records(html_text, expected_month=expected_month, page_url=page_url))
    unique: dict[str, ComicReleaseRecord] = {}
    for record in records:
        if record.release_date.strftime("%Y-%m") != expected_month:
            continue
        previous = unique.get(record.source_item_id)
        if previous is None or _record_score(record) > _record_score(previous):
            unique[record.source_item_id] = record
    return sorted(
        (
            record
            for record in unique.values()
            if not _is_non_book_calendar_item(record)
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
        detail_records = selected[:detail_limit]
        with ThreadPoolExecutor(max_workers=min(detail_workers, len(detail_records) or 1)) as executor:
            enriched = list(executor.map(enrich, detail_records))
        selected[:detail_limit] = enriched
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


def _page_links(
    html_text: str,
    *,
    page_url: str,
    expected_month: str,
) -> set[str]:
    links: set[str] = set()
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", html_text, flags=re.IGNORECASE):
        url = _absolute_rakuten_url(href, base_url=page_url)
        if "/calendar/001001/monthly/" not in url:
            continue
        target_dates = urllib.parse.parse_qs(
            urllib.parse.urlsplit(url).query
        ).get("tid", [])
        # The page links to adjacent months too.  Following them turns one
        # monthly collection into a broad crawl, so retain only pagination
        # URLs explicitly bound to the requested month.
        if not target_dates or not target_dates[0].startswith(expected_month):
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
    start_url = source_url.format(month=month)
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
                    if previous is None or _record_score(record) > _record_score(previous):
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
        if old is None or _record_score(record) > _record_score(old):
            result[record.source_item_id] = record
    return sorted(
        (
            record
            for record in result.values()
            if not _is_non_book_calendar_item(record)
        ),
        key=lambda record: (record.release_date, record.source_item_id),
    )


def _is_non_book_calendar_item(record: ComicReleaseRecord) -> bool:
    title = normalize_space(record.title)
    return (
        title.startswith(("【特典】", "[特典]", "特典："))
        or "お風呂ポスター" in title
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
    for item in items:
        title_key = normalize_identity(item.normalized_title or item.title)
        volume = normalize_space(item.volume_label) or None
        if title_key:
            by_title_volume.setdefault((title_key, volume), item)
    changes: list[PlannedChange] = []
    for record in records:
        item = by_identity.get(record.catalog_source_item_id)
        if item is not None:
            fields = _changed_fields(item, record)
            changes.append(PlannedChange(record, "UPDATED" if fields else "UNCHANGED", item.id, fields))
            continue
        cross_source = by_isbn.get(record.isbn) if record.isbn else None
        if cross_source is None:
            cross_source = by_title_volume.get((record.normalized_title, record.volume_label))
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
    selected = [change for change in changes if change.action in {"NEW", "UPDATED"}]
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
        summary = CsvImportService(session).import_file(canonical_csv, dry_run=False, commit=False)
        by_identity = {
            str(item.source_item_id): item
            for item in session.scalars(select(EbookItem).where(EbookItem.source_name == SOURCE_NAME))
        }
        item_ids: list[str] = []
        for change in selected_changes:
            item = by_identity.get(change.record.catalog_source_item_id)
            if item is None:
                raise MonthlyComicReleaseSyncError("import did not produce expected ebook item")
            item.source_discovery = SOURCE_DISCOVERY
            item.source_url = change.record.source_url
            _store_metadata(session, run_id=run_id, change=change, item=item, observed_at=observed_at)
            item_ids.append(item.id)
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


def _kindle_enrich(ebook_item_id: str, *, execute: bool) -> dict[str, Any]:
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
        item = session.get(EbookItem, ebook_item_id)
        if item is None:
            return {"ebook_item_id": ebook_item_id, "status": "ITEM_NOT_FOUND"}
        existing = session.scalar(select(StoreOffer).where(StoreOffer.ebook_item_id == item.id, StoreOffer.store_name == "amazon").limit(1))
        if existing is not None:
            return {"ebook_item_id": item.id, "status": "NOOP_ALREADY_PRESENT", "store_item_id": existing.store_item_id}
        client: AmazonCreatorsApiClient | None = None
        try:
            client = AmazonCreatorsApiClient.from_environment()
            result = AmazonCreatorsKindleResolver(session, client).resolve(
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
        finally:
            if client is not None:
                client.close()


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
) -> dict[str, list[dict[str, Any]]]:
    unique_ids = list(dict.fromkeys(item_ids))
    kobo: list[dict[str, Any]] = []
    kobo_rate_limited = False
    for ebook_item_id in unique_ids[:kobo_limit]:
        if kobo_rate_limited:
            kobo.append(
                {
                    "ebook_item_id": ebook_item_id,
                    "status": "DEFERRED_RATE_LIMIT",
                    "reason_code": "KOBO_OFFICIAL_API_RATE_LIMIT",
                }
            )
            continue
        result = _kobo_enrich(ebook_item_id, execute=execute)
        if result.get("diagnostic_code") == "HTTP_STATUS_ERROR;status=429":
            result["status"] = "DEFERRED_RATE_LIMIT"
            result["reason_code"] = "KOBO_OFFICIAL_API_RATE_LIMIT"
            kobo_rate_limited = True
        kobo.append(result)
    dmm = [_dmm_enrich(item_id, execute=execute) for item_id in unique_ids[:dmm_limit]]
    kindle = [_kindle_enrich(item_id, execute=execute) for item_id in unique_ids[:kindle_limit]]
    cover_candidates = [entry["ebook_item_id"] for entry in kobo if entry.get("status") in {"SAVED", "NOOP_ALREADY_PRESENT"}]
    covers = [_cover_reconcile(item_id, execute=execute) for item_id in cover_candidates[:cover_limit]]
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
) -> dict[str, Any]:
    if phase not in {"plan", "apply", "enrich", "all"}:
        raise MonthlyComicReleaseSyncError("phase must be plan, apply, enrich, or all")
    normalized_month, _, _ = parse_month(month)
    run_id = f"{normalized_month.replace('-', '')}_{uuid.uuid4().hex[:12]}"
    runtime_dir = repository_root / "exchange" / "runtime" / "monthly_comic_release_sync" / normalized_month / run_id
    runtime_dir.mkdir(parents=True, exist_ok=True)
    records = load_records_csv(input_csv, month=normalized_month) if input_csv else collect_rakuten_calendar(
        month=normalized_month,
        source_url=source_url,
        max_pages=max_pages,
        page_workers=page_workers,
        detail_limit=detail_limit,
        detail_workers=detail_workers,
        detail_cache_dir=(repository_root / "exchange" / "runtime" / "monthly_comic_release_sync" / normalized_month / "product_detail_cache"),
        detail_cache_ttl_hours=detail_cache_ttl_hours,
    )
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
        # A scheduled ``all`` run enriches only records it inserted or changed.
        # The explicit ``enrich`` phase is the recoverable resume path after a
        # transient store outage; it intentionally scans the month's items.
        item_ids = imported_item_ids
        if execute and phase == "enrich" and not item_ids:
            item_ids = monthly_sync_item_ids(month=normalized_month)
        payload["enrichment_item_count"] = len(item_ids)
        payload["enrichment"] = enrich_items(item_ids, execute=execute, kobo_limit=kobo_limit, dmm_limit=dmm_limit, kindle_limit=kindle_limit, cover_limit=cover_limit)
        payload["external_store_requests_performed"] = bool(execute and item_ids)
    write_report(runtime_dir / "result.json", payload)
    return payload
