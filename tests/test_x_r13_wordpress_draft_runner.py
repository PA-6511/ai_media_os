from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
)
from app.services.x_r13_wordpress_draft_gate import (
    X13WordPressDraftGateError,
)
from scripts.run_x_r13_wordpress_draft_creation_once import (
    execute_x_r13_wordpress_draft_once,
)


def build_item(**overrides):
    values = {
        "id": "e2029b2f-f44a-462f-abc8-86c4bc74b818",
        "title": "メダリスト",
        "volume_label": "第15巻",
        "author_name": "つるまいかだ",
        "publisher_name": "講談社",
        "release_date": date(2026, 7, 22),
        "item_type": "tankobon",
        "workflow_status": "READY",
        "review_status": "APPROVED",
        "publish_ready": False,
        "wordpress_status": "NOT_CREATED",
        "wordpress_post_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_request(**overrides):
    values = {
        "status": "APPROVED",
        "approval_type": "REVIEW_READY",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def build_offer(**overrides):
    values = {
        "store_name": "rakuten_kobo",
        "store_item_id": "4310000887411",
        "affiliate_url": "https://example.test/affiliate",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeClient:
    def __init__(self) -> None:
        self.payloads = []

    def create_draft(self, payload):
        self.payloads.append(payload)
        return WordPressDraftResponse(
            post_id=777,
            status="draft",
            link="https://example.test/?p=777",
        )


class FakeStateRepository:
    def __init__(self) -> None:
        self.calls = []

    def mark_wordpress_draft_created(
        self,
        item,
        post_id,
        *,
        changed_by,
        note="",
    ):
        self.calls.append((item, post_id, changed_by, note))
        item.wordpress_post_id = str(post_id)
        item.wordpress_status = "DRAFT"
        return True


def test_execute_once_creates_draft_and_reconciles_state() -> None:
    item = build_item()
    client = FakeClient()
    state_repository = FakeStateRepository()
    events = []

    result = execute_x_r13_wordpress_draft_once(
        item=item,
        approval_request=build_request(),
        offer=build_offer(),
        client=client,
        state_repository=state_repository,
        commit=lambda: events.append("commit"),
        rollback=lambda: events.append("rollback"),
    )

    assert result.post_id == 777
    assert result.status == "draft"
    assert result.committed is True
    assert item.wordpress_post_id == "777"
    assert item.wordpress_status == "DRAFT"
    assert events == ["commit"]
    assert len(client.payloads) == 1
    assert client.payloads[0]["status"] == "draft"
    assert len(state_repository.calls) == 1


def test_gate_failure_blocks_transport_and_rolls_back() -> None:
    item = build_item(review_status="IN_REVIEW")
    client = FakeClient()
    state_repository = FakeStateRepository()
    events = []

    with pytest.raises(
        X13WordPressDraftGateError,
        match="review_status must be APPROVED",
    ):
        execute_x_r13_wordpress_draft_once(
            item=item,
            approval_request=build_request(),
            offer=build_offer(),
            client=client,
            state_repository=state_repository,
            commit=lambda: events.append("commit"),
            rollback=lambda: events.append("rollback"),
        )

    assert client.payloads == []
    assert state_repository.calls == []
    assert events == ["rollback"]


def test_existing_wordpress_post_blocks_transport() -> None:
    item = build_item(
        wordpress_status="DRAFT",
        wordpress_post_id="999",
    )
    client = FakeClient()
    events = []

    with pytest.raises(
        X13WordPressDraftGateError,
        match="wordpress_status must be NOT_CREATED",
    ):
        execute_x_r13_wordpress_draft_once(
            item=item,
            approval_request=build_request(),
            offer=build_offer(),
            client=client,
            state_repository=FakeStateRepository(),
            commit=lambda: events.append("commit"),
            rollback=lambda: events.append("rollback"),
        )

    assert client.payloads == []
    assert events == ["rollback"]
