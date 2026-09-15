"""Project an ``EbookContext`` to the legacy new-release autonomy item facts."""

from __future__ import annotations

from datetime import date

from app.services.ebook_context import EbookContext
from integrations.wordpress.ebook_new_releases.scripts.export_ready_approved_new_releases import (
    STORE_ALIASES,
    STORE_KEYS,
)


def build_new_release_autonomy_input(
    context: EbookContext | None,
) -> dict[str, object] | None:
    """Return comparable public-item facts without selecting or authorizing releases.

    The legacy exporter can order multiple database offers for one public store.
    Context intentionally does not expose that ordering, so an ambiguous mapping is
    unavailable instead of introducing a new selection rule here.
    """
    if context is None:
        return None

    item_id = context.identity.id
    title = context.title
    release_date = context.release
    approval_state = context.publication.review_status
    display_cover = context.display_cover
    if (
        not isinstance(item_id, str)
        or not item_id.strip()
        or not isinstance(title, str)
        or not title.strip()
        or not isinstance(release_date, date)
        or not isinstance(approval_state, str)
        or not approval_state.strip()
        or display_cover is None
    ):
        return None

    image_url = display_cover.url
    if image_url is None:
        image_url = ""
    if not isinstance(image_url, str):
        return None

    offers_by_store: dict[str, list[str]] = {store_key: [] for store_key in STORE_KEYS}
    for store in context.stores:
        store_name = store.name
        affiliate_url = store.affiliate_url
        if not isinstance(store_name, str) or not isinstance(affiliate_url, str):
            continue
        store_key = STORE_ALIASES.get(store_name.strip().lower())
        affiliate_url = affiliate_url.strip()
        if store_key is not None and affiliate_url:
            offers_by_store[store_key].append(affiliate_url)

    if any(len(offers) > 1 for offers in offers_by_store.values()):
        return None

    stores = {
        store_key: {"url": offers[0] if offers else ""}
        for store_key, offers in offers_by_store.items()
    }
    return {
        "item_id": item_id,
        "approval_state": approval_state,
        "title": title,
        "release_date": release_date.isoformat(),
        "stores": stores,
        "image_url": image_url,
    }
