from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import threading

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    StoreOffer,
    WorkflowApprovalRequest,
    WorkflowHistory,
)
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)
from app.integrations.wordpress_rest_client import WordPressDraftResponse
from app.services.wordpress_draft_execution_service import (
    COMPLETED,
    FAILED_PRE_EXTERNAL,
    OUTCOME_UNKNOWN,
    RECONCILIATION_REQUIRED,
    WordPressDraftExecutionError,
    WordPressDraftExecutionStore,
    execute_approved_wordpress_draft_once,
)


def build_item(**overrides):
    values = {
        "id": "ebook-1",
        "source_item_id": "example-20260717-001",
        "title": "サンプル作品",
        "volume_label": "",
        "author_name": "sample author",
        "publisher_name": "sample publisher",
        "release_date": "2026-07-17",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
        "x_status": "NOT_CREATED",
        "publish_ready": False,
        "is_excluded": False,
        "offers": ["unchanged-offer"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_approval(**overrides):
    values = {
        "id": "approval-1",
        "ebook_item_id": "ebook-1",
        "approval_type": "REVIEW_READY",
        "status": "APPROVED",
        "decided_at": datetime.now(timezone.utc),
        "expected_current_status": "REVIEW",
        "requested_status": "READY",
        "decision_note": "unchanged-approval",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_offer(**overrides):
    values = {
        "store_name": "rakuten_kobo",
        "store_item_id": "4310000000001",
        "affiliate_url": "https://example.test/affiliate",
        "product_url": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeClient:
    def __init__(self, *, error=None, post_id=321):
        self.error = error
        self.post_id = post_id
        self.payloads = []
        self.get_calls = []
        self.upload_calls = []
        self.update_calls = []

    def create_draft(self, payload):
        self.payloads.append(dict(payload))
        if self.error is not None:
            raise self.error
        return WordPressDraftResponse(
            post_id=self.post_id,
            status="draft",
            link=f"https://wordpress.test/?p={self.post_id}",
        )

    def get_draft(self, *, post_id):
        self.get_calls.append(post_id)
        return WordPressDraftResponse(
            post_id=post_id,
            status="draft",
            link=f"https://wordpress.test/?p={post_id}",
        )


class FakeStateRepository:
    def __init__(self):
        self.calls = []

    def mark_wordpress_draft_created(
        self,
        item,
        post_id,
        *,
        changed_by,
        note,
    ):
        self.calls.append((item.id, post_id, changed_by, note))
        item.wordpress_post_id = str(post_id)
        item.wordpress_status = "DRAFT"
        return True


def execute(
    tmp_path,
    *,
    item=None,
    approval=None,
    offer=None,
    client=None,
    repository=None,
    commit=None,
    rollback=None,
    store=None,
    cover_fetcher=None,
):
    arguments = {
        "ebook_item_id": "ebook-1",
        "item": item or build_item(),
        "approval_request": approval or build_approval(),
        "offer": offer or build_offer(),
        "wordpress_client": client or FakeClient(),
        "state_repository": repository or FakeStateRepository(),
        "commit": commit or (lambda: None),
        "rollback": rollback or (lambda: None),
        "execution_store": store or WordPressDraftExecutionStore(tmp_path),
    }
    if cover_fetcher is not None:
        arguments["cover_fetcher"] = cover_fetcher
    return execute_approved_wordpress_draft_once(**arguments)


def test_approved_request_creates_one_draft_and_preserves_other_state(tmp_path):
    item = build_item()
    approval = build_approval()
    offer = build_offer()
    client = FakeClient()
    repository = FakeStateRepository()
    before = {
        "workflow_status": item.workflow_status,
        "review_status": item.review_status,
        "publish_ready": item.publish_ready,
        "x_status": item.x_status,
        "offers": list(item.offers),
        "approval_status": approval.status,
        "approval_note": approval.decision_note,
    }

    result = execute(
        tmp_path,
        item=item,
        approval=approval,
        offer=offer,
        client=client,
        repository=repository,
    )

    assert result.wordpress_post_id == 321
    assert item.wordpress_status == "DRAFT"
    assert item.wordpress_post_id == "321"
    assert client.payloads[0]["status"] == "draft"
    assert "publish" not in client.payloads[0].values()
    assert before == {
        "workflow_status": item.workflow_status,
        "review_status": item.review_status,
        "publish_ready": item.publish_ready,
        "x_status": item.x_status,
        "offers": item.offers,
        "approval_status": approval.status,
        "approval_note": approval.decision_note,
    }
    evidence = WordPressDraftExecutionStore(tmp_path).read_for_item("ebook-1")
    assert evidence["status"] == COMPLETED
    assert evidence["wordpress_post_id"] == 321
    assert evidence["database_update_result"] == "COMMITTED"
    assert evidence["publish_executed"] is False


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"workflow_status": "REVIEW"}, "workflow_status must be READY"),
        ({"review_status": "NOT_REVIEWED"}, "review_status must be APPROVED"),
        ({"is_excluded": True}, "excluded ebook item"),
        ({"publish_ready": True}, "publish_ready must remain false"),
        ({"wordpress_status": "DRAFT"}, "wordpress_status must be NOT_CREATED"),
        ({"wordpress_post_id": "99"}, "draft already exists"),
    ],
)
def test_invalid_item_state_is_rejected_before_claim_and_transport(
    tmp_path,
    overrides,
    message,
):
    client = FakeClient()
    store = WordPressDraftExecutionStore(tmp_path)
    with pytest.raises(WordPressDraftExecutionError, match=message):
        execute(
            tmp_path,
            item=build_item(**overrides),
            client=client,
            store=store,
        )
    assert client.payloads == []
    assert store.read_for_item("ebook-1") is None


