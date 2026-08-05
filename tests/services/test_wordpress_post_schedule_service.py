from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory
from app.services.wordpress_post_schedule_service import (
    WordPressPostScheduleError,
    WordPressPostScheduleExecutionStore,
    WordPressPostScheduleService,
)
from app.integrations.wordpress_rest_client import WordPressCategory


NOW = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self, status="draft", *, fail=False, omit_category=False, response_post_id=264):
        self.status = status
        self.fail = fail
        self.omit_category = omit_category
        self.response_post_id = response_post_id
        self.calls = []

    def get_post_state(self, *, post_id):
        self.calls.append(("get", post_id))
        if self.fail:
            raise RuntimeError("API failed safely")
        return SimpleNamespace(
            post_id=self.response_post_id,
            status=self.status,
            date="2026-08-02T20:30:00",
            date_gmt="2026-08-02T11:30:00",
            categories=(1,),
        )

    def list_categories(self, *, per_page):
        self.calls.append(("categories", per_page))
        return [WordPressCategory(43, "コミック新刊", "comic-new-release", 1)]

    def schedule_post(self, **payload):
        self.calls.append(("schedule", payload))
        if self.fail:
            raise RuntimeError("API failed safely")
        self.status = "future"
        return SimpleNamespace(
            status="future",
            date=payload["date"],
            date_gmt=payload["date_gmt"],
            categories=(
                ()
                if self.omit_category
                else ((payload.get("category_id"),) if payload.get("category_id") else (1,))
            ),
        )

    def update_category(self, **payload):
        self.calls.append(("update_category", payload))
        if self.fail:
            raise RuntimeError("API failed safely")
        return SimpleNamespace(
            post_id=payload["post_id"],
            status=self.status,
            categories=(payload["category_id"],),
        )

    def cancel_schedule(self, *, post_id):
        self.calls.append(("cancel", post_id))
        self.status = "draft"
        return SimpleNamespace(status="draft")


def make_session(tmp_path, *, status="DRAFT"):
    engine = create_engine(f"sqlite:///{tmp_path / 'schedule.db'}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    item = EbookItem(
        source_name="pytest",
        source_item_id="schedule-1",
        title="Schedule",
        item_type="tankobon",
        workflow_status="READY",
        review_status="APPROVED",
        wordpress_status=status,
        wordpress_post_id="264",
    )
    session.add(item)
    session.commit()
    return session, item


def service(session, tmp_path, client):
    return WordPressPostScheduleService(
        session,
        wordpress_client=client,
        execution_store=WordPressPostScheduleExecutionStore(tmp_path),
        now=lambda: NOW,
    )


@pytest.mark.parametrize("publish_at", ["2026-08-02T20:59", "2026-08-02T21:01"])
def test_past_or_within_sixty_seconds_does_not_call_api(tmp_path, publish_at):
    session, item = make_session(tmp_path)
    client = FakeClient()
    with pytest.raises(WordPressPostScheduleError) as error:
        service(session, tmp_path, client).schedule_post(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            publish_at_local=publish_at,
        )
    assert error.value.code == "publish_at_too_soon"
    assert client.calls == []


