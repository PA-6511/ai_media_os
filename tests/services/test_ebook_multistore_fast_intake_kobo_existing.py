from __future__ import annotations

from types import SimpleNamespace

import pytest


PRODUCT_URL = (
    "https://books.rakuten.co.jp/"
    "rk/17998a1e10563af9a969366f8dd0d13f/"
)

STORE_ITEM_ID = (
    "17998a1e10563af9a969366f8dd0d13f"
)


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ):
        return False

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@pytest.mark.parametrize(
    "mode",
    (
        "dry_run",
        "execute",
    ),
)
def test_identical_existing_kobo_offer_ends_before_write_services(
    monkeypatch,
    mode,
) -> None:
    import app.services.ebook_multistore_fast_intake_runner as target

    session = FakeSession()

    offer = SimpleNamespace(
        id="offer-existing",
        store_name="rakuten_kobo",
        store_item_id=STORE_ITEM_ID,
        product_url=PRODUCT_URL,
        affiliate_url=(
            "https://hb.afl.rakuten.co.jp/existing"
        ),
    )

    item = SimpleNamespace(
        id="item-published",
        wordpress_status="PUBLISHED",
        cover_status="AUTO_ALLOWED",
        offers=[offer],
    )

    monkeypatch.setattr(
        target,
        "SessionLocal",
        lambda: session,
    )

    monkeypatch.setattr(
        target,
        "_resolve_kobo_product_input",
        lambda *_: (
            PRODUCT_URL,
            "",
        ),
    )

    monkeypatch.setattr(
        target,
        "_find_existing_item",
        lambda *_args, **_kwargs: item,
    )

    monkeypatch.setattr(
        target,
        "_generate_kobo_affiliate_url",
        lambda *_: pytest.fail(
            "affiliate generation must not run"
        ),
    )

    class ForbiddenManualStoreOfferService:
        def __init__(self, _session):
            pytest.fail(
                "offer service must not run"
            )

    monkeypatch.setattr(
        target,
        "ManualStoreOfferService",
        ForbiddenManualStoreOfferService,
    )

    monkeypatch.setattr(
        target,
        "_reconcile_kobo_cover",
        lambda *_: pytest.fail(
            "cover reconcile must not run"
        ),
    )

    result = (
        target.run_multistore_fast_intake(
            store_name="kobo",
            product_input=PRODUCT_URL,
            title="既存公開済み作品",
            mode=mode,
        )
    )

    payload = result["payload"]

    assert payload["status"] == "EXISTING"
    assert payload["created"] is False

    assert (
        payload["ebook_item_id"]
        == "item-published"
    )

    assert (
        payload["offer_id"]
        == "offer-existing"
    )

    assert (
        payload["canonical_store_item_id"]
        == STORE_ITEM_ID
    )

    assert (
        payload["product_url"]
        == PRODUCT_URL
    )

    assert (
        payload["cover_status"]
        == "AUTO_ALLOWED"
    )

    assert session.commits == 0
    assert session.rollbacks == 1
