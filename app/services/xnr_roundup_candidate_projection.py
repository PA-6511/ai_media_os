"""Canonical XNR Roundup candidate projection."""

from __future__ import annotations

from typing import Any

from app.db.read_only_session import ReadOnlySessionLocal
from app.services.ebook_context_adapter import EbookContextAdapter
from app.services.ebook_new_release_autonomy_consumer import (
    build_new_release_autonomy_input,
)
from app.services.xnr_roundup_metadata_gate import (
    XnrRoundupMetadataGateError,
)


def build_context_candidate_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build canonical EbookContext-derived XNR candidate payload.

    The input payload is not mutated.
    """

    releases = payload.get("new_releases")

    if not isinstance(releases, list):
        raise XnrRoundupMetadataGateError(
            "CONTEXT_CANDIDATE_UNAVAILABLE",
            detail="new_releases must be a list",
        )

    projected_items: list[dict[str, object]] = []

    with ReadOnlySessionLocal() as session:
        adapter = EbookContextAdapter(session)

        for legacy_item in releases:
            if not isinstance(legacy_item, dict):
                raise XnrRoundupMetadataGateError(
                    "CONTEXT_CANDIDATE_UNAVAILABLE",
                    detail="public item must be an object",
                )

            item_id = str(
                legacy_item.get("item_id") or ""
            ).strip()

            if not item_id:
                raise XnrRoundupMetadataGateError(
                    "CONTEXT_CANDIDATE_UNAVAILABLE",
                    detail="public item has no item_id",
                )

            context = adapter.get(item_id)

            if context is None:
                raise XnrRoundupMetadataGateError(
                    "CONTEXT_CANDIDATE_UNAVAILABLE",
                    candidate_id=item_id,
                    detail="EbookContext is unavailable",
                )

            context_item = (
                build_new_release_autonomy_input(
                    context
                )
            )

            if context_item is None:
                raise XnrRoundupMetadataGateError(
                    "CONTEXT_CANDIDATE_UNAVAILABLE",
                    candidate_id=item_id,
                    detail="Context projection is unavailable",
                )

            if context_item.get("item_id") != item_id:
                raise XnrRoundupMetadataGateError(
                    "CONTEXT_CANDIDATE_UNAVAILABLE",
                    candidate_id=item_id,
                    detail=(
                        "Context identity does not match "
                        "public item identity"
                    ),
                )

            projected_items.append(
                context_item
            )

    context_payload = dict(payload)
    context_payload["new_releases"] = (
        projected_items
    )

    return context_payload
