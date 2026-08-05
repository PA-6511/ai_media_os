from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.db.read_only_session import (
    create_sqlite_read_only_session_factory,
    sqlite_read_only_uri,
)
from app.db.repositories.workflow_repository import WorkflowRepository
from app.gui import ebook_database_web
from app.gui.ebook_database_web import (
    DatabaseSearchPageState,
    count_database_rows,
    parse_database_search_query,
    search_database_rows,
)


def _item(
    item_id: str,
    *,
    title: str,
    is_excluded: bool = False,
) -> EbookItem:
    return EbookItem(
        id=item_id,
        source_name="read-only-test",
        source_item_id=item_id,
        title=title,
        normalized_title=title,
        release_date=date(2026, 7, 22),
        item_type="tankobon",
        is_excluded=is_excluded,
    )


def _create_seeded_database(tmp_path):
    database_path = tmp_path / "ebook-search.db"
    write_engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(write_engine)

    with Session(write_engine) as session:
        complete = _item("complete", title="Complete")
        complete.offers.append(
            StoreOffer(
                store_name="amazon",
                store_item_id="COMPLETE-ASIN",
                price_yen=770,
                affiliate_url="https://example.test/complete",
            )
        )

        missing_price = _item("missing-price", title="Missing Price")
        missing_price.offers.append(
            StoreOffer(
                store_name="rakuten_kobo",
                store_item_id="MISSING-PRICE",
                price_yen=None,
                affiliate_url="https://example.test/missing-price",
            )
        )

        missing_affiliate = _item(
            "missing-affiliate",
            title="Missing Affiliate",
        )
        missing_affiliate.offers.extend(
            [
                StoreOffer(
                    store_name="amazon",
                    store_item_id="MISSING-AFFILIATE-AMAZON",
                    price_yen=880,
                    affiliate_url=None,
                ),
                StoreOffer(
                    store_name="dmm",
                    store_item_id="MISSING-AFFILIATE-DMM",
                    price_yen=860,
                    affiliate_url="   ",
                ),
            ]
        )

        excluded = _item(
            "excluded",
            title="Excluded",
            is_excluded=True,
        )
        session.add_all(
            [
                complete,
                missing_price,
                missing_affiliate,
                excluded,
            ]
        )
        session.commit()

    write_engine.dispose()
    return database_path


def _read_only_factory(tmp_path):
    database_path = _create_seeded_database(tmp_path)
    factory = create_sqlite_read_only_session_factory(database_path)
    return database_path, factory


def _paginated_read_only_factory(tmp_path, item_count=401):
    database_path = tmp_path / "ebook-pagination.db"
    write_engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(write_engine)
    with Session(write_engine) as session:
        session.add_all(
            [
                _item(
                    f"item-{index:04d}",
                    title=f"Title {index:04d}",
                )
                for index in range(item_count)
            ]
        )
        session.commit()
    write_engine.dispose()
    return create_sqlite_read_only_session_factory(database_path)


def _ids(rows):
    return {row["id"] for row in rows}


def test_read_only_uri_uses_sqlite_mode_ro(tmp_path) -> None:
    database_path = tmp_path / "uri mode.db"

    assert sqlite_read_only_uri(database_path).endswith(
        "/uri%20mode.db?mode=ro"
    )


def test_read_only_search_returns_rows_without_journal_mode_change(
    monkeypatch,
    tmp_path,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    engine = factory.kw["bind"]
    statements: list[str] = []

    event.listen(
        engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, _params, _context, _many: (
            statements.append(statement)
        ),
    )
    monkeypatch.setattr(
        ebook_database_web,
        "ReadOnlySessionLocal",
        factory,
    )

    dashboard = ebook_database_web.load_dashboard_summary()
    rows = search_database_rows(DatabaseSearchPageState())

    assert dashboard["cards"]["missing_price"] == 1
    assert dashboard["cards"]["missing_affiliate"] == 1
    assert _ids(rows) == {
        "complete",
        "missing-price",
        "missing-affiliate",
    }
    assert statements
    assert all("journal_mode" not in statement.lower() for statement in statements)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)


def test_read_only_connection_rejects_database_writes(tmp_path) -> None:
    _database_path, factory = _read_only_factory(tmp_path)

    with factory() as session:
        with pytest.raises(OperationalError, match="readonly"):
            session.execute(
                text(
                    "UPDATE ebook_items "
                    "SET title = 'changed' "
                    "WHERE id = 'complete'"
                )
            )


