from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)


def test_set_wordpress_post_id_avoids_workflow_history_value_path(
    monkeypatch,
) -> None:
    flush_calls = []

    def forbidden_set_value(*args, **kwargs):
        raise AssertionError(
            "_set_value must not be used for wordpress_post_id"
        )

    monkeypatch.setattr(
        WorkflowStateRepository,
        "_set_value",
        forbidden_set_value,
    )

    repository = object.__new__(
        WorkflowStateRepository
    )

    repository.session = SimpleNamespace(
        no_autoflush=nullcontext(),
        scalar=lambda _statement: None,
        flush=lambda: flush_calls.append("flush"),
    )

    item = SimpleNamespace(
        id="x-r13-item-321",
        wordpress_post_id=None,
        last_checked_at=None,
        wordpress_updated_at=None,
    )

    changed = repository.set_wordpress_post_id(
        item,
        321,
        changed_by="pytest:x-r13",
        note="draft created",
    )

    assert changed is True
    assert item.wordpress_post_id == "321"
    assert item.last_checked_at is not None
    assert item.wordpress_updated_at is not None
    assert flush_calls == ["flush"]



@pytest.mark.parametrize("value", [True, 0, -1, "", "0", "abc"])
def test_set_wordpress_post_id_rejects_invalid_values(value) -> None:
    repository = object.__new__(WorkflowStateRepository)

    with pytest.raises(ValueError, match="positive integer"):
        repository.set_wordpress_post_id(
            SimpleNamespace(wordpress_post_id=None),
            value,
            changed_by="pytest:x-r13",
        )


def test_mark_wordpress_draft_created_updates_id_and_status(monkeypatch) -> None:
    calls = []

    def fake_set_post_id(
        self,
        item,
        post_id,
        *,
        changed_by,
        note,
    ):
        calls.append(("post_id", post_id, changed_by, note))
        return True

    def fake_set_status(
        self,
        item,
        status,
        *,
        changed_by,
        note,
    ):
        calls.append(("status", status, changed_by, note))
        return True

    monkeypatch.setattr(
        WorkflowStateRepository,
        "set_wordpress_post_id",
        fake_set_post_id,
    )
    monkeypatch.setattr(
        WorkflowStateRepository,
        "set_wordpress_status",
        fake_set_status,
    )

    repository = object.__new__(WorkflowStateRepository)
    item = SimpleNamespace()

    changed = repository.mark_wordpress_draft_created(
        item,
        777,
        changed_by="pytest:x-r13",
        note="draft created",
    )

    assert changed is True
    assert calls == [
        ("post_id", 777, "pytest:x-r13", "draft created"),
        ("status", "DRAFT", "pytest:x-r13", "draft created"),
    ]
