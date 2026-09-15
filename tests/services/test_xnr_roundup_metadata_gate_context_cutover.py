from __future__ import annotations

from datetime import datetime

import pytest

import app.services.xnr_roundup_candidate_projection as projection
from app.services.xnr_roundup_metadata_gate import (
    XnrRoundupMetadataGateError,
    select_roundup_candidates,
)


def payload():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-09-14T09:00:00+09:00",
        "new_releases": [{"item_id": "one", "title": "legacy"}],
    }


def projected_item(item_id="one"):
    return {
        "item_id": item_id,
        "approval_state": "APPROVED",
        "title": "Context title",
        "release_date": "2026-09-14",
        "stores": {"kindle": {"url": "https://affiliate.example/one"}},
        "image_url": "https://images.example/one.jpg",
    }


class ReadOnlySession:
    committed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def commit(self):
        self.committed = True
        raise AssertionError("commit must not be called")


def install_context_path(monkeypatch, *, context=object(), projection_result=None):
    session = ReadOnlySession()
    calls = []

    class Adapter:
        def __init__(self, supplied_session):
            assert supplied_session is session

        def get(self, item_id):
            calls.append(item_id)
            return context

    monkeypatch.setattr(projection, "ReadOnlySessionLocal", lambda: session)
    monkeypatch.setattr(projection, "EbookContextAdapter", Adapter)
    monkeypatch.setattr(
        projection,
        "build_new_release_autonomy_input",
        lambda supplied_context: projection_result if supplied_context is context else None,
    )
    return session, calls


def test_uses_context_projection_as_candidate_facts(monkeypatch):
    _session, calls = install_context_path(monkeypatch, projection_result=projected_item())

    result = projection.build_context_candidate_payload(payload())

    assert calls == ["one"]
    assert result["new_releases"] == [projected_item()]
    assert result["schema_version"] == "1.0"
    assert result["generated_at"] == "2026-09-14T09:00:00+09:00"


def test_existing_candidate_rules_receive_context_projection(monkeypatch):
    install_context_path(monkeypatch, projection_result=projected_item())

    selection = select_roundup_candidates(
        projection.build_context_candidate_payload(payload()),
        target_date="2026-09-14",
        max_items=2,
        now=datetime.fromisoformat("2026-09-14T09:05:00+09:00"),
    )

    assert selection.candidate_ids == ("one",)


@pytest.mark.parametrize("context,projection_result", [
    (None, projected_item()),
    (object(), None),
])
def test_unavailable_context_projection_blocks_without_legacy_fallback(
    monkeypatch, context, projection_result
):
    install_context_path(monkeypatch, context=context, projection_result=projection_result)

    with pytest.raises(XnrRoundupMetadataGateError) as error:
        projection.build_context_candidate_payload(payload())

    assert error.value.code == "CONTEXT_CANDIDATE_UNAVAILABLE"


def test_missing_legacy_item_id_blocks_before_context_lookup(monkeypatch):
    _session, calls = install_context_path(monkeypatch, projection_result=projected_item())
    source = payload()
    source["new_releases"] = [{}]

    with pytest.raises(XnrRoundupMetadataGateError) as error:
        projection.build_context_candidate_payload(source)

    assert error.value.code == "CONTEXT_CANDIDATE_UNAVAILABLE"
    assert calls == []


def test_context_identity_mismatch_blocks_candidate(monkeypatch):
    install_context_path(monkeypatch, projection_result=projected_item("other"))

    with pytest.raises(XnrRoundupMetadataGateError) as error:
        projection.build_context_candidate_payload(payload())

    assert error.value.code == "CONTEXT_CANDIDATE_UNAVAILABLE"


def test_malformed_legacy_entry_does_not_restore_legacy_payload(monkeypatch):
    install_context_path(monkeypatch, projection_result=projected_item())
    source = payload()
    source["new_releases"] = ["not-an-item"]

    with pytest.raises(XnrRoundupMetadataGateError) as error:
        projection.build_context_candidate_payload(source)

    assert error.value.code == "CONTEXT_CANDIDATE_UNAVAILABLE"
