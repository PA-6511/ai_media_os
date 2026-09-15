"""Compare legacy new-release public items with their Context projections."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.services.ebook_context import EbookContext
from app.services.ebook_new_release_autonomy_consumer import (
    build_new_release_autonomy_input,
)
from integrations.wordpress.ebook_new_releases.scripts.export_ready_approved_new_releases import (
    STORE_KEYS,
)


@dataclass(frozen=True)
class NewReleaseAutonomyShadowResult:
    status: str
    differences: tuple["NewReleaseAutonomyDifference", ...]


@dataclass(frozen=True)
class NewReleaseAutonomyDifference:
    field: str
    legacy: object
    context: object


_REQUIRED_TEXT_FIELDS = ("item_id", "approval_state", "title", "release_date")
_COMPARE_FIELDS = (*_REQUIRED_TEXT_FIELDS, "image_url")


def compare_legacy_new_release_item_to_context(
    legacy_item: Mapping[str, object] | None,
    context: EbookContext | None,
) -> NewReleaseAutonomyShadowResult:
    """Return semantic field differences, or NOT_COMPARABLE for incomplete input."""
    context_item = build_new_release_autonomy_input(context)
    if not _is_comparable_legacy_item(legacy_item) or context_item is None:
        return NewReleaseAutonomyShadowResult("NOT_COMPARABLE", ())

    differences: list[NewReleaseAutonomyDifference] = []
    for field in _COMPARE_FIELDS:
        if legacy_item[field] != context_item[field]:
            differences.append(NewReleaseAutonomyDifference(
                field, legacy_item[field], context_item[field]
            ))

    legacy_stores = legacy_item["stores"]
    context_stores = context_item["stores"]
    assert isinstance(legacy_stores, Mapping)
    assert isinstance(context_stores, Mapping)
    for store_key in STORE_KEYS:
        legacy_url = legacy_stores[store_key]["url"]
        context_url = context_stores[store_key]["url"]
        if legacy_url != context_url:
            differences.append(NewReleaseAutonomyDifference(
                f"stores.{store_key}.url", legacy_url, context_url
            ))

    return NewReleaseAutonomyShadowResult(
        "MISMATCH" if differences else "MATCH",
        tuple(differences),
    )


def _is_comparable_legacy_item(item: Mapping[str, object] | None) -> bool:
    if not isinstance(item, Mapping):
        return False
    if any(not isinstance(item.get(field), str) or not item[field].strip() for field in _REQUIRED_TEXT_FIELDS):
        return False
    if not isinstance(item.get("image_url"), str):
        return False
    stores = item.get("stores")
    if not isinstance(stores, Mapping):
        return False
    for store_key in STORE_KEYS:
        store = stores.get(store_key)
        if not isinstance(store, Mapping) or not isinstance(store.get("url"), str):
            return False
    return True
