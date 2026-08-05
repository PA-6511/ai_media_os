from __future__ import annotations

import html
import re
from datetime import datetime
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import OperationalError

from app.gui.ebook_database_web import (
    DatabaseSearchPageState,
    parse_database_search_query,
    render_affiliate_readiness,
    render_database_search_page,
)
from app.services.catalog_edit_service import normalize_authors
from app.services.daily_summary_query_service import DailySummarySnapshot


@pytest.fixture(autouse=True)
def isolate_render_tests_from_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rendering tests must never obtain their fixtures from production."""

    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_dashboard_summary",
        lambda: {
            "cards": {
                "today_release": 0,
                "tomorrow_release": 0,
                "this_week_release": 0,
                "this_month_release": 0,
                "missing_price": 0,
                "missing_affiliate": 0,
                "excluded": 0,
            },
            "dates": {
                "today": "2026-07-23",
                "tomorrow": "2026-07-24",
                "week_end": "2026-07-26",
                "month_start": "2026-07-01",
                "month_end": "2026-07-31",
            },
            "database": {
                "total_items": 0,
                "store_count": 0,
                "latest_import_at": None,
            },
        },
    )
    monkeypatch.setattr(web, "search_database_rows", lambda _state: [])
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 0)
    monkeypatch.setattr(
        web,
        "load_pending_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_approved_review_ready_approvals",
        lambda _ids: {},
    )
    monkeypatch.setattr(
        web,
        "load_wordpress_draft_execution_states",
        lambda _ids: {},
    )


def test_parse_database_search_query() -> None:
    state = parse_database_search_query(
        "keyword=%E3%82%B5%E3%83%B3%E3%83%97%E3%83%AB"
        "&release_date_from=2026-07-17"
        "&item_type=tankobon"
        "&store_name=rakuten_kobo"
        "&include_excluded=true"
    )

    assert state.keyword == "サンプル"
    assert state.release_date_from == "2026-07-17"
    assert state.item_type == "tankobon"
    assert state.store_name == "rakuten_kobo"
    assert state.include_excluded is True


def test_database_search_state_defaults() -> None:
    state = parse_database_search_query("")

    assert state == DatabaseSearchPageState(
        summary_date=datetime.now(ZoneInfo("Asia/Tokyo")).date().isoformat()
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("横山 アー", "横山アー"),
        ("横山　アー", "横山アー"),
        ("作者 A | 作者　B", "作者A|作者B"),
        ("作者A|作者B", "作者A|作者B"),
        ("", None),
    ],
)
def test_normalize_authors_for_catalog_edit(
    value: str, expected: str | None
) -> None:
    assert normalize_authors(value) == expected


@pytest.mark.parametrize("raw_page", [None, "not-a-number", "0", "-3"])
def test_database_search_page_defaults_invalid_values_to_one(raw_page) -> None:
    raw_query = "" if raw_page is None else f"page={raw_page}"

    assert parse_database_search_query(raw_query).page == 1


def test_database_search_page_accepts_positive_integer() -> None:
    assert parse_database_search_query("page=8").page == 8


def test_render_database_search_page_contains_navigation() -> None:
    page = render_database_search_page("keyword=サンプル")

    assert "電子書籍データベース検索" in page
    assert 'href="/"' in page
    assert 'href="/database-search"' in page
    assert "検索文字" in page
    assert "検索結果:" in page


def test_daily_summary_zero_state_is_rendered_without_migration_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_daily_summary_snapshot",
        lambda _value: DailySummarySnapshot(
            summary_date=datetime(2026, 8, 3).date(),
            items=(),
            target_count=0,
            selected_count=0,
            published_count=0,
            unpublished_count=0,
            three_store_complete_count=0,
            link_missing_count=0,
            inconsistent_count=0,
            error_count=0,
        ),
    )

    page = web.render_database_search_page(
        "summary_date=2026-08-03&release_date_from=2026-08-03"
    )

    assert "対象件数</span><strong>0件" in page
    assert "掲載選択</span><strong>0件" in page
    assert "migration適用状態" not in page
    assert "summary_date=2026-08-03" in page
    assert "release_date_from=2026-08-03" in page


def test_daily_summary_context_failure_is_logged_and_classified(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_daily_summary_snapshot",
        lambda _value: (_ for _ in ()).throw(RuntimeError("query failed")),
    )

    with caplog.at_level("ERROR"):
        page = web.render_database_search_page("summary_date=2026-08-03")

    assert "error_code=DAILY_SUMMARY_CONTEXT_FAILED" in page
    assert "migration適用状態" not in page
    assert "Daily summary context load failed" in caplog.text


def test_daily_summary_table_missing_shows_migration_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    error = OperationalError(
        "SELECT * FROM daily_summary_selections",
        {},
        Exception("no such table: daily_summary_selections"),
    )
    monkeypatch.setattr(
        web,
        "load_daily_summary_snapshot",
        lambda _value: (_ for _ in ()).throw(error),
    )

    page = web.render_database_search_page("summary_date=2026-08-03")

    assert "migration適用状態を確認してください" in page


def test_daily_summary_invalid_date_has_specific_error_code() -> None:
    import app.gui.ebook_database_web as web

    page = web.render_database_search_page("summary_date=invalid-date")

    assert "error_code=DAILY_SUMMARY_INVALID_DATE" in page
    assert "migration適用状態" not in page


def test_daily_summary_query_error_has_specific_error_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    error = OperationalError(
        "SELECT * FROM daily_summary_selections",
        {},
        Exception("database is locked"),
    )
    monkeypatch.setattr(
        web,
        "load_daily_summary_snapshot",
        lambda _value: (_ for _ in ()).throw(error),
    )

    page = web.render_database_search_page("summary_date=2026-08-03")

    assert "error_code=DAILY_SUMMARY_QUERY_FAILED" in page
    assert "migration適用状態" not in page


def test_search_item_type_contains_classification_modes() -> None:
    page = render_database_search_page("item_type=single_or_split")

    assert '<option value="normal" >通常版</option>' in page
    assert '<option value="single_episode" >単話</option>' in page
    assert '<option value="split_edition" >分冊版</option>' in page
    assert (
        '<option value="single_or_split" selected>'
        "単話または分冊版</option>"
    ) in page
    assert '<option value="unclassified" >未分類</option>' in page


def test_render_database_search_page_escapes_input() -> None:
    page = render_database_search_page(
        "keyword=%3Cscript%3Ealert%281%29%3C%2Fscript%3E"
    )

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_render_database_search_page_keeps_zero_counts() -> None:
    page = render_database_search_page("")
    pagination = page.split('<p class="pagination">', 1)[1].split("</p>", 1)[0]

    assert "0件" in page
    assert pagination == '<strong aria-current="page">1</strong>'
    assert "前へ" not in page
    assert "次へ" not in page


def test_pagination_keeps_all_filters_and_search_form_resets_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1489)
    raw_query = (
        "keyword=%E6%96%B0%E5%88%8A&release_date_from=2026-07-01"
        "&release_date_to=2026-07-31&item_type=tankobon"
        "&store_name=rakuten_kobo&include_excluded=true"
        "&excluded_only=true&missing_price=true"
        "&missing_affiliate=true&page=1"
    )

    page = render_database_search_page(raw_query)
    match = re.search(r'href="([^"]+)">2</a>', page)
    assert match is not None
    query = parse_qs(
        urlsplit(html.unescape(match.group(1))).query,
        keep_blank_values=True,
    )
    assert query == {
        "keyword": ["新刊"],
        "release_date_from": ["2026-07-01"],
        "release_date_to": ["2026-07-31"],
        "item_type": ["tankobon"],
        "store_name": ["rakuten_kobo"],
        "include_excluded": ["true"],
        "excluded_only": ["true"],
        "missing_price": ["true"],
        "affiliate_status": ["all_unregistered"],
        "page": ["2"],
    }
    search_form = page.split(
        '<form method="get" action="/database-search">', 1
    )[1].split("</form>", 1)[0]
    assert 'name="page"' not in search_form


def test_numeric_page_links_and_current_page_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1489)

    first_page = render_database_search_page("page=1")
    second_page = render_database_search_page("page=2")
    first_pagination = first_page.split(
        '<p class="pagination">', 1
    )[1].split("</p>", 1)[0]
    second_pagination = second_page.split(
        '<p class="pagination">', 1
    )[1].split("</p>", 1)[0]

    assert "検索結果: 全1489件" in first_page
    assert "表示中: 1〜200件" in first_page
    assert '<strong aria-current="page">1</strong>' in first_pagination
    assert ">1</a>" not in first_pagination
    assert '<strong aria-current="page">2</strong>' in second_pagination
    assert ">2</a>" not in second_pagination
    assert "前へ" not in first_page
    assert "次へ" not in first_page
    assert "1 / 8" not in first_page

    first_links = re.findall(r'href="([^"]+)">(\d+)</a>', first_pagination)
    second_links = re.findall(r'href="([^"]+)">(\d+)</a>', second_pagination)
    assert [number for _href, number in first_links] == [
        str(number) for number in range(2, 9)
    ]
    assert [number for _href, number in second_links] == [
        "1", "3", "4", "5", "6", "7", "8"
    ]
    for href, number in first_links + second_links:
        query = parse_qs(urlsplit(html.unescape(href)).query)
        assert query["page"] == [number]


def test_page_above_total_pages_is_clamped_before_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.gui.ebook_database_web as web

    searched_pages: list[int] = []
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1489)
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda state: searched_pages.append(state.page) or [],
    )

    page = render_database_search_page("page=999")

    assert searched_pages == [8]
    assert "表示中: 1401〜1489件" in page


def test_render_status_badges() -> None:
    from app.gui.ebook_database_web import (
        render_ready_badge,
        render_status_badge,
    )

    assert "新規" in render_status_badge("NEW")
    assert "未作成" in render_status_badge("NOT_CREATED")
    assert "公開可能" in render_ready_badge(True)
    assert "未準備" in render_ready_badge(False)


@pytest.mark.parametrize(
    ("ready_fields", "expected_count"),
    [
        ({"amazon_affiliate_ready": True}, "1/3"),
        ({"rakuten_kobo_affiliate_ready": True}, "1/3"),
        ({"dmm_affiliate_ready": True}, "1/3"),
        (
            {
                "amazon_affiliate_ready": True,
                "rakuten_kobo_affiliate_ready": True,
                "dmm_affiliate_ready": True,
            },
            "3/3",
        ),
        ({}, "0/3"),
    ],
)
def test_render_affiliate_readiness_badges(
    ready_fields: dict[str, bool], expected_count: str
) -> None:
    rendered = render_affiliate_readiness(ready_fields)

    assert ">K</span>" in rendered
    assert ">R</span>" in rendered
    assert ">D</span>" in rendered
    assert expected_count in rendered
    assert rendered.count("title=") == 4
    assert rendered.count("aria-label=") == 4


def test_affiliate_readiness_labels_expose_each_registration_state() -> None:
    rendered = render_affiliate_readiness(
        {
            "amazon_affiliate_ready": True,
            "rakuten_kobo_affiliate_ready": False,
            "dmm_affiliate_ready": True,
        }
    )

    assert "Amazon: 登録済み" in rendered
    assert "楽天Kobo: 未登録" in rendered
    assert "DMM: 登録済み" in rendered
    assert "2/3" in rendered
    assert "affiliate-service-amazon is-ready" in rendered
    assert "affiliate-service-rakuten-kobo is-missing" in rendered
    assert "affiliate-service-dmm is-ready" in rendered


def test_affiliate_readiness_renderer_never_outputs_stored_html() -> None:
    rendered = render_affiliate_readiness(
        {
            "amazon_affiliate_ready": False,
            "rakuten_kobo_affiliate_ready": False,
            "dmm_affiliate_ready": False,
            "affiliate_url": '<script>alert("unsafe")</script>',
            "dmm_affiliate_html": '<img src=x onerror="alert(1)">',
        }
    )

    assert "<script" not in rendered
    assert "<img" not in rendered
    assert "onerror" not in rendered


def test_database_page_contains_workflow_columns() -> None:
    page = render_database_search_page("")

    assert "<th>Workflow</th>" in page
    assert "<th>WordPress</th>" in page
    assert "<th>X</th>" in page
    assert "<th>Review</th>" in page
    assert "<th>Affiliate</th>" in page
    assert "<th>Image</th>" in page
    assert "<th>Publish Ready</th>" in page
    assert "<th>アフィリエイト登録</th>" in page
    assert "アフィリエイト数" not in page


def _bulk_selection_row(**overrides):
    values = {
        "id": "31cfd69e-3c43-4bfd-9fe7-f3e8cae75f00",
        "source_item_id": "bulk-source",
        "title": "Bulk Selection Book",
        "volume_label": "1巻",
        "author_name": "作者",
        "publisher_name": "出版社",
        "release_date": "2026-08-03",
        "item_type": "tankobon",
        "store_names": "amazon",
        "prices": "amazon:700 JPY",
        "amazon_affiliate_ready": False,
        "rakuten_kobo_affiliate_ready": False,
        "dmm_affiliate_ready": False,
        "workflow_status": "READY",
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": "",
        "x_status": "NOT_CREATED",
        "affiliate_status": "MISSING",
        "image_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "last_error": "",
        "is_excluded": False,
        "rakuten_kobo_offer": None,
        "affiliate_registration_capability": "READY_TO_REGISTER",
        "wordpress_draft_capability": "READY",
        "wordpress_schedule_capability": "NOT_DRAFT",
    }
    values.update(overrides)
    return values


def test_database_result_row_has_dedicated_bulk_checkbox(monkeypatch) -> None:
    import app.gui.ebook_database_web as web

    row = _bulk_selection_row()
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(web, "search_database_rows", lambda _state: [row])

    page = web.render_database_search_page(
        "summary_date=2026-08-03&affiliate_status=all_unregistered"
    )

    assert page.count('class="bulk-operation-item-checkbox"') == 1
    assert 'name="selected_ebook_item_ids"' in page
    assert f'value="{row["id"]}"' in page
    assert 'name="included" value="true"' in page
    assert 'name="included" class="bulk-operation-item-checkbox"' not in page
    assert 'name="affiliate_status"' in page
    assert 'value="all_unregistered" selected' in page


def test_bulk_selection_panel_has_limit_and_page_scope_text() -> None:
    page = render_database_search_page("")

    assert "一括処理対象" in page
    assert "選択件数:" in page
    assert "0 / 5件" in page
    assert "最大5件" in page
    assert "選択は現在のページ内だけ有効です" in page
    assert "表示中を選択" in page
    assert "選択解除" in page
    assert "選択内容を確認" in page


def test_zero_results_have_no_bulk_item_checkbox() -> None:
    page = render_database_search_page("")

    assert 'class="bulk-operation-item-checkbox"' not in page


def test_excluded_row_bulk_checkbox_is_disabled(monkeypatch) -> None:
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(web, "count_database_rows", lambda _state: 1)
    monkeypatch.setattr(
        web,
        "search_database_rows",
        lambda _state: [_bulk_selection_row(is_excluded=True)],
    )

    page = web.render_database_search_page("include_excluded=true")

    checkbox = page.split('class="bulk-operation-item-checkbox"', 1)[1]
    assert "disabled" in checkbox.split(">", 1)[0]
    assert "除外済みのため選択できません" in checkbox.split(">", 1)[0]


def test_supplement_page_does_not_use_bulk_selection_checkbox() -> None:
    from app.gui.ebook_database_web import render_supplement_import_page

    page = render_supplement_import_page("", csrf_token="token")

    assert 'name="selected_ebook_item_ids"' not in page
    assert 'class="bulk-operation-item-checkbox"' not in page


def test_affiliate_settings_page_contains_dmm_destination_forms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_affiliate_setting_views",
        lambda: {
            "amazon": SimpleNamespace(
                masked_affiliate_id="未登録",
                source="database",
                enabled=False,
            )
        },
    )
    monkeypatch.setattr(
        web,
        "load_dmm_destination_profile_views",
        lambda: {
            "blog_main": web.DmmDestinationProfileDisplay(
                provider="dmm",
                destination_type="wordpress",
                destination_key="blog_main",
                display_name="メインブログ",
                masked_affiliate_id="blo*****008",
                configured=True,
                active=True,
                channel="toolbar",
                channel_id="text",
            ),
            "x_main": web.DmmDestinationProfileDisplay(
                provider="dmm",
                destination_type="x",
                destination_key="x_main",
                display_name="公式X",
                masked_affiliate_id="未登録",
                configured=False,
                active=False,
                channel="toolbar",
                channel_id="text",
            ),
        },
    )

    page = web.render_affiliate_settings_page()

    assert "DMM掲載先別設定" in page
    assert 'value="blog_main"' in page
    assert 'value="wordpress"' in page
    assert 'value="x_main"' in page
    assert 'value="x"' in page
    assert page.count('name="affiliate_id"') == 3
    assert "未設定の掲載先を別IDで代替しません" in page


def test_affiliate_settings_page_escapes_destination_display_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace
    import app.gui.ebook_database_web as web

    monkeypatch.setattr(
        web,
        "load_affiliate_setting_views",
        lambda: {
            "amazon": SimpleNamespace(
                masked_affiliate_id="未登録",
                source="database",
                enabled=False,
            )
        },
    )
    monkeypatch.setattr(
        web,
        "load_dmm_destination_profile_views",
        lambda: {
            key: web.DmmDestinationProfileDisplay(
                provider="dmm",
                destination_type=("wordpress" if key == "blog_main" else "x"),
                destination_key=key,
                display_name="<script>alert(1)</script>",
                masked_affiliate_id="未登録",
                configured=False,
                active=False,
                channel="toolbar",
                channel_id="text",
            )
            for key in ("blog_main", "x_main")
        },
    )

    page = web.render_affiliate_settings_page()

    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_workflow_action_form_is_post_with_token() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-test-id",
            "workflow_status": "NEW",
        },
        "keyword=test",
    )

    assert 'method="post"' in html
    assert 'action="/database-workflow"' in html
    assert 'name="csrf_token"' in html
    assert 'name="item_id"' in html
    assert 'value="ebook-test-id"' in html
    assert 'name="new_status"' in html
    assert 'value="REVIEW"' in html
    assert "レビュー開始" in html
    assert "confirm(" in html


def test_published_item_has_no_update_form() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-published-id",
            "workflow_status": "PUBLISHED",
        }
    )

    assert "<form" not in html
    assert "完了" in html


def test_review_not_reviewed_is_inconsistent() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-review-id",
            "workflow_status": "REVIEW",
            "review_status": "NOT_REVIEWED",
            "is_excluded": False,
        }
    )

    assert "状態不整合：管理確認が必要" in html
    assert "<form" not in html


def test_review_in_review_shows_pending_decision_forms() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-review-id",
            "workflow_status": "REVIEW",
            "review_status": "IN_REVIEW",
            "is_excluded": False,
        },
        pending_approval={
            "id": "12345678-abcd-efgh-ijkl-123456789012",
            "approval_type": "REVIEW_READY",
            "status": "PENDING",
            "expires_at": "2026-07-22 16:00:00",
            "token_available": True,
            "is_expired": False,
        },
    )

    assert "承認待ち" in html
    assert "request=12345678…" in html
    assert "type=REVIEW_READY" in html
    assert 'value="APPROVE"' in html
    assert 'value="REJECT"' in html
    assert html.count(
        'action="/database-review-ready-decision"'
    ) == 2
    assert "approval_token" not in html


@pytest.mark.parametrize(
    ("token_available", "is_expired", "reason"),
    [
        (False, False, "承認tokenを復元できません"),
        (True, True, "期限切れ"),
    ],
)
def test_unusable_pending_request_shows_reissue_only(
    token_available,
    is_expired,
    reason,
) -> None:
    from app.gui.ebook_database_web import render_workflow_action_form

    html = render_workflow_action_form(
        {
            "id": "ebook-review-id",
            "workflow_status": "REVIEW",
            "review_status": "IN_REVIEW",
            "is_excluded": False,
        },
        pending_approval={
            "id": "12345678-abcd-efgh-ijkl-123456789012",
            "approval_type": "REVIEW_READY",
            "status": "PENDING",
            "expires_at": "2026-07-22 16:00:00",
            "token_available": token_available,
            "is_expired": is_expired,
        },
    )

    assert reason in html
    assert "承認申請を再発行" in html
    assert 'action="/database-review-ready-reissue"' in html
    assert 'action="/database-review-ready-decision"' not in html
    assert 'value="APPROVE"' not in html
    assert 'value="REJECT"' not in html


def test_review_in_review_without_request_shows_approval_request() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-review-id",
            "workflow_status": "REVIEW",
            "review_status": "IN_REVIEW",
            "is_excluded": False,
        }
    )

    assert "承認申請" in html
    assert 'action="/database-review-ready-request"' in html


def test_ready_approved_shows_completed_without_transition() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-ready-id",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "is_excluded": False,
        }
    )

    assert "準備完了 / 承認済み" in html
    assert "<form" not in html


def test_ready_without_approval_is_inconsistent() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-ready-id",
            "workflow_status": "READY",
            "review_status": "NOT_REVIEWED",
            "is_excluded": False,
        }
    )

    assert "状態不整合：管理確認が必要" in html
    assert "<form" not in html


def test_excluded_review_item_has_no_approval_action() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_action_form,
    )

    html = render_workflow_action_form(
        {
            "id": "ebook-excluded-id",
            "workflow_status": "REVIEW",
            "review_status": "NOT_REVIEWED",
            "is_excluded": True,
        }
    )

    assert "除外済み：操作不可" in html
    assert "<form" not in html


def test_wordpress_button_requires_ready_and_approved() -> None:
    from app.gui.ebook_database_web import (
        render_wordpress_draft_action_form,
    )

    unapproved = render_wordpress_draft_action_form(
        {
            "id": "ebook-wp-id",
            "title": "sample",
            "author_name": "作者",
            "publisher_name": "出版社",
            "workflow_status": "READY",
            "review_status": "NOT_REVIEWED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
            "publish_ready": False,
        }
    )
    approved = render_wordpress_draft_action_form(
        {
            "id": "ebook-wp-id",
            "title": "sample",
            "author_name": "作者",
            "publisher_name": "出版社",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
            "publish_ready": False,
        },
        approved_request={
            "id": "approval-1",
            "ebook_item_id": "ebook-wp-id",
            "approval_type": "REVIEW_READY",
            "status": "APPROVED",
            "decided_at": "2026-07-22T00:00:00+00:00",
            "expected_current_status": "REVIEW",
            "requested_status": "READY",
        },
    )

    assert 'action="/database-wordpress-draft"' not in unapproved
    assert "WordPress下書き作成（承認後）" in unapproved
    assert 'action="/database-wordpress-draft"' in approved
    assert 'name="csrf_token"' in approved
    assert 'value="create_wordpress_draft"' in approved
    assert "公開はしません" in approved


def test_missing_publisher_is_scoped_to_draft_creation_row() -> None:
    from app.gui.ebook_database_web import render_wordpress_draft_action_form

    html = render_wordpress_draft_action_form(
        {
            "id": "ebook-missing-publisher",
            "title": "sample",
            "author_name": "作者",
            "publisher_name": "",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
            "publish_ready": False,
        },
        approved_request={
            "ebook_item_id": "ebook-missing-publisher",
            "approval_type": "REVIEW_READY",
            "status": "APPROVED",
            "decided_at": "2026-07-22T00:00:00+00:00",
            "expected_current_status": "REVIEW",
            "requested_status": "READY",
        },
    )
    assert "METADATA_REVIEW_REQUIRED: missing publisher_name" in html
    assert 'action="/database-wordpress-draft"' not in html


def test_approved_draft_with_post_id_shows_schedule_form() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form
    from app.integrations.wordpress_rest_client import WordPressCategory

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "264",
        },
        schedule_state={"remote_status": "draft"},
        wordpress_categories=[
            WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
        ],
    )
    assert 'type="datetime-local"' in html
    assert 'name="publish_at"' in html
    assert 'step="60"' in html
    assert 'name="wordpress_category_id"' in html
    assert '<option value="43">コミック新刊</option>' in html
    assert "カテゴリーを設定して予約投稿" in html
    assert 'action="/database-wordpress-schedule"' in html


@pytest.mark.parametrize(
    "overrides",
    [
        {"review_status": "NOT_REVIEWED"},
        {"workflow_status": "COLLECTED"},
    ],
)
def test_ineligible_item_does_not_show_schedule_form(overrides) -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    row = {
        "id": "ebook-1",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "wordpress_status": "DRAFT",
        "wordpress_post_id": "264",
    }
    row.update(overrides)
    assert render_wordpress_schedule_action_form(row) == ""


@pytest.mark.parametrize("workflow_status", ["READY", "REVIEW"])
def test_not_created_item_keeps_disabled_wordpress_section(workflow_status) -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "author_name": "作者",
            "publisher_name": "出版社",
            "workflow_status": workflow_status,
            "review_status": "APPROVED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
        }
    )

    assert "WordPress予約・カテゴリー" in html
    assert "WordPress投稿：未作成" in html
    assert "先にWordPress下書きを作成してください" in html
    assert html.count("disabled") >= 4
    assert '<form method="post"' not in html
    assert 'href="#catalog-edit-ebook-1"' in html


def test_not_created_item_with_missing_publisher_keeps_section() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-missing-publisher",
            "author_name": "作者",
            "publisher_name": "",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
        }
    )

    assert "WordPress予約・カテゴリー" in html
    assert "missing: publisher_name" in html
    assert "基本情報を完成後、下書きを作成してください" in html
    assert "disabled" in html
    assert "基本情報編集" in html


def test_same_wordpress_section_becomes_enabled_after_draft_creation() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form
    from app.integrations.wordpress_rest_client import WordPressCategory

    base = {
        "id": "ebook-1",
        "author_name": "作者",
        "publisher_name": "出版社",
        "workflow_status": "READY",
        "review_status": "APPROVED",
    }
    before = render_wordpress_schedule_action_form({
        **base,
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
    })
    after = render_wordpress_schedule_action_form(
        {
            **base,
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "264",
        },
        schedule_state={"remote_status": "draft"},
        wordpress_categories=[
            WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
        ],
    )

    assert "WordPress投稿：未作成" in before
    assert 'action="/database-wordpress-schedule"' not in before
    assert "WordPress投稿: post_id=264" in after
    assert 'action="/database-wordpress-schedule"' in after
    assert "カテゴリーを設定して予約投稿" in after


def test_scheduled_item_shows_jst_reschedule_and_cancel() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form
    from app.integrations.wordpress_rest_client import WordPressCategory

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "SCHEDULED",
            "wordpress_post_id": "264",
        },
        schedule_state={
            "publish_at_local": "2026-08-03T07:00:00+09:00",
            "remote_status": "future",
            "current_categories": [
                WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
            ],
        },
        wordpress_categories=[
            WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
        ],
    )
    assert "予約済み: 2026-08-03 07:00 JST" in html
    assert "現在のカテゴリー: コミック新刊" in html
    assert "カテゴリーと予約日時を変更" in html
    assert "カテゴリーを更新" in html
    assert "予約を解除して下書きへ戻す" in html
    assert 'value="RESCHEDULE"' in html
    assert 'value="CANCEL_SCHEDULE"' in html


def test_published_item_shows_publication_without_schedule_actions() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "PUBLISHED",
            "wordpress_post_id": "301",
        },
        schedule_state={
            "remote_status": "publish",
            "remote_date": "2026-08-02T20:30:00",
        },
    )

    assert "WordPress状態：公開済み" in html
    assert "公開日時: 2026-08-02 20:30 JST" in html
    assert "remote_unavailable" not in html
    assert "カテゴリーと予約日時を変更" not in html
    assert "予約を解除して下書きへ戻す" not in html
    assert "カテゴリーを更新" not in html
    assert '<form method="post"' not in html


def test_active_schedule_claim_keeps_disabled_schedule_section() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "264",
        },
        schedule_state={"claim_status": "CLAIMED"},
    )
    assert "WordPress予約・カテゴリー" in html
    assert "WordPress状態: 確認できません" in html
    assert "disabled" in html
    assert "WordPress状態を再確認" in html
    assert '<form method="post"' not in html


@pytest.mark.parametrize(
    ("schedule_state", "state_text", "error_code"),
    [
        ({"remote_status": "trash"}, "WordPress投稿はゴミ箱内です", "remote_status_trash"),
        (
            {"remote_state_error": True, "remote_error_code": "post_not_found"},
            "WordPress投稿が見つかりません",
            "post_not_found",
        ),
        (
            {"remote_state_error": True, "remote_error_code": "authentication_failed"},
            "WordPress認証を確認してください",
            "authentication_failed",
        ),
        (
            {"remote_state_error": True, "remote_error_code": "remote_unavailable"},
            "WordPress状態: 確認できません",
            "remote_unavailable",
        ),
    ],
)
def test_remote_failure_keeps_disabled_wordpress_section(
    schedule_state,
    state_text,
    error_code,
) -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "222",
        },
        schedule_state=schedule_state,
        query_string="keyword=sample&page=2",
    )

    assert "WordPress予約・カテゴリー" in html
    assert "post_id=222" in html
    assert state_text in html
    assert f"error_code={error_code}" in html
    assert "disabled" in html
    assert '<form method="post"' not in html
    assert "keyword=sample&amp;page=2" in html
    assert "WordPress状態を再確認" in html


def test_category_list_failure_keeps_remote_state_and_cancel_available() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "SCHEDULED",
            "wordpress_post_id": "264",
        },
        schedule_state={
            "remote_status": "future",
            "publish_at_local": "2026-08-03T07:00:00+09:00",
        },
        wordpress_categories=[],
    )

    assert "WordPress状態: 予約済み" in html
    assert "カテゴリー一覧を取得できない" in html
    assert "<select disabled>" in html
    assert "予約を解除して下書きへ戻す" in html
    assert 'value="CANCEL_SCHEDULE"' in html


def test_wordpress_category_context_filters_to_verified_allowlist(
    monkeypatch,
) -> None:
    from types import SimpleNamespace

    from app.gui.ebook_database_web import load_wordpress_category_context
    from app.integrations.wordpress_rest_client import WordPressCategory

    categories = [
        WordPressCategory(43, "コミック新刊", "comic-new-release", 1),
        WordPressCategory(1, "未分類", "uncategorized", 23),
    ]

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def list_categories(self, *, per_page):
            assert per_page == 100
            return categories

        def get_post_state(self, *, post_id):
            assert post_id == 264
            return SimpleNamespace(status="draft", categories=(1,))

    monkeypatch.setenv("WORDPRESS_BASE_URL", "https://example.test")
    monkeypatch.setenv("WORDPRESS_USERNAME", "tester")
    monkeypatch.setenv("WORDPRESS_APPLICATION_PASSWORD", "dummy")
    monkeypatch.setattr(
        "app.integrations.wordpress_rest_client.WordPressRestClient",
        FakeClient,
    )
    context = load_wordpress_category_context([
        {
            "id": "ebook-1",
            "review_status": "APPROVED",
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "264",
        }
    ])
    assert [category.slug for category in context.categories] == ["comic-new-release"]
    assert [
        category.name
        for category in context.item_states["ebook-1"]["current_categories"]
    ] == ["未分類"]


@pytest.mark.parametrize(
    "raw_query",
    [
        "page=1",
        "page=2",
        "keyword=sample&page=1",
    ],
)
def test_database_search_rebuilds_wordpress_context_on_every_page(
    monkeypatch,
    raw_query,
) -> None:
    from app.gui import ebook_database_web as web
    from app.integrations.wordpress_rest_client import WordPressCategory

    row = {
        "id": "ebook-1",
        "source_item_id": "source-1",
        "title": "sample",
        "volume_label": "",
        "author_name": "作者",
        "publisher_name": "出版社",
        "release_date": "2026-08-02",
        "item_type": "tankobon",
        "store_names": "rakuten_kobo",
        "prices": "rakuten_kobo:700 JPY",
        "amazon_affiliate_ready": False,
        "rakuten_kobo_affiliate_ready": True,
        "dmm_affiliate_ready": False,
        "workflow_status": "READY",
        "wordpress_status": "DRAFT",
        "wordpress_post_id": "264",
        "x_status": "NOT_CREATED",
        "affiliate_status": "READY",
        "image_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "last_error": "",
        "is_excluded": False,
        "rakuten_kobo_offer": None,
    }
    category = WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 400)
    monkeypatch.setattr(web, "search_database_rows", lambda _state: [row])
    monkeypatch.setattr(web, "load_wordpress_schedule_states", lambda _ids: {
        "ebook-1": {"publish_at_local": "2026-08-03T07:00:00+09:00"}
    })
    monkeypatch.setattr(web, "load_wordpress_category_context", lambda _rows: (
        web.WordPressCategoryPageContext(
            categories=[category],
            item_states={
                "ebook-1": {
                    "remote_status": "draft",
                    "current_categories": [category],
                }
            },
        )
    ))

    page = web.render_database_search_page(raw_query, csrf_token="fresh-token")

    assert "カテゴリーを設定して予約投稿" in page
    assert 'name="wordpress_category_id"' in page
    assert "現在のカテゴリー: コミック新刊" in page
    assert 'value="fresh-token"' in page


@pytest.mark.parametrize(
    "raw_query",
    ["page=1", "page=2", "keyword=sample&page=1"],
)
def test_database_search_keeps_not_created_wordpress_section(
    monkeypatch,
    raw_query,
) -> None:
    from app.gui import ebook_database_web as web

    row = {
        "id": "ebook-1",
        "source_item_id": "source-1",
        "title": "sample",
        "volume_label": "",
        "author_name": "作者",
        "publisher_name": "出版社",
        "release_date": "2026-08-02",
        "item_type": "tankobon",
        "store_names": "",
        "prices": "",
        "amazon_affiliate_ready": False,
        "rakuten_kobo_affiliate_ready": False,
        "dmm_affiliate_ready": False,
        "workflow_status": "READY",
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
        "x_status": "NOT_CREATED",
        "affiliate_status": "READY",
        "image_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "last_error": "",
        "is_excluded": False,
        "rakuten_kobo_offer": None,
    }
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 400)
    monkeypatch.setattr(web, "search_database_rows", lambda _state: [row])

    page = web.render_database_search_page(raw_query)

    assert "WordPress予約・カテゴリー" in page
    assert "WordPress投稿：未作成" in page
    assert "先にWordPress下書きを作成してください" in page
    assert 'href="#catalog-edit-ebook-1"' in page
    assert 'id="catalog-edit-ebook-1"' in page


def test_existing_post_can_schedule_without_publisher() -> None:
    from app.gui.ebook_database_web import render_wordpress_schedule_action_form
    from app.integrations.wordpress_rest_client import WordPressCategory

    html = render_wordpress_schedule_action_form(
        {
            "id": "ebook-1",
            "publisher_name": "",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "DRAFT",
            "wordpress_post_id": "264",
        },
        schedule_state={"remote_status": "draft"},
        wordpress_categories=[
            WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
        ],
    )
    assert "カテゴリーを設定して予約投稿" in html
    assert "METADATA_REVIEW_REQUIRED" not in html


def test_category_loader_failure_shows_notice_without_breaking_page(monkeypatch) -> None:
    from app.gui import ebook_database_web as web

    monkeypatch.setattr(web, "load_wordpress_category_context", lambda _rows: (_ for _ in ()).throw(RuntimeError("offline")))
    page = web.render_database_search_page("")
    assert "WordPressカテゴリー一覧を取得できませんでした" in page
    assert "電子書籍データベース検索" in page


def test_schedule_evidence_failure_stops_only_affected_row(monkeypatch) -> None:
    from app.gui import ebook_database_web as web
    from app.integrations.wordpress_rest_client import WordPressCategory

    base = {
        "source_item_id": "source",
        "title": "sample",
        "volume_label": "",
        "author_name": "作者",
        "publisher_name": "出版社",
        "release_date": "2026-08-02",
        "item_type": "tankobon",
        "store_names": "",
        "prices": "",
        "amazon_affiliate_ready": False,
        "rakuten_kobo_affiliate_ready": False,
        "dmm_affiliate_ready": False,
        "workflow_status": "READY",
        "wordpress_status": "DRAFT",
        "wordpress_post_id": "264",
        "x_status": "NOT_CREATED",
        "affiliate_status": "READY",
        "image_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "is_excluded": False,
        "rakuten_kobo_offer": None,
    }
    rows = [{**base, "id": "broken"}, {**base, "id": "healthy", "wordpress_post_id": "265"}]
    category = WordPressCategory(43, "コミック新刊", "comic-new-release", 1)
    monkeypatch.setattr(web, "count_database_rows", lambda _state: 2)
    monkeypatch.setattr(web, "search_database_rows", lambda _state: rows)
    monkeypatch.setattr(web, "load_wordpress_schedule_states", lambda _ids: {
        "broken": {"loader_error": True, "claim_status": "UNKNOWN"},
        "healthy": {},
    })
    monkeypatch.setattr(web, "load_wordpress_category_context", lambda _rows: web.WordPressCategoryPageContext(
        categories=[category],
        item_states={
            "broken": {"remote_status": "draft"},
            "healthy": {"remote_status": "draft"},
        },
    ))
    page = web.render_database_search_page("")
    assert page.count("WordPress状態: 確認できません") == 1
    assert page.count("WordPress状態を再確認") == 1
    assert page.count("カテゴリーを設定して予約投稿") == 1


@pytest.mark.parametrize(
    ("execution_state", "expected"),
    [
        ({"status": "CLAIMED"}, "下書き作成処理中"),
        (
            {
                "status": (
                    "WORDPRESS_DRAFT_CREATED_DB_"
                    "RECONCILIATION_REQUIRED"
                ),
                "wordpress_post_id": 321,
            },
            "WordPress下書きは作成済みの可能性があります",
        ),
        (
            {
                "status": "WORDPRESS_DRAFT_CREATED",
                "wordpress_post_id": 321,
            },
            "WordPress下書き作成（承認後）",
        ),
        (
            {"status": "FAILED_PRE_EXTERNAL"},
            "状態不整合：管理確認が必要",
        ),
    ],
)
def test_wordpress_execution_state_removes_action_form(
    execution_state,
    expected,
) -> None:
    from app.gui.ebook_database_web import (
        render_wordpress_draft_action_form,
    )

    html = render_wordpress_draft_action_form(
        {
            "id": "ebook-wp-id",
            "title": "sample",
            "workflow_status": "READY",
            "review_status": "APPROVED",
            "wordpress_status": "NOT_CREATED",
            "wordpress_post_id": None,
            "publish_ready": False,
            "is_excluded": False,
        },
        execution_state=execution_state,
    )

    assert expected in html
    assert 'action="/database-wordpress-draft"' not in html


def test_wordpress_form_requires_bound_formal_approval() -> None:
    from app.gui.ebook_database_web import (
        render_wordpress_draft_action_form,
    )

    row = {
        "id": "ebook-wp-id",
        "title": "sample",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
        "publish_ready": False,
        "is_excluded": False,
    }
    missing = render_wordpress_draft_action_form(row)
    wrong_item = render_wordpress_draft_action_form(
        row,
        approved_request={
            "ebook_item_id": "other-item",
            "approval_type": "REVIEW_READY",
            "status": "APPROVED",
            "decided_at": "2026-07-22T00:00:00+00:00",
            "expected_current_status": "REVIEW",
            "requested_status": "READY",
        },
    )

    assert 'action="/database-wordpress-draft"' not in missing
    assert 'action="/database-wordpress-draft"' not in wrong_item


def test_workflow_notice_uses_whitelist() -> None:
    from app.gui.ebook_database_web import (
        render_workflow_notice,
    )

    success = render_workflow_notice(
        {"workflow_update": ["success"]}
    )

    unknown = render_workflow_notice(
        {"workflow_update": ["<script>"]}
    )

    assert "状態を更新" in success
    assert "workflow-notice-success" in success
    assert unknown == ""
