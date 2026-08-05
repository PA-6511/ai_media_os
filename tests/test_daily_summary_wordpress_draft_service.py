from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    DailySummaryRunHistory,
    DailySummarySelection,
    EbookItem,
    StoreOffer,
)
from app.services.daily_summary_wordpress_draft_service import (
    DailySummaryDraftError,
    DailySummaryWordPressDraftService,
)


SUMMARY_DATE = date(2026, 8, 3)


class FakeWordPressClient:
    def __init__(self, *, item_status: str = "publish") -> None:
        self.item_status = item_status
        self.created = []
        self.updated = []
        self.summary_status = "draft"
        self.create_error = False

    def get_post_state(self, *, post_id: int):
        if post_id == 301:
            return SimpleNamespace(
                post_id=post_id,
                status=self.item_status,
                link="https://example.com/item-301",
            )
        return SimpleNamespace(
            post_id=post_id,
            status=self.summary_status,
            link="https://example.com/summary",
        )

    def get_post_affiliate_meta(self, *, post_id: int):
        return SimpleNamespace(
            post_id=post_id,
            meta={"kindle_url": "https://example.com/kindle"},
        )

    def create_draft(self, payload):
        if self.create_error:
            raise RuntimeError("transport outcome unknown")
        self.created.append(payload)
        return SimpleNamespace(post_id=900, status="draft")

    def update_draft(self, *, post_id: int, payload):
        self.updated.append((post_id, payload))
        return SimpleNamespace(post_id=post_id, status="draft")


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value


def add_selected_item(session: Session, *, local_status: str = "PUBLISHED") -> None:
    item = EbookItem(
        id="item-1",
        source_name="test",
        source_item_id="item-1",
        title="新刊A",
        release_date=SUMMARY_DATE,
        workflow_status="READY",
        review_status="APPROVED",
        wordpress_status=local_status,
        wordpress_post_id="301",
    )
    item.offers.append(
        StoreOffer(
            store_name="rakuten_kobo",
            store_item_id="rk-1",
            affiliate_url="https://example.com/kobo",
        )
    )
    session.add(item)
    session.add(
        DailySummarySelection(
            ebook_item_id="item-1",
            summary_date=SUMMARY_DATE,
            inclusion_state="AUTO_INCLUDED",
            selection_source="AUTO",
            selected_by="auto",
        )
    )
    session.flush()


def test_zero_selected_items_blocks_generation(session: Session) -> None:
    service = DailySummaryWordPressDraftService(
        session, wordpress_client=FakeWordPressClient()
    )
    with pytest.raises(DailySummaryDraftError):
        service.execute(summary_date=SUMMARY_DATE, dry_run=True)


def test_local_unpublished_item_blocks_before_remote_call(session: Session) -> None:
    add_selected_item(session, local_status="DRAFT")
    service = DailySummaryWordPressDraftService(
        session, wordpress_client=FakeWordPressClient()
    )
    with pytest.raises(DailySummaryDraftError) as exc_info:
        service.execute(summary_date=SUMMARY_DATE, dry_run=True)
    assert "ローカル状態不整合" in exc_info.value.warnings[0]


def test_remote_non_publish_blocks_generation(session: Session) -> None:
    add_selected_item(session)
    service = DailySummaryWordPressDraftService(
        session, wordpress_client=FakeWordPressClient(item_status="future")
    )
    with pytest.raises(DailySummaryDraftError) as exc_info:
        service.execute(summary_date=SUMMARY_DATE, dry_run=True)
    assert any("未公開" in warning for warning in exc_info.value.warnings)


def test_dry_run_saves_preview_without_wordpress_post(session: Session) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)
    preview = service.execute(summary_date=SUMMARY_DATE, dry_run=True)
    assert preview.generation_allowed is True
    assert client.created == []
    assert client.updated == []
    run = service.run_repository.get_for_date(SUMMARY_DATE)
    assert run is not None
    assert run.execution_status == "PREVIEWED"
    assert session.query(DailySummaryRunHistory).count() == 1


def test_first_live_execution_creates_only_a_draft(session: Session) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)
    service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    assert len(client.created) == 1
    assert client.created[0]["status"] == "draft"
    assert "date" not in client.created[0]
    run = service.run_repository.get_for_date(SUMMARY_DATE)
    assert run is not None
    assert run.wordpress_post_id == "900"
    assert run.execution_status == "SUCCEEDED"


def test_same_input_does_not_post_twice(session: Session) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)
    service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    assert len(client.created) == 1
    assert client.updated == []


def test_changed_input_updates_existing_draft(session: Session) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)
    service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    item = session.get(EbookItem, "item-1")
    assert item is not None
    item.title = "新刊A 改訂"
    session.flush()

    service.execute(summary_date=SUMMARY_DATE, dry_run=False)

    assert len(client.created) == 1
    assert len(client.updated) == 1
    assert client.updated[0][0] == 900


def test_transport_failure_is_persisted_and_retry_is_blocked(session: Session) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    client.create_error = True
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)

    with pytest.raises(RuntimeError):
        service.execute(summary_date=SUMMARY_DATE, dry_run=False)

    run = service.run_repository.get_for_date(SUMMARY_DATE)
    assert run is not None
    assert run.execution_status == "FAILED"
    client.create_error = False
    with pytest.raises(DailySummaryDraftError) as exc_info:
        service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    assert exc_info.value.code == "reconciliation_required"
    assert client.created == []


@pytest.mark.parametrize("status", ["future", "publish", "trash"])
def test_existing_non_draft_summary_is_never_updated(session: Session, status: str) -> None:
    add_selected_item(session)
    client = FakeWordPressClient()
    service = DailySummaryWordPressDraftService(session, wordpress_client=client)
    service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    client.summary_status = status
    with pytest.raises(DailySummaryDraftError):
        service.execute(summary_date=SUMMARY_DATE, dry_run=False)
    assert client.updated == []