def test_search_uses_count_limit_offset_and_existing_order(
    monkeypatch,
    tmp_path,
) -> None:
    factory = _paginated_read_only_factory(tmp_path)
    engine = factory.kw["bind"]
    statements: list[tuple[str, object]] = []
    event.listen(
        engine,
        "before_cursor_execute",
        lambda _conn, _cursor, statement, params, _context, _many: (
            statements.append((statement, params))
        ),
    )
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    total_count = count_database_rows(DatabaseSearchPageState())
    first_page = search_database_rows(DatabaseSearchPageState())
    second_page = search_database_rows(DatabaseSearchPageState(page=2))
    third_page = search_database_rows(DatabaseSearchPageState(page=3))

    assert total_count == 401
    assert len(first_page) == 200
    assert len(second_page) == 200
    assert len(third_page) == 1
    assert second_page[0]["id"] == "item-0200"
    item_selects = [
        (statement, params)
        for statement, params in statements
        if "from ebook_items" in statement.lower()
        and "order by" in statement.lower()
    ]
    assert item_selects
    assert all(
        "ebook_items.release_date asc, ebook_items.title asc"
        in statement.lower()
        for statement, _params in item_selects
    )
    assert any(params[-2:] == (200, 200) for _statement, params in item_selects)
    count_selects = [
        statement
        for statement, _params in statements
        if "count(" in statement.lower()
    ]
    assert count_selects
    assert all(" limit " not in statement.lower() for statement in count_selects)


@pytest.mark.parametrize(
    ("raw_query", "field_name"),
    [
        ("missing_price=true", "missing_price"),
        ("missing_affiliate=YES", "missing_affiliate"),
        ("excluded_only=On", "excluded_only"),
        ("include_excluded=1", "include_excluded"),
    ],
)
def test_boolean_search_parameters_accept_only_supported_true_values(
    raw_query,
    field_name,
) -> None:
    state = parse_database_search_query(raw_query)

    assert getattr(state, field_name) is True


@pytest.mark.parametrize("value", ["", "0", "false", "off", "unknown"])
def test_unknown_boolean_search_parameters_are_false(value) -> None:
    state = parse_database_search_query(f"missing_price={value}")

    assert state.missing_price is False


def test_missing_price_filter_returns_only_items_without_any_price(
    monkeypatch,
    tmp_path,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    rows = search_database_rows(
        DatabaseSearchPageState(missing_price=True)
    )

    assert _ids(rows) == {"missing-price"}


def test_missing_affiliate_filter_requires_nonblank_affiliate_url(
    monkeypatch,
    tmp_path,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    rows = search_database_rows(
        DatabaseSearchPageState(missing_affiliate=True)
    )

    assert _ids(rows) == {"missing-affiliate"}


def test_excluded_only_filter_returns_only_excluded_items(
    monkeypatch,
    tmp_path,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    rows = search_database_rows(
        DatabaseSearchPageState(excluded_only=True)
    )

    assert _ids(rows) == {"excluded"}


def test_include_excluded_remains_backward_compatible(
    monkeypatch,
    tmp_path,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    rows = search_database_rows(
        DatabaseSearchPageState(include_excluded=True)
    )

    assert _ids(rows) == {
        "complete",
        "missing-price",
        "missing-affiliate",
        "excluded",
    }


def test_normal_search_behavior_is_preserved(monkeypatch, tmp_path) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    rows = search_database_rows(
        DatabaseSearchPageState(keyword="Complete")
    )

    assert _ids(rows) == {"complete"}


@pytest.mark.parametrize(
    "state",
    [
        DatabaseSearchPageState(keyword="Complete"),
        DatabaseSearchPageState(store_name="rakuten_kobo"),
        DatabaseSearchPageState(missing_price=True),
        DatabaseSearchPageState(missing_affiliate=True),
        DatabaseSearchPageState(excluded_only=True),
        DatabaseSearchPageState(include_excluded=True),
    ],
)
def test_count_and_list_use_the_same_filters(
    monkeypatch,
    tmp_path,
    state,
) -> None:
    _database_path, factory = _read_only_factory(tmp_path)
    monkeypatch.setattr(ebook_database_web, "ReadOnlySessionLocal", factory)

    assert count_database_rows(state) == len(search_database_rows(state))


def test_database_search_page_uses_explicit_read_only_filter_names(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        ebook_database_web,
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
                "today": "2026-07-22",
                "tomorrow": "2026-07-23",
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
    monkeypatch.setattr(
        ebook_database_web,
        "search_database_rows",
        lambda _state: [],
    )
    monkeypatch.setattr(
        ebook_database_web,
        "count_database_rows",
        lambda _state: 0,
    )

    page = ebook_database_web.render_database_search_page(
        "missing_price=on&missing_affiliate=yes&excluded_only=1"
    )

    assert 'href="/database-search?excluded_only=true"' in page
    assert 'name="missing_price"' in page
    assert 'name="missing_affiliate"' in page
    assert 'name="excluded_only"' in page
    assert "除外済みだけ表示" in page


def test_workflow_repository_remains_writable_with_write_session(
    tmp_path,
) -> None:
    database_path = _create_seeded_database(tmp_path)
    write_engine = create_engine(f"sqlite:///{database_path}")
    write_factory = sessionmaker(bind=write_engine)

    with write_factory() as session:
        item = session.get(EbookItem, "complete")
        assert item is not None
        WorkflowRepository(session).set_workflow_status(
            item,
            "REVIEW",
            changed_by="test:write-session",
        )
        session.commit()

    with write_factory() as session:
        status = session.scalar(
            select(EbookItem.workflow_status).where(
                EbookItem.id == "complete"
            )
        )

    write_engine.dispose()
    assert status == "REVIEW"
