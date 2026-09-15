"""Pure shadow comparison for the Daily Roundup's existing cover gate."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.ebook_context import EbookContext
from app.services.ebook_new_release_autonomy_consumer import (
    build_new_release_autonomy_input,
)


@dataclass(frozen=True)
class CoverGateDecision:
    status: str


@dataclass(frozen=True)
class CoverGateDifference:
    field: str
    legacy: object
    context: object


@dataclass(frozen=True)
class CoverGateShadowResult:
    status: str
    legacy_gate: CoverGateDecision | None
    context_gate: CoverGateDecision | None
    differences: tuple[CoverGateDifference, ...]


def evaluate_cover_gate_image_url(image_url: object) -> CoverGateDecision:
    """Apply the same URL predicate used by the current shell Cover Gate."""
    value = str(image_url or "").strip()
    parsed = urlparse(value)
    is_placeholder = any(
        marker in value.lower()
        for marker in ("noimage", "no-image", "no_image")
    )
    return CoverGateDecision(
        "PASS"
        if parsed.scheme == "https" and parsed.netloc and not is_placeholder
        else "BLOCK"
    )


def compare_legacy_cover_gate_to_context(
    legacy_item: Mapping[str, object] | None,
    context: EbookContext | None,
) -> CoverGateShadowResult:
    """Compare legacy and Context image facts without changing gate behavior."""
    if not isinstance(legacy_item, Mapping):
        return _not_comparable()
    item_id = legacy_item.get("item_id")
    if not isinstance(item_id, str) or not item_id.strip() or "image_url" not in legacy_item:
        return _not_comparable()

    context_item = build_new_release_autonomy_input(context)
    if context_item is None:
        return _not_comparable()

    legacy_url = str(legacy_item.get("image_url") or "").strip()
    context_url = str(context_item.get("image_url") or "").strip()
    legacy_gate = evaluate_cover_gate_image_url(legacy_url)
    context_gate = evaluate_cover_gate_image_url(context_url)
    differences: list[CoverGateDifference] = []
    if legacy_url != context_url:
        differences.append(CoverGateDifference("image_url", legacy_url, context_url))
    if legacy_gate.status != context_gate.status:
        differences.append(
            CoverGateDifference("gate.status", legacy_gate.status, context_gate.status)
        )
    return CoverGateShadowResult(
        "MISMATCH" if differences else "MATCH",
        legacy_gate,
        context_gate,
        tuple(differences),
    )


def _not_comparable() -> CoverGateShadowResult:
    return CoverGateShadowResult("NOT_COMPARABLE", None, None, ())
