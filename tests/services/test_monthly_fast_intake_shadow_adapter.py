from types import SimpleNamespace

import pytest

from app.services.monthly_fast_intake_shadow_adapter import (
    build_monthly_fast_intake_shadow_handoff,
    normalize_fast_intake_store_name,
)


def offer(
    *,
    offer_id="offer-1",
    store_name="rakuten_kobo",
    product_url="",
    store_item_id="",
):
    return SimpleNamespace(
        id=offer_id,
        store_name=store_name,
        product_url=product_url,
        store_item_id=store_item_id,
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("rakuten_kobo", "kobo"),
        ("kobo", "kobo"),
        ("amazon", "amazon"),
        ("kindle", "amazon"),
        ("dmm", "dmm"),
    ],
)
def test_normalize_store_name(
    source,
    expected,
):
    assert (
        normalize_fast_intake_store_name(
            source
        )
        == expected
    )


def test_kobo_prefers_product_url():
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name="rakuten_kobo",
            offers=[
                offer(
                    product_url=(
                        "https://books.rakuten.co.jp/"
                        "rk/example/"
                    ),
                    store_item_id="1234567890123",
                )
            ],
        )
    )

    assert result.status == "READY"
    assert result.ready is True
    assert result.offer_id == "offer-1"

    assert (
        result.fast_intake_store_name
        == "kobo"
    )

    assert result.product_input == (
        "https://books.rakuten.co.jp/"
        "rk/example/"
    )

    assert result.to_fast_intake_input() == {
        "store_name": "kobo",
        "product_input": (
            "https://books.rakuten.co.jp/"
            "rk/example/"
        ),
        "title": "Book 1",
    }


@pytest.mark.parametrize(
    ("db_store", "fast_store"),
    [
        ("dmm", "dmm"),
        ("amazon", "amazon"),
    ],
)
def test_supported_store_handoff(
    db_store,
    fast_store,
):
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name=db_store,
            offers=[
                offer(
                    store_name=db_store,
                    product_url=(
                        "https://example.invalid/item"
                    ),
                    store_item_id="id-1",
                )
            ],
        )
    )

    assert result.status == "READY"

    assert (
        result.fast_intake_store_name
        == fast_store
    )


def test_store_item_id_is_fallback_identity():
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name="dmm",
            offers=[
                offer(
                    store_name="dmm",
                    store_item_id="dmm-item-1",
                )
            ],
        )
    )

    assert result.status == "READY"
    assert result.product_input == "dmm-item-1"


def test_no_offer_is_not_ready():
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name="rakuten_kobo",
            offers=[],
        )
    )

    assert result.status == "NO_OFFER"
    assert result.ready is False

    with pytest.raises(
        ValueError,
        match="HANDOFF_NOT_READY",
    ):
        result.to_fast_intake_input()


def test_multiple_same_store_offers_are_ambiguous():
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name="rakuten_kobo",
            offers=[
                offer(
                    offer_id="offer-1",
                    product_url="https://example/1",
                ),
                offer(
                    offer_id="offer-2",
                    product_url="https://example/2",
                ),
            ],
        )
    )

    assert (
        result.status
        == "AMBIGUOUS_OFFERS"
    )

    assert (
        result.reason_code
        == "MULTIPLE_STORE_OFFERS"
    )


def test_missing_identity_is_not_ready():
    result = (
        build_monthly_fast_intake_shadow_handoff(
            ebook_item_id="item-1",
            title="Book 1",
            database_store_name="amazon",
            offers=[
                offer(
                    store_name="amazon",
                )
            ],
        )
    )

    assert (
        result.status
        == "IDENTITY_MISSING"
    )

    assert (
        result.reason_code
        == "STORE_IDENTITY_MISSING"
    )


def test_unsupported_store_rejected():
    with pytest.raises(
        ValueError,
        match="UNSUPPORTED_STORE",
    ):
        normalize_fast_intake_store_name(
            "unknown-store"
        )