def test_schedule_converts_tokyo_to_utc_and_records_evidence(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    executor = service(session, tmp_path, client)
    result = executor.schedule_post(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        publish_at_local="2026-08-03T07:00",
    )
    session.refresh(item)
    assert result.publish_at_local == "2026-08-03T07:00:00+09:00"
    assert result.publish_at_utc == "2026-08-02T22:00:00+00:00"
    assert client.calls[1][1] == {
        "post_id": 264,
        "date": "2026-08-03T07:00:00",
        "date_gmt": "2026-08-02T22:00:00",
    }
    assert item.wordpress_status == "SCHEDULED"
    evidence = executor.execution_store.read_latest_success(item.id)
    assert evidence["operation"] == "SCHEDULE"
    assert evidence["completed"] is True
    assert evidence["success"] is True
    assert session.scalar(
        select(WorkflowHistory).where(WorkflowHistory.ebook_item_id == item.id)
    ).after_value == "SCHEDULED"


def test_api_failure_keeps_database_and_records_failure(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient(fail=True)
    executor = service(session, tmp_path, client)
    with pytest.raises(WordPressPostScheduleError) as error:
        executor.schedule_post(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            publish_at_local="2026-08-03T07:00",
        )
    session.refresh(item)
    assert item.wordpress_status == "DRAFT"
    assert error.value.evidence["completed"] is False
    assert error.value.evidence["operation"] == "SCHEDULE"
    assert "API failed safely" in error.value.evidence["wordpress_response_summary"]


def test_existing_claim_rejects_second_execution_before_api(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    store = WordPressPostScheduleExecutionStore(tmp_path)
    store.acquire(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        operation="SCHEDULE",
    )
    executor = WordPressPostScheduleService(
        session,
        wordpress_client=client,
        execution_store=store,
        now=lambda: NOW,
    )
    with pytest.raises(WordPressPostScheduleError) as error:
        executor.schedule_post(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            publish_at_local="2026-08-03T07:00",
        )
    assert error.value.code == "execution_claim_exists"
    assert client.calls == []


def test_reschedule_and_cancel_preserve_audit_chain(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    executor = service(session, tmp_path, client)
    executor.schedule_post(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        publish_at_local="2026-08-03T07:00",
    )
    client.status = "future"
    changed = executor.reschedule_post(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        publish_at_local="2026-08-03T08:00",
    )
    assert changed.operation == "RESCHEDULE"
    latest = executor.execution_store.read_latest_success(item.id)
    assert latest["old_publish_at"] == "2026-08-03T07:00:00+09:00"
    assert latest["new_publish_at"] == "2026-08-03T08:00:00+09:00"
    cancelled = executor.cancel_schedule(
        ebook_item_id=item.id,
        wordpress_post_id=264,
    )
    session.refresh(item)
    assert cancelled.operation == "CANCEL_SCHEDULE"
    assert item.wordpress_status == "DRAFT"
    latest = executor.execution_store.read_latest_success(item.id)
    assert latest["publish_at_local"] is None
    assert latest["previous_publish_at"] == "2026-08-03T08:00:00+09:00"


def test_unknown_category_is_rejected_before_claim_and_update(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    with pytest.raises(WordPressPostScheduleError) as error:
        service(session, tmp_path, client).schedule_post(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            category_id=999,
            publish_at_local="2026-08-03T07:00",
        )
    assert error.value.code == "category_not_found"
    assert client.calls == [("categories", 100)]


def test_schedule_with_category_is_atomic_and_audited(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    executor = service(session, tmp_path, client)
    result = executor.schedule_post(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        category_id=43,
        publish_at_local="2026-08-03T07:00",
    )
    schedule_call = next(call for call in client.calls if call[0] == "schedule")
    assert schedule_call[1]["category_id"] == 43
    assert result.operation == "SCHEDULE_WITH_CATEGORY"
    evidence = executor.execution_store.read_latest_success(item.id)
    assert evidence["previous_category_ids"] == [1]
    assert evidence["requested_category_id"] == 43
    assert evidence["confirmed_category_ids"] == [43]
    assert evidence["category_name"] == "コミック新刊"
    assert evidence["category_slug"] == "comic-new-release"


def test_category_update_preserves_draft_status(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient()
    executor = service(session, tmp_path, client)
    result = executor.update_category(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        category_id=43,
    )
    session.refresh(item)
    assert item.wordpress_status == "DRAFT"
    assert result.operation == "CATEGORY_UPDATE"
    assert result.previous_category_ids == (1,)
    assert result.confirmed_category_ids == (43,)


def test_future_post_category_can_be_updated(tmp_path):
    session, item = make_session(tmp_path, status="SCHEDULED")
    client = FakeClient(status="future")
    result = service(session, tmp_path, client).update_category(
        ebook_item_id=item.id,
        wordpress_post_id=264,
        category_id=43,
    )
    assert result.new_wordpress_status == "SCHEDULED"


def test_category_update_failure_does_not_change_schedule_state(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient(fail=True)
    with pytest.raises(WordPressPostScheduleError) as error:
        service(session, tmp_path, client).update_category(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            category_id=43,
        )
    session.refresh(item)
    assert item.wordpress_status == "DRAFT"
    assert error.value.evidence["completed"] is False
    assert error.value.evidence["success"] is False


def test_schedule_response_without_category_keeps_draft_state(tmp_path):
    session, item = make_session(tmp_path)
    client = FakeClient(omit_category=True)
    with pytest.raises(WordPressPostScheduleError) as error:
        service(session, tmp_path, client).schedule_post(
            ebook_item_id=item.id,
            wordpress_post_id=264,
            category_id=43,
            publish_at_local="2026-08-03T07:00",
        )
    session.refresh(item)
    assert error.value.code == "response_mismatch"
    assert item.wordpress_status == "DRAFT"
    assert error.value.evidence["requested_category_id"] == 43
    assert error.value.evidence["confirmed_category_ids"] == []


@pytest.mark.parametrize(
    ("remote_status", "local_status", "expected_status"),
    [
        ("future", "SCHEDULED", "SCHEDULED"),
        ("publish", "SCHEDULED", "PUBLISHED"),
        ("publish", "DRAFT", "PUBLISHED"),
    ],
)
def test_sync_remote_status_maps_confirmed_wordpress_state(
    tmp_path,
    remote_status,
    local_status,
    expected_status,
):
    session, item = make_session(tmp_path, status=local_status)
    executor = service(session, tmp_path, FakeClient(status=remote_status))

    result = executor.sync_remote_status(
        ebook_item_id=item.id,
        wordpress_post_id=264,
    )
    session.refresh(item)

    assert item.wordpress_status == expected_status
    assert result.remote_status == remote_status
    assert result.new_local_status == expected_status
    evidence = executor.execution_store.read_latest_success(item.id)
    assert evidence["operation"] == "SYNC_REMOTE_STATUS"
    assert evidence["wordpress_post_id"] == 264
    assert evidence["previous_local_status"] == local_status
    assert evidence["remote_status"] == remote_status
    assert evidence["new_local_status"] == expected_status
    assert evidence["remote_date"] == "2026-08-02T20:30:00"
    assert evidence["remote_date_gmt"] == "2026-08-02T11:30:00"
    assert evidence["checked_at"]
    assert evidence["success"] is True


def test_sync_rejects_response_post_id_mismatch_without_local_change(tmp_path):
    session, item = make_session(tmp_path, status="SCHEDULED")
    executor = service(
        session,
        tmp_path,
        FakeClient(status="publish", response_post_id=999),
    )

    with pytest.raises(WordPressPostScheduleError) as raised:
        executor.sync_remote_status(
            ebook_item_id=item.id,
            wordpress_post_id=264,
        )

    session.refresh(item)
    assert raised.value.code == "post_item_mismatch"
    assert item.wordpress_status == "SCHEDULED"
    assert raised.value.evidence["success"] is False


def test_sync_api_failure_keeps_local_status_and_records_failure(tmp_path):
    session, item = make_session(tmp_path, status="SCHEDULED")
    executor = service(session, tmp_path, FakeClient(fail=True))

    with pytest.raises(WordPressPostScheduleError) as raised:
        executor.sync_remote_status(
            ebook_item_id=item.id,
            wordpress_post_id=264,
        )

    session.refresh(item)
    assert item.wordpress_status == "SCHEDULED"
    assert raised.value.evidence["operation"] == "SYNC_REMOTE_STATUS"
    assert raised.value.evidence["success"] is False
    assert raised.value.evidence["new_local_status"] == "SCHEDULED"