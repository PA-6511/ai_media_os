from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.services.monthly_comic_release_sync import (
    ComicReleaseRecord,
    PlannedChange,
    apply_plan,
    build_sync_plan,
    enrich_rakuten_product_metadata,
    load_records_csv,
    normalize_identity,
    parse_calendar_html,
    parse_month,
    parse_rakuten_product_html,
    SyncPlan,
    write_canonical_csv,
)
from app.services import monthly_comic_release_sync as monthly_sync


def test_parse_month_accepts_leap_year_and_rejects_invalid() -> None:
    month, start, end = parse_month("2028-02")
    assert month == "2028-02"
    assert start == date(2028, 2, 1)
    assert end == date(2028, 3, 1)


def test_normalize_identity_ignores_spacing_case_and_punctuation() -> None:
    assert normalize_identity(" Comic  Title!! 3 ") == "comictitle3"


def test_parse_calendar_json_ld_preserves_source_and_imprint() -> None:
    html = '''<script type="application/ld+json">{"itemListElement":[{"name":"作品名（レーベルコミックス） 3","url":"https://books.rakuten.co.jp/rb/12345678/","datePublished":"2026-09-11","author":{"name":"作者"},"publisher":{"name":"出版社"},"isbn":"978-4-123-45678-9"}]}</script>'''
    records = parse_calendar_html(html, expected_month="2026-09", page_url="https://books.rakuten.co.jp/calendar/001001/monthly/?tid=2026-09-01")
    assert len(records) == 1
    assert records[0].source_item_id == "rb-12345678"
    assert records[0].volume_label == "3"
    assert records[0].author_name == "作者"
    assert records[0].publisher_name == "出版社"
    assert records[0].isbn == "9784123456789"


def test_product_page_enrichment_fills_public_metadata_and_keeps_cover_as_evidence() -> None:
    record = ComicReleaseRecord(
        "rb-12345678",
        "作品名（レーベルコミックス） 3",
        date(2026, 9, 11),
        "https://books.rakuten.co.jp/rb/12345678/",
        series_name="作品名",
        volume_label="3",
    )
    html = '''
        <meta property="books:isbn" content="978-4-123-45678-9" />
        <meta property="og:image" content="https://example.test/cover.jpg" />
        <li class="productInfo"><span class="category">発売日</span><span class="categoryValue">2026年09月12日</span></li>
        <li class="productInfo"><span class="category">著者／編集</span><span class="categoryValue"><a>作者A</a>(著) <a>作者B</a>(原作)</span></li>
        <li class="productInfo"><span class="category">シリーズ</span><span class="categoryValue"><a>公式シリーズ</a></span></li>
        <li class="productInfo"><span class="category">レーベル</span><span class="categoryValue"><a>公式レーベル</a></span></li>
        <li class="productInfo"><span class="category">出版社</span><span class="categoryValue"><a>公式出版社</a></span></li>
    '''
    enriched = parse_rakuten_product_html(html, record=record)
    assert enriched.release_date == date(2026, 9, 12)
    assert enriched.author_name == "作者A|作者B"
    assert enriched.publisher_name == "公式出版社"
    assert enriched.imprint_name == "公式レーベル"
    assert enriched.series_name == "公式シリーズ"
    assert enriched.isbn == "9784123456789"
    assert enriched.raw["cover_candidate_url"] == "https://example.test/cover.jpg"
    assert enriched.raw["cover_candidate_source"] == "RAKUTEN_BOOKS_PRODUCT_PAGE"