def test_collect_shadow_handoffs_three_stores(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    calls = []

    def fake_load(
        session,
        *,
        ebook_item_id,
        store_name,
    ):
        calls.append(
            (
                ebook_item_id,
                store_name,
            )
        )

        return (
            adapter.MonthlyFastIntakeShadowHandoff(
                status="READY",
                ebook_item_id=ebook_item_id,
                offer_id=(
                    "offer-"
                    + store_name
                ),
                database_store_name=(
                    store_name
                ),
                fast_intake_store_name=(
                    adapter
                    .normalize_fast_intake_store_name(
                        store_name
                    )
                ),
                product_input=(
                    "input-"
                    + store_name
                ),
                title=(
                    "title-"
                    + ebook_item_id
                ),
            )
        )

    monkeypatch.setattr(
        adapter,
        "load_monthly_fast_intake_shadow_handoff",
        fake_load,
    )

    result = (
        adapter
        .collect_monthly_fast_intake_shadow_handoffs(
            object(),
            {
                "rakuten_kobo": [
                    {
                        "ebook_item_id":
                            "item-kobo",
                        "status": "SAVED",
                    }
                ],
                "dmm": [
                    {
                        "ebook_item_id":
                            "item-dmm",
                        "status": "FOUND",
                    }
                ],
                "kindle": [
                    {
                        "ebook_item_id":
                            "item-amazon",
                        "status": "SAVED",
                    }
                ],
                "covers": [],
            },
        )
    )

    assert result["status"] == "OK"
    assert result["row_count"] == 3
    assert result["ready_count"] == 3

    assert calls == [
        (
            "item-kobo",
            "rakuten_kobo",
        ),
        (
            "item-dmm",
            "dmm",
        ),
        (
            "item-amazon",
            "amazon",
        ),
    ]

    assert (
        result["stores"]
        ["rakuten_kobo"]
        ["status_counts"]
        == {"READY": 1}
    )

    assert (
        result["stores"]
        ["dmm"]
        ["status_counts"]
        == {"READY": 1}
    )

    assert (
        result["stores"]
        ["kindle"]
        ["status_counts"]
        == {"READY": 1}
    )


def test_collect_shadow_handoff_missing_item_id(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    def fail_load(*args, **kwargs):
        raise AssertionError(
            "loader must not be called"
        )

    monkeypatch.setattr(
        adapter,
        "load_monthly_fast_intake_shadow_handoff",
        fail_load,
    )

    result = (
        adapter
        .collect_monthly_fast_intake_shadow_handoffs(
            object(),
            {
                "rakuten_kobo": [
                    {
                        "ebook_item_id": "",
                        "status": "FAILED",
                    }
                ],
                "dmm": [],
                "kindle": [],
            },
        )
    )

    assert result["row_count"] == 1
    assert result["ready_count"] == 0

    row = (
        result["stores"]
        ["rakuten_kobo"]
        ["rows"][0]
    )

    assert (
        row["shadow_status"]
        == "INVALID_ITEM_ID"
    )

    assert row["ready"] is False


class _IdentityStateSession:
    def __init__(
        self,
        *,
        item,
        offers,
    ):
        self.item = item
        self.offers = list(offers)

    def get(
        self,
        _model,
        _item_id,
    ):
        return self.item

    def scalars(
        self,
        _statement,
    ):
        return self.offers


def test_loaded_ready_handoff_resolves_to_existing_same_item(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    item = SimpleNamespace(
        id="item-existing",
        title="Book Existing",
    )

    saved_offer = offer(
        offer_id="offer-existing",
        store_name="rakuten_kobo",
        product_url=(
            "https://books.rakuten.co.jp/"
            "rk/existing/"
        ),
        store_item_id="2000000000001",
    )

    session = _IdentityStateSession(
        item=item,
        offers=[saved_offer],
    )

    calls = []

    def fake_resolve(
        session_arg,
        *,
        store_name,
        store_item_id,
        product_url,
        title,
    ):
        calls.append({
            "session": session_arg,
            "store_name": store_name,
            "store_item_id": store_item_id,
            "product_url": product_url,
            "title": title,
        })

        return item

    monkeypatch.setattr(
        adapter,
        "find_existing_fast_intake_item",
        fake_resolve,
    )

    result = (
        adapter
        .load_monthly_fast_intake_shadow_handoff(
            session,
            ebook_item_id="item-existing",
            store_name="rakuten_kobo",
        )
    )

    assert result.status == "READY"
    assert result.ready is True
    assert result.fast_intake_status == "EXISTING"
    assert (
        result.resolved_ebook_item_id
        == "item-existing"
    )
    assert result.identity_reason_code == ""

    assert len(calls) == 1
    assert calls[0]["session"] is session
    assert (
        calls[0]["store_name"]
        == "rakuten_kobo"
    )
    assert (
        calls[0]["store_item_id"]
        == "2000000000001"
    )
    assert calls[0]["product_url"] == (
        "https://books.rakuten.co.jp/"
        "rk/existing/"
    )


def test_loaded_ready_handoff_marks_owner_mismatch_review_required(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    item = SimpleNamespace(
        id="item-original",
        title="Book Original",
    )

    saved_offer = offer(
        offer_id="offer-original",
        store_name="dmm",
        product_url=(
            "https://book.dmm.com/"
            "product/original/"
        ),
        store_item_id="dmm-original",
    )

    session = _IdentityStateSession(
        item=item,
        offers=[saved_offer],
    )

    monkeypatch.setattr(
        adapter,
        "find_existing_fast_intake_item",
        lambda *_args, **_kwargs: (
            SimpleNamespace(
                id="item-other",
            )
        ),
    )

    result = (
        adapter
        .load_monthly_fast_intake_shadow_handoff(
            session,
            ebook_item_id="item-original",
            store_name="dmm",
        )
    )

    assert result.status == "READY"
    assert (
        result.fast_intake_status
        == "REVIEW_REQUIRED"
    )
    assert (
        result.resolved_ebook_item_id
        == "item-other"
    )
    assert (
        result.identity_reason_code
        == "CANONICAL_IDENTITY_OWNER_MISMATCH"
    )


def test_loaded_ready_handoff_marks_ambiguity_review_required(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    item = SimpleNamespace(
        id="item-ambiguous",
        title="Book Ambiguous",
    )

    saved_offer = offer(
        offer_id="offer-ambiguous",
        store_name="amazon",
        product_url=(
            "https://www.amazon.co.jp/"
            "dp/B0AMBIGUOUS"
        ),
        store_item_id="B0AMBIGUOUS",
    )

    session = _IdentityStateSession(
        item=item,
        offers=[saved_offer],
    )

    def raise_ambiguous(
        *_args,
        **_kwargs,
    ):
        raise (
            adapter
            .CanonicalIdentityAmbiguousError(
                "CANONICAL_IDENTITY_AMBIGUOUS"
            )
        )

    monkeypatch.setattr(
        adapter,
        "find_existing_fast_intake_item",
        raise_ambiguous,
    )

    result = (
        adapter
        .load_monthly_fast_intake_shadow_handoff(
            session,
            ebook_item_id="item-ambiguous",
            store_name="amazon",
        )
    )

    assert result.status == "READY"
    assert (
        result.fast_intake_status
        == "REVIEW_REQUIRED"
    )
    assert result.resolved_ebook_item_id == ""
    assert (
        result.identity_reason_code
        == "CANONICAL_IDENTITY_AMBIGUOUS"
    )


def test_non_ready_handoff_does_not_call_common_identity_resolver(
    monkeypatch,
):
    import app.services.monthly_fast_intake_shadow_adapter as adapter

    item = SimpleNamespace(
        id="item-no-offer",
        title="Book No Offer",
    )

    session = _IdentityStateSession(
        item=item,
        offers=[],
    )

    def fail_resolve(
        *_args,
        **_kwargs,
    ):
        raise AssertionError(
            "IDENTITY_RESOLVER_MUST_NOT_RUN"
        )

    monkeypatch.setattr(
        adapter,
        "find_existing_fast_intake_item",
        fail_resolve,
    )

    result = (
        adapter
        .load_monthly_fast_intake_shadow_handoff(
            session,
            ebook_item_id="item-no-offer",
            store_name="rakuten_kobo",
        )
    )

    assert result.status == "NO_OFFER"
    assert result.ready is False
    assert result.fast_intake_status == ""
    assert result.resolved_ebook_item_id == ""
    assert result.identity_reason_code == ""
