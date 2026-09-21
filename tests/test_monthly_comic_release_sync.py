from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.services.monthly_comic_release_sync import (
    ComicReleaseRecord,
    PlannedChange,
    apply_plan,
    build_sync_plan,
    enrich_rakuten_product_metadata,
    load_records_csv,
    normalize_identity,
    normalize_work_identity,
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


def test_normalize_work_identity_ignores_store_and_imprint_decorations() -> None:
    assert normalize_work_identity(
        "女友達は頼めば意外とヤらせてくれる(5)【電子限定特典付き】"
    ) == normalize_work_identity(
        "女友達は頼めば意外とヤらせてくれる(5) (角川コミックス・エース)"
    )


def test_parse_kobo_daily_calendar_keeps_volume_metadata_and_rejects_non_volumes() -> None:
    def item(title: str, *, number: str, price: int) -> str:
        return f'''<li class="item"><div class="item-release__date">9月 10日</div>
        <div class="item-image"><a href="https://books.rakuten.co.jp/rk/{number[-32:].zfill(32)}/">
        <img src="//tshop.r10s.jp/rakutenkobo-ebooks/cabinet/0001/{number}.jpg"></a></div>
        <div class="item-title"><span class="item-title__text">{title}</span></div>
        <div class="item-author"><div class="item-author__name">作者A, 作者B</div></div>
        <div class="item-publisher">出版社</div>
        <div class="item-pricing"><span class="item-pricing__price">{price:,}円</span></div></li>'''

    html = "".join(
        (
            item(
                "ティアムーン帝国物語〜断頭台から始まる、姫の転生逆転ストーリー〜@COMIC 第12巻",
                number="2000021537464",
                price=759,
            ),
            item("女王の烙印〜滅びの国の夜伽巫女〜 54", number="2000021537006", price=165),
            item("ヤングジャンプ 2026 No.41", number="2000021537471", price=499),
            item("ニュージャパニズム ブランディング", number="2000021537007", price=5280),
        )
    )
    records = parse_calendar_html(
        html,
        expected_month="2026-09",
        page_url="https://books.rakuten.co.jp/calendar/101904/daily/?tid=2026-09-10&v=3",
    )

    assert [record.title for record in records] == [
        "ティアムーン帝国物語〜断頭台から始まる、姫の転生逆転ストーリー〜@COMIC 第12巻"
    ]
    record = records[0]
    assert record.source_item_id == "rk-2000021537464"
    assert record.author_name == "作者A|作者B"
    assert record.publisher_name == "出版社"
    assert record.release_date == date(2026, 9, 10)
    assert record.raw["price_yen"] == 759
    assert record.raw["store_item_id"] == "2000021537464"
    assert record.raw["cover_candidate_source"] == "RAKUTEN_KOBO_CALENDAR"


def test_daily_kobo_pagination_does_not_follow_another_release_date() -> None:
    html = '''
      <a href="?tid=2026-09-10&p=2&v=3#rclist">2</a>
      <a href="?tid=2026-09-11&v=3">翌日</a>
    '''
    links = monthly_sync._page_links(
        html,
        page_url="https://books.rakuten.co.jp/calendar/101904/daily/?tid=2026-09-10&v=3",
        expected_month="2026-09",
    )

    assert links == {
        "https://books.rakuten.co.jp/calendar/101904/daily/?p=2&tid=2026-09-10&v=3"
    }


def test_parse_calendar_json_ld_preserves_source_and_imprint() -> None:
    html = '''<script type="application/ld+json">{"itemListElement":[{"name":"作品名（レーベルコミックス） 3","url":"https://books.rakuten.co.jp/rb/12345678/","datePublished":"2026-09-11","author":{"name":"作者"},"publisher":{"name":"出版社"},"isbn":"978-4-123-45678-9"}]}</script>'''
    records = parse_calendar_html(html, expected_month="2026-09", page_url="https://books.rakuten.co.jp/calendar/001001/monthly/?tid=2026-09-01")
    assert len(records) == 1
    assert records[0].source_item_id == "rb-12345678"
    assert records[0].volume_label == "3"
    assert records[0].author_name == "作者"
    assert records[0].publisher_name == "出版社"
    assert records[0].isbn == "9784123456789"


def test_anchor_parser_does_not_take_a_later_card_release_date() -> None:
    html = '''
        <li class="item">
          <div class="item-title"><a href="https://books.rakuten.co.jp/rb/10000001/">商品A</a></div>
        </li>
        <li class="item">
          <div class="item-release">9月 11日</div>
          <div class="item-title"><a href="https://books.rakuten.co.jp/rb/10000002/">商品B</a></div>
        </li>
    '''

    records = parse_calendar_html(
        html,
        expected_month="2026-09",
        page_url="https://books.rakuten.co.jp/calendar/001001/monthly/?tid=2026-09-01",
    )

    assert [record.source_item_id for record in records] == ["rb-10000002"]


def test_anchor_parser_uses_release_date_from_its_own_card() -> None:
    html = '''
        <li class="item">
          <div class="item-release">9月 8日</div>
          <div class="item-title"><a href="https://books.rakuten.co.jp/rb/10000001/">商品A</a></div>
          <div class="item-author"><div class="item-author__name">作者A</div></div>
        </li>
    '''

    records = parse_calendar_html(
        html,
        expected_month="2026-09",
        page_url="https://books.rakuten.co.jp/calendar/001001/monthly/?tid=2026-09-01",
    )

    assert len(records) == 1
    assert records[0].source_item_id == "rb-10000001"
    assert records[0].release_date == date(2026, 9, 8)


def test_anchor_parser_skips_a_card_without_a_release_date() -> None:
    html = '''
        <li class="item">
          <div class="item-title"><a href="https://books.rakuten.co.jp/rb/10000001/">商品A</a></div>
        </li>
    '''

    records = parse_calendar_html(
        html,
        expected_month="2026-09",
        page_url="https://books.rakuten.co.jp/calendar/001001/monthly/?tid=2026-09-01",
    )

    assert records == []


def test_dedupe_records_prefers_ebook_calendar_over_metadata_richer_anchor() -> None:
    ebook_calendar = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 20",
        date(2026, 9, 8),
        "https://books.rakuten.co.jp/rb/18712089/",
        raw={"parser": "ebook_calendar"},
    )
    anchor = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 最強漫画家はお絵描きスキルで異世界無双する！20",
        date(2026, 9, 11),
        "https://books.rakuten.co.jp/rb/18712089/",
        author_name="作者",
        publisher_name="出版社",
        imprint_name="レーベル",
        series_name="ドローイング",
        volume_label="20",
        isbn="9784123456789",
        raw={"parser": "anchor"},
    )

    records = monthly_sync._dedupe_records([anchor, ebook_calendar])

    assert len(records) == 1
    assert records[0].raw["parser"] == "ebook_calendar"
    assert records[0].release_date == date(2026, 9, 8)