def test_product_metadata_cache_reuses_a_fresh_public_page(tmp_path) -> None:
    record = ComicReleaseRecord(
        "rb-12345678",
        "作品名 1",
        date(2026, 9, 1),
        "https://books.rakuten.co.jp/rb/12345678/",
    )
    html = '''<meta property="books:isbn" content="978-4-123-45678-9" />
        <li class="productInfo"><span class="category">出版社</span><span class="categoryValue"><a>出版社</a></span></li>'''
    calls: list[str] = []

    def fetch(url: str) -> str:
        calls.append(url)
        return html

    first = enrich_rakuten_product_metadata([record], cache_dir=tmp_path, fetch=fetch)
    second = enrich_rakuten_product_metadata([record], cache_dir=tmp_path, fetch=fetch)
    assert calls == [record.source_url]
    assert first[0].isbn == second[0].isbn == "9784123456789"
    assert first[0].raw["detail_cache"] == "MISS"
    assert second[0].raw["detail_cache"] == "HIT"


def test_plan_reports_existing_update_and_cross_source_duplicate() -> None:
    changed = ComicReleaseRecord("rb-1", "作品 2", date(2026, 9, 1), "https://books.rakuten.co.jp/rb/1/", volume_label="2", series_name="作品")
    duplicate = ComicReleaseRecord("rb-2", "別作品 1", date(2026, 9, 2), "https://books.rakuten.co.jp/rb/2/", isbn="9784123456789", volume_label="1", series_name="別作品")
    current = SimpleNamespace(id="current", source_name="new_release_multistore", source_item_id="rakuten_books:rb-1", title="作品 1", normalized_title="作品", isbn=None, volume_label="1", author_name=None, publisher_name=None, series_name="作品", release_date=date(2026, 9, 1))
    other = SimpleNamespace(id="other", source_name="supplement", source_item_id="old", title="別作品 1", normalized_title="別作品", isbn="9784123456789", volume_label="1", author_name=None, publisher_name=None, series_name="別作品", release_date=date(2026, 9, 2))
    plan = build_sync_plan([changed, duplicate], month="2026-09", source_url="source", items=[current, other])
    assert plan.changes[0].action == "UPDATED"
    assert "title" in plan.changes[0].changed_fields
    assert plan.changes[1].action == "REVIEW_REQUIRED"
    assert plan.changes[1].reason == "CROSS_SOURCE_DUPLICATE"


def test_plan_does_not_replace_existing_values_with_missing_metadata() -> None:
    record = ComicReleaseRecord(
        "rb-1",
        "作品 1",
        date(2026, 9, 1),
        "https://books.rakuten.co.jp/rb/1/",
    )
    current = SimpleNamespace(
        id="current",
        source_name="new_release_multistore",
        source_item_id="rakuten_books:rb-1",
        title="作品 1",
        normalized_title="作品 1",
        isbn="9784123456789",
        volume_label="1",
        author_name="既存作者",
        publisher_name="既存出版社",
        series_name="既存シリーズ",
        release_date=date(2026, 9, 1),
    )

    plan = build_sync_plan(
        [record], month="2026-09", source_url="source", items=[current]
    )

    assert plan.changes[0].action == "UNCHANGED"
    assert plan.changes[0].changed_fields == ()


def test_canonical_csv_can_be_reused_as_monthly_sync_input(tmp_path) -> None:
    record = ComicReleaseRecord(
        "rb-12345678",
        "作品 1",
        date(2026, 9, 1),
        "https://books.rakuten.co.jp/rb/12345678/",
    )
    path = tmp_path / "canonical.csv"

    assert write_canonical_csv(path, [PlannedChange(record, "NEW", None)]) == 1

    restored = load_records_csv(path, month="2026-09")
    assert len(restored) == 1
    assert restored[0].source_item_id == "rb-12345678"
    assert restored[0].source_url == record.source_url


def test_kobo_rate_limit_defers_remaining_items_without_more_requests(monkeypatch) -> None:
    requested: list[str] = []

    def rate_limited(ebook_item_id: str, *, execute: bool) -> dict[str, str]:
        requested.append(ebook_item_id)
        return {
            "ebook_item_id": ebook_item_id,
            "status": "FAILED",
            "reason_code": "KOBO_OFFICIAL_API_FAILED",
            "diagnostic_code": "HTTP_STATUS_ERROR;status=429",
        }

    monkeypatch.setattr(monthly_sync, "_kobo_enrich", rate_limited)

    result = monthly_sync.enrich_items(
        ["first", "second", "third"],
        execute=True,
        kobo_limit=3,
        dmm_limit=0,
        kindle_limit=0,
        cover_limit=0,
    )

    assert requested == ["first"]
    assert [entry["status"] for entry in result["rakuten_kobo"]] == [
        "DEFERRED_RATE_LIMIT",
        "DEFERRED_RATE_LIMIT",
        "DEFERRED_RATE_LIMIT",
    ]


