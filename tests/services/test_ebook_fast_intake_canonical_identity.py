from __future__ import annotations

from types import SimpleNamespace


def _item(
    *,
    item_id: str,
    title: str,
    volume_label: str,
    source_name: str = "new_release_multistore",
    wordpress_status: str = "NOT_CREATED",
    offers=(),
):
    return SimpleNamespace(
        id=item_id,
        title=title,
        normalized_title=title,
        volume_label=volume_label,
        source_name=source_name,
        wordpress_status=wordpress_status,
        offers=list(offers),
    )


def test_reuses_unique_monthly_placeholder_across_title_variants():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_reusable_monthly_placeholder,
    )

    existing = _item(
        item_id="monthly-orion-11",
        title="盤上のオリオン（11） (講談社コミックス)",
        volume_label="11",
    )

    result = find_reusable_monthly_placeholder(
        title="盤上のオリオン(11) (週刊少年マガジン)",
        items=[existing],
    )

    assert result is existing


def test_normalizes_dai_volume_label_and_bare_volume():
    from app.services.ebook_fast_intake_canonical_identity import (
        canonical_series_volume,
    )

    left = canonical_series_volume(
        "盤上のオリオン(11) (週刊少年マガジン)",
        "第11巻",
    )

    right = canonical_series_volume(
        "盤上のオリオン（11） (講談社コミックス)",
        "11",
    )

    assert left == right
    assert left == (
        "盤上のオリオン",
        "11",
    )


def test_does_not_reuse_published_item():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_reusable_monthly_placeholder,
    )

    existing = _item(
        item_id="published-orion-11",
        title="盤上のオリオン（11） (講談社コミックス)",
        volume_label="11",
        wordpress_status="PUBLISHED",
    )

    result = find_reusable_monthly_placeholder(
        title="盤上のオリオン(11) (週刊少年マガジン)",
        items=[existing],
    )

    assert result is None


def test_does_not_reuse_item_that_already_has_store_offer():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_reusable_monthly_placeholder,
    )

    existing = _item(
        item_id="offered-orion-11",
        title="盤上のオリオン（11） (講談社コミックス)",
        volume_label="11",
        offers=[
            SimpleNamespace(
                store_name="amazon",
            )
        ],
    )

    result = find_reusable_monthly_placeholder(
        title="盤上のオリオン(11) (週刊少年マガジン)",
        items=[existing],
    )

    assert result is None


def test_does_not_guess_when_multiple_placeholders_match():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_reusable_monthly_placeholder,
    )

    one = _item(
        item_id="one",
        title="作品名（3） (コミックス)",
        volume_label="3",
    )

    two = _item(
        item_id="two",
        title="作品名 3 (別コミックス)",
        volume_label="第3巻",
    )

    result = find_reusable_monthly_placeholder(
        title="作品名(3)",
        items=[one, two],
    )

    assert result is None


def test_does_not_match_different_volume():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_reusable_monthly_placeholder,
    )

    existing = _item(
        item_id="orion-10",
        title="盤上のオリオン（10） (講談社コミックス)",
        volume_label="10",
    )

    result = find_reusable_monthly_placeholder(
        title="盤上のオリオン(11) (週刊少年マガジン)",
        items=[existing],
    )

    assert result is None


class _IdentityResolverSession:
    def __init__(
        self,
        *,
        scalar_results,
        monthly_items=(),
    ):
        self.scalar_results = list(
            scalar_results
        )
        self.monthly_items = list(
            monthly_items
        )
        self.scalar_calls = 0
        self.scalars_calls = 0

    def scalar(self, _statement):
        self.scalar_calls += 1

        if not self.scalar_results:
            raise AssertionError(
                "UNEXPECTED_SCALAR_CALL"
            )

        return self.scalar_results.pop(0)

    def scalars(self, _statement):
        self.scalars_calls += 1
        return self.monthly_items


def test_session_resolver_prefers_exact_store_offer_identity():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_existing_fast_intake_item,
    )

    existing = SimpleNamespace(
        id="store-hit",
    )

    session = _IdentityResolverSession(
        scalar_results=[existing],
    )

    result = find_existing_fast_intake_item(
        session,
        store_name="rakuten_kobo",
        store_item_id="2000000000001",
        product_url="https://example.invalid/item",
        title="作品名 3",
    )

    assert result is existing
    assert session.scalar_calls == 1
    assert session.scalars_calls == 0


def test_session_resolver_falls_back_to_exact_title():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_existing_fast_intake_item,
    )

    exact_title = SimpleNamespace(
        id="title-hit",
    )

    session = _IdentityResolverSession(
        scalar_results=[
            None,
            exact_title,
        ],
    )

    result = find_existing_fast_intake_item(
        session,
        store_name="dmm",
        store_item_id="dmm-missing",
        product_url="",
        title="作品名 3",
    )

    assert result is exact_title
    assert session.scalar_calls == 2
    assert session.scalars_calls == 0


def test_session_resolver_falls_back_to_unique_monthly_placeholder():
    from app.services.ebook_fast_intake_canonical_identity import (
        find_existing_fast_intake_item,
    )

    monthly = _item(
        item_id="monthly-session-hit",
        title="作品名（3） (コミックス)",
        volume_label="3",
    )

    session = _IdentityResolverSession(
        scalar_results=[
            None,
            None,
        ],
        monthly_items=[
            monthly,
        ],
    )

    result = find_existing_fast_intake_item(
        session,
        store_name="rakuten_kobo",
        store_item_id="",
        product_url="https://example.invalid/missing",
        title="作品名 3",
    )

    assert result is monthly
    assert session.scalar_calls == 2
    assert session.scalars_calls == 1


def test_session_resolver_raises_for_ambiguous_monthly_placeholders():
    import pytest

    from app.services.ebook_fast_intake_canonical_identity import (
        CanonicalIdentityAmbiguousError,
        find_existing_fast_intake_item,
    )

    session = _IdentityResolverSession(
        scalar_results=[
            None,
            None,
        ],
        monthly_items=[
            _item(
                item_id="monthly-session-one",
                title="作品名（3） (コミックス)",
                volume_label="3",
            ),
            _item(
                item_id="monthly-session-two",
                title="作品名 3 (別コミックス)",
                volume_label="3",
            ),
        ],
    )

    with pytest.raises(
        CanonicalIdentityAmbiguousError,
        match="CANONICAL_IDENTITY_AMBIGUOUS",
    ):
        find_existing_fast_intake_item(
            session,
            store_name="rakuten_kobo",
            store_item_id="",
            product_url="https://example.invalid/missing",
            title="作品名(3)",
        )