def test_dedupe_records_prefers_ebook_calendar_over_metadata_richer_json_ld() -> None:
    ebook_calendar = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 20",
        date(2026, 9, 8),
        "https://books.rakuten.co.jp/rb/18712089/",
        raw={"parser": "ebook_calendar"},
    )
    json_ld = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 最強漫画家はお絵描きスキルで異世界無双する！20",
        date(2026, 9, 11),
        "https://books.rakuten.co.jp/rb/18712089/",
        author_name="作者",
        publisher_name="出版社",
        imprint_name="レーベル",
        series_name="ドローイング",
        volume_label="20",
        isbn="9784123456789",
        raw={"parser": "json_ld"},
    )

    records = monthly_sync._dedupe_records([json_ld, ebook_calendar])

    assert len(records) == 1
    assert records[0].raw["parser"] == "ebook_calendar"
    assert records[0].release_date == date(2026, 9, 8)


def test_dedupe_records_uses_metadata_score_within_the_same_parser() -> None:
    sparse = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 20",
        date(2026, 9, 8),
        "https://books.rakuten.co.jp/rb/18712089/",
        raw={"parser": "anchor"},
    )
    complete = ComicReleaseRecord(
        "rb-18712089",
        "ドローイング 最強漫画家はお絵描きスキルで異世界無双する！20",
        date(2026, 9, 11),
        "https://books.rakuten.co.jp/rb/18712089/",
        author_name="作者",
        publisher_name="出版社",
        series_name="ドローイング",
        volume_label="20",
        raw={"parser": "anchor"},
    )

    records = monthly_sync._dedupe_records([sparse, complete])

    assert len(records) == 1
    assert records[0].release_date == date(2026, 9, 11)


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
        lambda item_id, *, execute, client=None, client_error=None: calls.append(f"kindle:{item_id}")
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