@pytest.mark.parametrize("status", ["PENDING", "REJECTED", "EXPIRED"])
def test_nonapproved_request_is_rejected(tmp_path, status):
    client = FakeClient()
    with pytest.raises(
        WordPressDraftExecutionError,
        match="approval request status must be APPROVED",
    ):
        execute(
            tmp_path,
            approval=build_approval(status=status),
            client=client,
        )
    assert client.payloads == []


def test_missing_decided_at_and_other_item_approval_are_rejected(tmp_path):
    client = FakeClient()
    with pytest.raises(WordPressDraftExecutionError, match="decided_at"):
        execute(
            tmp_path / "missing",
            approval=build_approval(decided_at=None),
            client=client,
        )
    with pytest.raises(WordPressDraftExecutionError, match="does not belong"):
        execute(
            tmp_path / "other",
            approval=build_approval(ebook_item_id="ebook-2"),
            client=client,
        )
    assert client.payloads == []


def test_invalid_offer_is_rejected_before_claim(tmp_path):
    client = FakeClient()
    with pytest.raises(WordPressDraftExecutionError, match="must use HTTPS"):
        execute(
            tmp_path,
            offer=build_offer(affiliate_url="http://example.test"),
            client=client,
        )
    assert client.payloads == []


def test_sequential_duplicate_is_blocked_after_success(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    first_client = FakeClient()
    execute(tmp_path, client=first_client, store=store)

    second_client = FakeClient()
    with pytest.raises(
        WordPressDraftExecutionError,
        match="already claimed",
    ):
        execute(tmp_path, client=second_client, store=store)

    assert len(first_client.payloads) == 1
    assert second_client.payloads == []


def test_concurrent_duplicate_allows_exactly_one_transport(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    entered = threading.Event()
    release = threading.Event()
    transport_count = 0
    count_lock = threading.Lock()

    class BlockingClient(FakeClient):
        def create_draft(self, payload):
            nonlocal transport_count
            with count_lock:
                transport_count += 1
            entered.set()
            assert release.wait(timeout=5)
            return super().create_draft(payload)

    def first_run():
        return execute(
            tmp_path,
            client=BlockingClient(),
            store=store,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first_run)
        assert entered.wait(timeout=5)
        second_future = pool.submit(
            execute,
            tmp_path,
            client=FakeClient(),
            store=store,
        )
        with pytest.raises(WordPressDraftExecutionError):
            second_future.result(timeout=5)
        release.set()
        assert first_future.result(timeout=5).wordpress_post_id == 321

    assert transport_count == 1


def test_external_response_is_persisted_before_database_commit(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    seen = {}

    def commit():
        seen.update(store.read_for_item("ebook-1"))

    execute(tmp_path, store=store, commit=commit)

    assert seen["status"] == RECONCILIATION_REQUIRED
    assert seen["wordpress_post_id"] == 321
    assert seen["wordpress_status"] == "draft"
    assert seen["database_update_result"] == "PENDING"


def test_commit_failure_requires_reconciliation_and_blocks_retry(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    rollback_calls = []
    client = FakeClient(post_id=876)

    with pytest.raises(
        WordPressDraftExecutionError,
        match=RECONCILIATION_REQUIRED,
    ):
        execute(
            tmp_path,
            client=client,
            store=store,
            commit=lambda: (_ for _ in ()).throw(RuntimeError("commit failed")),
            rollback=lambda: rollback_calls.append("rollback"),
        )

    evidence = store.read_for_item("ebook-1")
    assert evidence["status"] == RECONCILIATION_REQUIRED
    assert evidence["wordpress_post_id"] == 876
    assert evidence["database_update_result"] == "FAILED"
    assert "commit failed" in evidence["error"]
    assert rollback_calls == ["rollback"]

    retry_client = FakeClient()
    with pytest.raises(WordPressDraftExecutionError, match="already claimed"):
        execute(tmp_path, client=retry_client, store=store)
    assert len(client.payloads) == 1
    assert retry_client.payloads == []


def test_transport_error_after_call_started_is_outcome_unknown_and_blocks(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    client = FakeClient(error=RuntimeError("timeout"))

    with pytest.raises(WordPressDraftExecutionError, match=OUTCOME_UNKNOWN):
        execute(tmp_path, client=client, store=store)

    evidence = store.read_for_item("ebook-1")
    assert evidence["status"] == OUTCOME_UNKNOWN
    assert evidence["external_post_attempted"] is True
    assert evidence["external_post_succeeded"] is False

    retry_client = FakeClient()
    with pytest.raises(WordPressDraftExecutionError):
        execute(tmp_path, client=retry_client, store=store)
    assert retry_client.payloads == []


def test_invalid_offer_is_rejected_before_claim(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    client = FakeClient()
    with pytest.raises(
        WordPressDraftExecutionError,
        match="store_item_id is required",
    ):
        execute(
            tmp_path,
            offer=build_offer(store_item_id=""),
            client=client,
            store=store,
        )
    assert store.read_for_item("ebook-1") is None
    assert client.payloads == []


def test_claim_is_followed_by_fresh_database_revalidation(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    client = FakeClient()

    def refresh_current_state():
        return (
            build_item(is_excluded=True),
            build_approval(),
            build_offer(),
        )

    with pytest.raises(
        WordPressDraftExecutionError,
        match="current database state failed pre-external revalidation",
    ):
        execute_approved_wordpress_draft_once(
            ebook_item_id="ebook-1",
            item=build_item(),
            approval_request=build_approval(),
            offer=build_offer(),
            wordpress_client=client,
            state_repository=FakeStateRepository(),
            commit=lambda: None,
            rollback=lambda: None,
            execution_store=store,
            refresh_current_state=refresh_current_state,
        )

    evidence = store.read_for_item("ebook-1")
    assert evidence["status"] == FAILED_PRE_EXTERNAL
    assert evidence["external_post_attempted"] is False
    assert client.payloads == []


def test_image_failure_is_recorded_after_base_draft_commit(tmp_path):
    store = WordPressDraftExecutionStore(tmp_path)
    client = FakeClient()

    def fail_cover(**kwargs):
        raise RuntimeError("cover fetch failed")

    result = execute(
        tmp_path,
        offer=build_offer(
            product_url="https://books.rakuten.co.jp/rk/example/"
        ),
        client=client,
        store=store,
        cover_fetcher=fail_cover,
    )

    assert result.status == "DRAFT_CREATED_IMAGE_REVIEW_REQUIRED"
    assert result.image_status == "REVIEW_REQUIRED"
    evidence = store.read_for_item("ebook-1")
    assert evidence["status"] == COMPLETED
    assert evidence["image_status"] == "REVIEW_REQUIRED"
    assert evidence["wordpress_post_id"] == 321


def create_database_fixture(tmp_path, filename="wordpress-draft.db"):
    engine = create_engine(f"sqlite:///{tmp_path / filename}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    now = datetime.now(timezone.utc)
    item = EbookItem(
        id="ebook-1",
        source_name="pytest",
        source_item_id="example-20260717-001",
        title="サンプル作品",
        item_type="tankobon",
        workflow_status="READY",
        review_status="APPROVED",
        wordpress_status="NOT_CREATED",
        wordpress_post_id=None,
        x_status="NOT_CREATED",
        publish_ready=False,
        is_excluded=False,
    )
    offer = StoreOffer(
        ebook_item=item,
        store_name="rakuten_kobo",
        store_item_id="4310000000001",
        affiliate_url="https://example.test/affiliate",
    )
    approval = WorkflowApprovalRequest(
        id="approval-1",
        ebook_item_id="ebook-1",
        approval_type="REVIEW_READY",
        expected_current_status="REVIEW",
        requested_status="READY",
        status="APPROVED",
        request_nonce_hash="a" * 64,
        requested_by="pytest",
        requested_at=now - timedelta(minutes=5),
        expires_at=now + timedelta(minutes=55),
        decided_by="pytest",
        decided_at=now,
        decision_note="unchanged-approval",
    )
    session.add_all([item, offer, approval])
    session.commit()
    return session, item, offer, approval


def test_temporary_database_updates_only_wordpress_state_and_history(tmp_path):
    session, item, offer, approval = create_database_fixture(tmp_path)
    store = WordPressDraftExecutionStore(tmp_path / "artifacts")
    try:
        execute_approved_wordpress_draft_once(
            ebook_item_id=item.id,
            item=item,
            approval_request=approval,
            offer=offer,
            wordpress_client=FakeClient(post_id=555),
            state_repository=WorkflowStateRepository(session),
            commit=session.commit,
            rollback=session.rollback,
            execution_store=store,
        )
        session.expire_all()
        stored = session.get(EbookItem, "ebook-1")
        assert stored.wordpress_status == "DRAFT"
        assert stored.wordpress_post_id == "555"
        assert stored.workflow_status == "READY"
        assert stored.review_status == "APPROVED"
        assert stored.publish_ready is False
        assert stored.x_status == "NOT_CREATED"
        assert session.scalar(select(func.count(StoreOffer.id))) == 1
        stored_approval = session.get(WorkflowApprovalRequest, "approval-1")
        assert stored_approval.status == "APPROVED"
        assert stored_approval.decision_note == "unchanged-approval"
        histories = session.scalars(select(WorkflowHistory)).all()
        assert [history.field_name for history in histories] == [
            "wordpress_status",
            "image_status",
        ]
        assert histories[0].before_value == "NOT_CREATED"
        assert histories[0].after_value == "DRAFT"
        assert histories[1].before_value == "UNCHECKED"
        assert histories[1].after_value == "REVIEW"
    finally:
        session.close()


def test_temporary_database_commit_failure_rolls_back_state_and_history(tmp_path):
    session, item, offer, approval = create_database_fixture(
        tmp_path,
        "wordpress-draft-failure.db",
    )
    store = WordPressDraftExecutionStore(tmp_path / "failure-artifacts")

    def fail_commit():
        raise RuntimeError("simulated commit failure")

    try:
        with pytest.raises(WordPressDraftExecutionError):
            execute_approved_wordpress_draft_once(
                ebook_item_id=item.id,
                item=item,
                approval_request=approval,
                offer=offer,
                wordpress_client=FakeClient(post_id=556),
                state_repository=WorkflowStateRepository(session),
                commit=fail_commit,
                rollback=session.rollback,
                execution_store=store,
            )
        session.expire_all()
        stored = session.get(EbookItem, "ebook-1")
        assert stored.wordpress_status == "NOT_CREATED"
        assert stored.wordpress_post_id is None
        assert session.scalar(select(func.count(WorkflowHistory.id))) == 0
        evidence = store.read_for_item("ebook-1")
        assert evidence["status"] == RECONCILIATION_REQUIRED
        assert evidence["wordpress_post_id"] == 556
    finally:
        session.close()