def test_store_enrichment_order_and_cover_candidate_selection(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        monthly_sync,
        "_kobo_enrich",
        lambda item_id, *, execute: calls.append(f"kobo:{item_id}")
        or {"ebook_item_id": item_id, "status": "SAVED"},
    )
    monkeypatch.setattr(
        monthly_sync,
        "_dmm_enrich",
        lambda item_id, *, execute: calls.append(f"dmm:{item_id}")
        or {"ebook_item_id": item_id, "status": "NOT_FOUND"},
    )
    monkeypatch.setattr(
        monthly_sync,
        "_kindle_enrich",
        lambda item_id, *, execute: calls.append(f"kindle:{item_id}")
        or {"ebook_item_id": item_id, "status": "REVIEW_REQUIRED"},
    )
    monkeypatch.setattr(
        monthly_sync,
        "_cover_reconcile",
        lambda item_id, *, execute: calls.append(f"cover:{item_id}")
        or {"ebook_item_id": item_id, "status": "COVER_FOUND"},
    )

    result = monthly_sync.enrich_items(
        ["first", "second"],
        execute=True,
        kobo_limit=2,
        dmm_limit=2,
        kindle_limit=2,
        cover_limit=2,
    )

    assert calls == [
        "kobo:first",
        "kobo:second",
        "dmm:first",
        "dmm:second",
        "kindle:first",
        "kindle:second",
        "cover:first",
        "cover:second",
    ]
    assert [entry["status"] for entry in result["covers"]] == [
        "COVER_FOUND",
        "COVER_FOUND",
    ]


def test_apply_plan_dry_run_rolls_back_and_reports_no_write(
    tmp_path, monkeypatch
) -> None:
    record = ComicReleaseRecord(
        "rb-1",
        "作品 1",
        date(2026, 9, 1),
        "https://books.rakuten.co.jp/rb/1/",
    )
    change = PlannedChange(record, "NEW", None)
    plan = SyncPlan("2026-09", "source", [record], [change])
    canonical_csv = tmp_path / "canonical.csv"
    write_canonical_csv(canonical_csv, [change])
    state = {"rows": 0, "rollbacks": 0}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def rollback(self):
            state["rows"] = 0
            state["rollbacks"] += 1

    class FakeRepository:
        def __init__(self, _session):
            pass

        def import_row(self, _row):
            state["rows"] += 1
            return SimpleNamespace(
                created=True,
                updated=False,
                unchanged=False,
                offer_created=False,
                offer_updated=False,
                offer_unchanged=False,
            )

    monkeypatch.setattr(monthly_sync, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        "app.services.csv_import_service.ImportRepository", FakeRepository
    )

    result = apply_plan(
        plan=plan,
        canonical_csv=canonical_csv,
        run_id="dry-run",
        execute=False,
        selected_changes=[change],
    )

    assert result["database_write_performed"] is False
    assert state == {"rows": 0, "rollbacks": 1}


def test_first_production_sample_is_limited_to_100_items() -> None:
    records = [
        ComicReleaseRecord(
            f"rb-{index}",
            f"作品 {index}",
            date(2026, 9, 1),
            f"https://books.rakuten.co.jp/rb/{index}/",
        )
        for index in range(101)
    ]
    plan = build_sync_plan(
        records, month="2026-09", source_url="source", items=[]
    )

    selected = plan.actionable[:100]

    assert len(selected) == 100
    assert len({change.record.source_item_id for change in selected}) == 100