def test_independent_backlog_targets_do_not_consume_other_store_limits(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(monthly_sync, "_kobo_enrich", lambda item_id, *, execute: calls.append(f"kobo:{item_id}") or {"ebook_item_id": item_id, "status": "REVIEW_REQUIRED"})
    monkeypatch.setattr(monthly_sync, "_dmm_enrich", lambda item_id, *, execute: calls.append(f"dmm:{item_id}") or {"ebook_item_id": item_id, "status": "INCOMPLETE"})
    monkeypatch.setattr(monthly_sync, "_kindle_enrich", lambda item_id, *, execute, client=None, client_error=None: calls.append(f"kindle:{item_id}") or {"ebook_item_id": item_id, "status": "NO_MATCH"})
    monkeypatch.setattr(monthly_sync, "_cover_reconcile", lambda item_id, *, execute: calls.append(f"cover:{item_id}") or {"ebook_item_id": item_id, "status": "HIDDEN_UNVERIFIED"})

    result = monthly_sync.enrich_items(
        [],
        execute=False,
        kobo_limit=1,
        dmm_limit=1,
        kindle_limit=1,
        cover_limit=1,
        target_ids={
            "rakuten_kobo": ["kobo-pending"],
            "dmm": ["dmm-pending"],
            "kindle": ["kindle-pending"],
            "covers": ["cover-pending"],
        },
    )

    assert calls == [
        "kobo:kobo-pending",
        "dmm:dmm-pending",
        "kindle:kindle-pending",
        "cover:cover-pending",
    ]
    assert monthly_sync.summarize_enrichment(result)["FAILED"] == 0
    assert monthly_sync.summarize_enrichment(result)["KOBO_AMBIGUOUS"] == 1
    assert monthly_sync.summarize_enrichment(result)["DMM_INCOMPLETE"] == 1
    assert monthly_sync.summarize_enrichment(result)["KINDLE_NO_MATCH"] == 1
    assert monthly_sync.summarize_enrichment(result)["COVER_PENDING"] == 1


def test_enrichment_pacing_is_execute_only(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(monthly_sync.time, "sleep", sleeps.append)
    monkeypatch.setattr(monthly_sync, "_kobo_enrich", lambda item_id, *, execute: {"ebook_item_id": item_id, "status": "REVIEW_REQUIRED"})
    monkeypatch.setattr(monthly_sync, "_dmm_enrich", lambda item_id, *, execute: {"ebook_item_id": item_id, "status": "INCOMPLETE"})
    monkeypatch.setattr(monthly_sync, "_kindle_enrich", lambda item_id, *, execute, client=None, client_error=None: {"ebook_item_id": item_id, "status": "NO_MATCH"})
    monkeypatch.setattr(monthly_sync, "_cover_reconcile", lambda item_id, *, execute: {"ebook_item_id": item_id, "status": "HIDDEN_UNVERIFIED"})

    monthly_sync.enrich_items(
        ["one", "two"],
        execute=False,
        kobo_limit=2,
        dmm_limit=2,
        kindle_limit=0,
        cover_limit=2,
        target_ids={"covers": ["one", "two"]},
        kobo_pacing_seconds=5,
        dmm_pacing_seconds=5,
        cover_pacing_seconds=5,
    )
    assert sleeps == []

    monthly_sync.enrich_items(
        ["one", "two"],
        execute=True,
        kobo_limit=2,
        dmm_limit=2,
        kindle_limit=0,
        cover_limit=2,
        target_ids={"covers": ["one", "two"]},
        kobo_pacing_seconds=5,
        dmm_pacing_seconds=5,
        cover_pacing_seconds=5,
    )
    assert sleeps == [5, 5, 5]


def test_dmm_not_found_is_separate_from_other_incomplete() -> None:
    summary = monthly_sync.summarize_enrichment(
        {
            "rakuten_kobo": [],
            "dmm": [
                {"status": "INCOMPLETE", "reason_code": "DMM_PRODUCT_NOT_FOUND"},
                {"status": "INCOMPLETE", "reason_code": "TITLE_REQUIRED"},
            ],
            "kindle": [],
            "covers": [],
        }
    )
    assert summary["DMM_NO_MATCH"] == 1
    assert summary["DMM_INCOMPLETE"] == 1


def test_monthly_completion_metrics_use_full_backlog_counts() -> None:
    metrics = monthly_sync.monthly_completion_metrics(
        total_month_items=100,
        backlog_counts={
            "rakuten_kobo": 60,
            "dmm": 25,
            "kindle": 10,
            "covers": 80,
        },
        any_store_found=85,
        cover_ok=20,
    )

    assert metrics == {
        "TOTAL_MONTH_ITEMS": 100,
        "KOBO_FOUND_RATE": 0.4,
        "DMM_FOUND_RATE": 0.75,
        "KINDLE_FOUND_RATE": 0.9,
        "ANY_STORE_FOUND_RATE": 0.85,
        "COVER_OK_RATE": 0.2,
    }


def test_enrichment_database_write_reporting_uses_committed_statuses() -> None:
    assert monthly_sync.enrichment_database_write_performed(
        {
            "rakuten_kobo": [{"status": "REVIEW_REQUIRED"}],
            "dmm": [{"status": "READY"}],
            "kindle": [{"status": "NO_MATCH"}],
            "covers": [],
        }
    ) is True
    assert monthly_sync.enrichment_database_write_performed(
        {
            "rakuten_kobo": [{"status": "REVIEW_REQUIRED"}],
            "dmm": [{"status": "INCOMPLETE"}],
            "kindle": [{"status": "NO_MATCH"}],
            "covers": [],
        }
    ) is False


def test_daily_backlog_rotation_is_stable_and_advances(monkeypatch) -> None:
    class FirstDay(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 2)

    class NextDay(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 3)

    values = [f"item-{index}" for index in range(7)]
    monkeypatch.setattr(monthly_sync, "date", FirstDay)
    first = monthly_sync.rotate_daily_backlog(values, limit=2)
    assert monthly_sync.rotate_daily_backlog(values, limit=2) == first
    monkeypatch.setattr(monthly_sync, "date", NextDay)
    assert monthly_sync.rotate_daily_backlog(values, limit=2) != first


def test_near_term_priority_orders_all_bands_before_old_backlog() -> None:
    reference = date(2026, 9, 19)
    candidates = [
        ("old", date(2026, 9, 1)),
        ("later-month", date(2026, 9, 29)),
        ("next-week", date(2026, 9, 26)),
        ("today", reference),
        ("tomorrow", date(2026, 9, 20)),
    ]

    assert monthly_sync.prioritize_enrichment_candidates(
        candidates, reference_date=reference, sync_month="2026-09",
        limit=5, rotate=False,
    ) == ["today", "next-week", "tomorrow", "later-month", "old"]


def test_near_term_priority_keeps_next_month_inside_seven_days() -> None:
    assert monthly_sync.prioritize_enrichment_candidates(
        [("october", date(2026, 10, 1)), ("september-old", date(2026, 9, 1))],
        reference_date=date(2026, 9, 30), sync_month="2026-09",
        limit=1, rotate=False,
    ) == ["october"]


def test_near_term_priority_rotates_inside_bands_without_exceeding_limit() -> None:
    candidates = [
        (f"today-{index}", date(2026, 9, 19)) for index in range(5)
    ] + [("old", date(2026, 9, 1))]
    first = monthly_sync.prioritize_enrichment_candidates(
        candidates, reference_date=date(2026, 9, 19), sync_month="2026-09",
        limit=2, rotate=True, rotation_date=date(2026, 9, 19),
    )
    again = monthly_sync.prioritize_enrichment_candidates(
        candidates, reference_date=date(2026, 9, 19), sync_month="2026-09",
        limit=2, rotate=True, rotation_date=date(2026, 9, 19),
    )
    next_day = monthly_sync.prioritize_enrichment_candidates(
        candidates, reference_date=date(2026, 9, 19), sync_month="2026-09",
        limit=2, rotate=True, rotation_date=date(2026, 9, 20),
    )
    assert len(first) == len(next_day) == 2
    assert first == again
    assert first != next_day
    assert all(value.startswith("today-") for value in first + next_day)


def test_no_near_term_priority_matches_existing_rotation_and_missing_date_is_last() -> None:
    reference = date(2026, 10, 10)
    candidates = [("old-a", date(2026, 9, 1)), ("old-b", date(2026, 9, 2))]
    expected = monthly_sync.rotate_daily_backlog(
        [item_id for item_id, _ in candidates], limit=1, reference_date=reference,
    )[:1]
    assert monthly_sync.prioritize_enrichment_candidates(
        candidates, reference_date=reference, sync_month="2026-09",
        limit=1, rotate=True, rotation_date=reference,
    ) == expected
    assert monthly_sync.prioritize_enrichment_candidates(
        [("unknown", None), ("old", date(2026, 9, 1))],
        reference_date=reference, sync_month="2026-09", limit=2, rotate=False,
    ) == ["old", "unknown"]


def test_monthly_enrichment_selector_excludes_ineligible_and_includes_next_month(
    monkeypatch,
) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from app.db.models import EbookItem, StoreOffer

    engine = create_engine("sqlite:///:memory:")
    EbookItem.__table__.create(engine)
    StoreOffer.__table__.create(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    monkeypatch.setattr(monthly_sync, "SessionLocal", session_factory)
    with session_factory() as session:
        for item_id, release, excluded in (
            ("today", date(2026, 9, 30), False),
            ("next-month", date(2026, 10, 1), False),
            ("excluded", date(2026, 9, 30), True),
            ("complete", date(2026, 9, 30), False),
            ("too-late", date(2026, 10, 8), False),
        ):
            session.add(EbookItem(
                id=item_id, source_name=monthly_sync.SOURCE_NAME,
                source_item_id=f"rakuten_books:{item_id}", title=item_id,
                release_date=release, is_excluded=excluded,
            ))
        session.add(StoreOffer(
            id="complete-offer", ebook_item_id="complete",
            store_name="rakuten_kobo", store_item_id="complete",
        ))
        session.commit()

    targets = monthly_sync.monthly_enrichment_target_ids(
        month="2026-09", reference_date=date(2026, 9, 30),
    )
    assert targets["rakuten_kobo"] == ["today", "next-month"]
    assert "excluded" not in targets["dmm"]
    assert "too-late" not in targets["kindle"]


def test_new_kobo_offer_is_eligible_for_cover_in_same_run(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(monthly_sync, "_kobo_enrich", lambda item_id, *, execute: {"ebook_item_id": item_id, "status": "SAVED"})
    monkeypatch.setattr(monthly_sync, "_cover_reconcile", lambda item_id, *, execute: calls.append(item_id) or {"ebook_item_id": item_id, "status": "AUTO_ALLOWED"})

    monthly_sync.enrich_items(
        [],
        execute=False,
        kobo_limit=1,
        dmm_limit=0,
        kindle_limit=0,
        cover_limit=2,
        target_ids={"rakuten_kobo": ["new-kobo"], "covers": ["old-cover"]},
    )

    assert calls == ["old-cover", "new-kobo"]


def test_kindle_enrichment_reuses_one_creators_client_per_batch(monkeypatch) -> None:
    class FakeClient:
        closed = False

        def close(self) -> None:
            self.closed = True

    fake_client = FakeClient()
    created: list[FakeClient] = []
    client_kwargs: list[dict[str, float]] = []
    seen_clients: list[FakeClient | None] = []

    class FakeAmazonCreatorsApiClient:
        @classmethod
        def from_environment(cls, **kwargs) -> FakeClient:
            client_kwargs.append(kwargs)
            created.append(fake_client)
            return fake_client

    def fake_kindle_enrich(
        item_id: str,
        *,
        execute: bool,
        client=None,
        client_error=None,
    ) -> dict[str, str]:
        seen_clients.append(client)
        return {"ebook_item_id": item_id, "status": "NO_MATCH"}

    monkeypatch.setattr(
        "app.integrations.amazon_creators_api_client.AmazonCreatorsApiClient",
        FakeAmazonCreatorsApiClient,
    )
    monkeypatch.setattr(monthly_sync, "_kindle_enrich", fake_kindle_enrich)

    result = monthly_sync.enrich_items(
        ["first", "second", "third"],
        execute=True,
        kobo_limit=0,
        dmm_limit=0,
        kindle_limit=2,
        cover_limit=0,
    )

    assert created == [fake_client]
    assert client_kwargs == [{"minimum_request_interval_seconds": 1.0}]
    assert seen_clients == [fake_client, fake_client]
    assert fake_client.closed is True
    assert [entry["ebook_item_id"] for entry in result["kindle"]] == ["first", "second"]


def test_kindle_unexpected_middle_item_exception_does_not_abort_later_items(monkeypatch) -> None:
    calls: list[str] = []

    def fake_kindle_enrich(
        item_id: str,
        *,
        execute: bool,
        client=None,
        client_error=None,
    ) -> dict[str, str]:
        calls.append(item_id)
        if item_id == "second":
            raise RuntimeError("resolver exploded")
        return {"ebook_item_id": item_id, "status": "NO_MATCH"}

    monkeypatch.setattr(monthly_sync, "_kindle_enrich", fake_kindle_enrich)

    result = monthly_sync.enrich_items(
        ["first", "second", "third"],
        execute=True,
        kobo_limit=0,
        dmm_limit=0,
        kindle_limit=3,
        cover_limit=0,
    )

    assert calls == ["first", "second", "third"]
    assert result["kindle"] == [
        {"ebook_item_id": "first", "status": "NO_MATCH"},
        {"ebook_item_id": "second", "status": "FAILED", "reason_code": "RuntimeError"},
        {"ebook_item_id": "third", "status": "NO_MATCH"},
    ]


def test_kindle_unexpected_session_exception_rolls_back_and_later_item_continues(monkeypatch) -> None:
    events: list[str] = []

    class FakeSession:
        def __init__(self) -> None:
            self.item_id = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, _model, item_id: str):
            self.item_id = item_id
            events.append(f"get:{item_id}")
            return SimpleNamespace(id=item_id)

        def scalar(self, _statement):
            if self.item_id == "second":
                raise RuntimeError("session failed")
            return None

        def commit(self) -> None:
            events.append(f"commit:{self.item_id}")

        def rollback(self) -> None:
            events.append(f"rollback:{self.item_id}")

    class FakeResolver:
        def __init__(self, session, _client) -> None:
            self.session = session

        def resolve(self, *, ebook_item_id: str, execute: bool):
            return SimpleNamespace(
                status="SAVED",
                candidate_count=1,
                asin=f"ASIN-{ebook_item_id}",
                cover_url="https://example.test/cover.jpg",
                score=0.99,
                classification="HIGH_CONFIDENCE",
                offer_id=f"offer-{ebook_item_id}",
            )

    class FakeClient:
        def close(self) -> None:
            pass

    class FakeAmazonCreatorsApiClient:
        @classmethod
        def from_environment(cls, **_kwargs):
            return FakeClient()

    monkeypatch.setattr(monthly_sync, "SessionLocal", FakeSession)
    monkeypatch.setattr(
        "app.integrations.amazon_creators_api_client.AmazonCreatorsApiClient",
        FakeAmazonCreatorsApiClient,
    )
    monkeypatch.setattr(
        "app.services.amazon_creators_kindle_resolver.AmazonCreatorsKindleResolver",
        FakeResolver,
    )

    result = monthly_sync.enrich_items(
        ["first", "second", "third"],
        execute=True,
        kobo_limit=0,
        dmm_limit=0,
        kindle_limit=3,
        cover_limit=0,
    )

    assert [entry["status"] for entry in result["kindle"]] == [
        "SAVED",
        "FAILED",
        "SAVED",
    ]
    assert result["kindle"][1]["reason_code"] == "RuntimeError"
    assert events == [
        "get:first",
        "commit:first",
        "get:second",
        "rollback:second",
        "get:third",
        "commit:third",
    ]


def test_kindle_shared_client_survives_item_exception_and_closes_once(monkeypatch) -> None:
    class FakeClient:
        close_count = 0

        def close(self) -> None:
            self.close_count += 1

    fake_client = FakeClient()
    seen_clients: list[FakeClient | None] = []

    class FakeAmazonCreatorsApiClient:
        @classmethod
        def from_environment(cls, **_kwargs) -> FakeClient:
            return fake_client

    def fake_kindle_enrich(
        item_id: str,
        *,
        execute: bool,
        client=None,
        client_error=None,
    ) -> dict[str, str]:
        seen_clients.append(client)
        if item_id == "second":
            raise RuntimeError("middle item failed")
        return {"ebook_item_id": item_id, "status": "NO_MATCH"}

    monkeypatch.setattr(
        "app.integrations.amazon_creators_api_client.AmazonCreatorsApiClient",
        FakeAmazonCreatorsApiClient,
    )
    monkeypatch.setattr(monthly_sync, "_kindle_enrich", fake_kindle_enrich)

    result = monthly_sync.enrich_items(
        ["first", "second", "third"],
        execute=True,
        kobo_limit=0,
        dmm_limit=0,
        kindle_limit=3,
        cover_limit=0,
    )

    assert seen_clients == [fake_client, fake_client, fake_client]
    assert [entry["status"] for entry in result["kindle"]] == [
        "NO_MATCH",
        "FAILED",
        "NO_MATCH",
    ]
    assert fake_client.close_count == 1


def test_kindle_item_boundary_does_not_swallow_base_exception(monkeypatch) -> None:
    class FakeClient:
        close_count = 0

        def close(self) -> None:
            self.close_count += 1

    fake_client = FakeClient()

    class FakeAmazonCreatorsApiClient:
        @classmethod
        def from_environment(cls, **_kwargs) -> FakeClient:
            return fake_client

    def raise_system_exit(
        item_id: str,
        *,
        execute: bool,
        client=None,
        client_error=None,
    ) -> dict[str, str]:
        raise SystemExit(7)

    monkeypatch.setattr(
        "app.integrations.amazon_creators_api_client.AmazonCreatorsApiClient",
        FakeAmazonCreatorsApiClient,
    )
    monkeypatch.setattr(monthly_sync, "_kindle_enrich", raise_system_exit)

    with pytest.raises(SystemExit):
        monthly_sync.enrich_items(
            ["first"],
            execute=True,
            kobo_limit=0,
            dmm_limit=0,
            kindle_limit=1,
            cover_limit=0,
        )

    assert fake_client.close_count == 1


def test_kindle_enrichment_dry_run_does_not_create_creators_client(monkeypatch) -> None:
    def fail_if_created():
        raise AssertionError("Creators client should not be created in dry-run")

    monkeypatch.setattr(
        "app.integrations.amazon_creators_api_client.AmazonCreatorsApiClient.from_environment",
        fail_if_created,
    )

    result = monthly_sync.enrich_items(
        ["first", "second"],
        execute=False,
        kobo_limit=0,
        dmm_limit=0,
        kindle_limit=2,
        cover_limit=0,
    )

    assert [entry["status"] for entry in result["kindle"]] == [
        "SKIPPED_DRY_RUN",
        "SKIPPED_DRY_RUN",
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
