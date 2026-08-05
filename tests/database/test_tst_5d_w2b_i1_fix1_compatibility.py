from __future__ import annotations

import importlib.util
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]

FIX1_SOURCE = (
    ROOT
    / "exchange"
    / "candidates"
    / "slack_worker_release_rebinding"
    / "slack-worker-CANDIDATE-NOT-APPROVED-01ba8809f133"
    / "tst-5d-w2b-i1-fix1"
    / "workflow_state_repository_fix1_candidate.py"
)


def _load_candidate():
    spec = importlib.util.spec_from_file_location(
        "tst_5d_w2b_i1_fix1_compat_repository",
        FIX1_SOURCE,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


candidate = _load_candidate()


def test_fix1_preserves_no_history_helper_path(
    monkeypatch,
) -> None:
    flush_calls: list[str] = []

    def forbidden_set_value(*_args, **_kwargs):
        raise AssertionError(
            "_set_value must not be used for wordpress_post_id"
        )

    monkeypatch.setattr(
        candidate.WorkflowStateRepository,
        "_set_value",
        forbidden_set_value,
    )

    repository = object.__new__(
        candidate.WorkflowStateRepository
    )

    repository.session = SimpleNamespace(
        no_autoflush=nullcontext(),
        scalar=lambda _statement: None,
        flush=lambda: flush_calls.append("flush"),
    )

    item = SimpleNamespace(
        id="item-fix1-321",
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


@pytest.mark.parametrize(
    "value",
    [True, 0, -1, "", "0", "abc"],
)
def test_fix1_rejects_invalid_value_before_identity_access(
    value,
) -> None:
    repository = object.__new__(
        candidate.WorkflowStateRepository
    )

    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        repository.set_wordpress_post_id(
            SimpleNamespace(
                wordpress_post_id=None
            ),
            value,
            changed_by="pytest:x-r13",
        )


def test_fix1_valid_binding_requires_persisted_item() -> None:
    repository = object.__new__(
        candidate.WorkflowStateRepository
    )

    with pytest.raises(
        candidate.WordPressPostIdItemNotPersistedError,
        match="persisted ebook item ID",
    ):
        repository.set_wordpress_post_id(
            SimpleNamespace(
                wordpress_post_id=None
            ),
            "321",
            changed_by="pytest:x-r13",
        )


def test_fix1_same_id_is_no_op_before_identity_access() -> None:
    repository = object.__new__(
        candidate.WorkflowStateRepository
    )

    changed = repository.set_wordpress_post_id(
        SimpleNamespace(
            wordpress_post_id="321"
        ),
        "321",
        changed_by="pytest:x-r13",
    )

    assert changed is False
