from __future__ import annotations

from pathlib import Path

import app.services.xnr_roundup_candidate_projection as projection


ROOT = Path(__file__).resolve().parents[1]


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


class _Adapter:
    def __init__(self, session):
        self.session = session

    def get(self, item_id):
        return {
            "item_id": item_id,
        }


def test_projection_does_not_mutate_input(
    monkeypatch,
):
    monkeypatch.setattr(
        projection,
        "ReadOnlySessionLocal",
        lambda: _SessionContext(),
    )

    monkeypatch.setattr(
        projection,
        "EbookContextAdapter",
        _Adapter,
    )

    monkeypatch.setattr(
        projection,
        "build_new_release_autonomy_input",
        lambda context: {
            "item_id": context["item_id"],
            "title": "Context title",
            "release_date": "2026-09-15",
            "approval_state": "APPROVED",
            "stores": {
                "rakuten_kobo": {
                    "url": (
                        "https://example.invalid/book"
                    ),
                },
            },
        },
    )

    original = {
        "schema_version": "1.0",
        "generated_at": (
            "2026-09-15T00:55:42+09:00"
        ),
        "new_releases": [
            {
                "item_id": "item-1",
                "title": "Legacy title",
            }
        ],
    }

    result = (
        projection.build_context_candidate_payload(
            original
        )
    )

    assert (
        original["new_releases"][0]["title"]
        == "Legacy title"
    )

    assert (
        result["new_releases"][0]["title"]
        == "Context title"
    )


def test_gate_uses_shared_projection():
    source = (
        ROOT
        / "scripts"
        / "check_xnr_roundup_metadata_gate.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "xnr_roundup_candidate_projection"
        in source
    )

    assert (
        "def build_context_candidate_payload("
        not in source
    )


def test_snapshot_uses_shared_projection():
    source = (
        ROOT
        / "scripts"
        / "run_daily_new_release_roundup_impl.sh"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "xnr_roundup_candidate_projection"
        in source
    )

    assert (
        "payload = build_context_candidate_payload("
        in source
    )

    projection_pos = source.index(
        "payload = build_context_candidate_payload("
    )

    selection_pos = source.index(
        "selection = select_roundup_candidates(",
        projection_pos,
    )

    assert projection_pos < selection_pos
