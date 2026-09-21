from __future__ import annotations

from types import SimpleNamespace

from app.services import (
    ebook_multistore_fast_intake_runner as target,
)


def _monthly(
    item_id: str,
    title: str,
):
    return SimpleNamespace(
        id=item_id,
        source_name="new_release_multistore",
        title=title,
        normalized_title=title,
        volume_label="3",
        wordpress_status="NOT_CREATED",
        offers=[],
    )


class FakeSession:
    def __init__(self):
        self.items = [
            _monthly(
                "monthly-one",
                "作品名（3） (コミックス)",
            ),
            _monthly(
                "monthly-two",
                "作品名 3 (別コミックス)",
            ),
        ]

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False

    def scalar(self, _statement):
        # StoreOffer identity lookup:
        #   miss
        #
        # Exact-title lookup:
        #   miss
        return None

    def scalars(self, _statement):
        # Canonical fallback:
        #   intentionally ambiguous.
        return self.items

    def rollback(self):
        return None

    def commit(self):
        raise AssertionError(
            "COMMIT_MUST_NOT_RUN"
        )


def _create_must_not_run(
    *_args,
    **_kwargs,
):
    raise AssertionError(
        "CREATE_MUST_NOT_RUN"
    )


def test_kobo_ambiguous_canonical_identity_returns_review_required(
    monkeypatch,
):
    monkeypatch.setattr(
        target,
        "SessionLocal",
        FakeSession,
    )

    monkeypatch.setattr(
        target,
        "_resolve_kobo_product_input",
        lambda _product, _title: (
            "https://books.rakuten.co.jp/"
            "rk/ambiguous-shadow/",
            "4310000000000",
        ),
    )

    monkeypatch.setattr(
        target,
        "_create_item",
        _create_must_not_run,
    )

    payload = target._kobo_intake(
        "4310000000000",
        "作品名(3)",
        "dry_run",
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["created"] is False


def test_dmm_ambiguous_canonical_identity_returns_review_required(
    monkeypatch,
):
    monkeypatch.setattr(
        target,
        "SessionLocal",
        FakeSession,
    )

    monkeypatch.setattr(
        target,
        "parse_dmm_input",
        lambda _value: SimpleNamespace(
            product_id="dmm-ambiguous",
            product_url=(
                "https://book.dmm.com/"
                "product/ambiguous/"
            ),
        ),
    )

    monkeypatch.setattr(
        target,
        "_create_item",
        _create_must_not_run,
    )

    payload = target._dmm_intake(
        "dmm-ambiguous",
        "作品名(3)",
        "dry_run",
    )

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["created"] is False
