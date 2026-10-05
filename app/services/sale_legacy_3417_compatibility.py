from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.services.sale_roundup_service import digest
from app.services.sale_store_policy import validate_sale_snapshot_store


LEGACY_3417_POST_ID = 3417
LEGACY_3417_CAMPAIGN_ID = (
    "rakuten-kobo-official-discount-341921-20261001"
)
LEGACY_3417_EXPERIMENT_ID = (
    "a028f0d31b6f7e1c895c4c140eba8008a98e9d2814d5e4a45902a5863771fcdf"
)
LEGACY_3417_FEATURED_MEDIA_ID = 3418
LEGACY_3417_CAMPAIGN_STORE = "rakuten_kobo"
LEGACY_3417_MARKER = (
    f"<!-- sale-roundup:{LEGACY_3417_EXPERIMENT_ID} -->"
)

_EXPECTED_PROVENANCE = {
    "source_type": "RAKUTEN_KOBO_OFFICIAL_MANIFEST",
    "verification_source": "kobo_official_campaign_source",
    "campaign_id": LEGACY_3417_CAMPAIGN_ID,
    "campaign_store": LEGACY_3417_CAMPAIGN_STORE,
}


@dataclass(frozen=True, slots=True)
class Legacy3417StoreContext:
    post_id: int
    campaign_id: str
    experiment_id: str
    existing_snapshot_hash: str
    marker: str
    featured_media_id: int
    campaign_store: str


def validate_legacy_3417_store_context(
    *,
    post_id,
    campaign_id,
    experiment_id,
    existing_snapshot,
    existing_snapshot_hash,
    marker,
    featured_media_id,
    campaign_store,
    provenance,
) -> Legacy3417StoreContext:
    """Validate only the fixed Post 3417 legacy identity without mutation."""
    identity = (
        post_id,
        campaign_id,
        experiment_id,
        existing_snapshot_hash,
        marker,
        featured_media_id,
        campaign_store,
    )
    expected_identity = (
        LEGACY_3417_POST_ID,
        LEGACY_3417_CAMPAIGN_ID,
        LEGACY_3417_EXPERIMENT_ID,
        LEGACY_3417_EXPERIMENT_ID,
        LEGACY_3417_MARKER,
        LEGACY_3417_FEATURED_MEDIA_ID,
        LEGACY_3417_CAMPAIGN_STORE,
    )
    if identity != expected_identity:
        raise ValueError("LEGACY_3417_IDENTITY_MISMATCH")

    if not isinstance(existing_snapshot, Mapping):
        raise ValueError("LEGACY_3417_SNAPSHOT_SHAPE_INVALID")
    if "campaign_store" in existing_snapshot:
        raise ValueError("LEGACY_3417_SNAPSHOT_SHAPE_INVALID")
    if existing_snapshot.get("campaign_id") != LEGACY_3417_CAMPAIGN_ID:
        raise ValueError("LEGACY_3417_IDENTITY_MISMATCH")

    if not isinstance(provenance, Mapping) or any(
        provenance.get(key) != value
        for key, value in _EXPECTED_PROVENANCE.items()
    ):
        raise ValueError("LEGACY_3417_PROVENANCE_MISMATCH")

    if digest(existing_snapshot) != existing_snapshot_hash:
        raise ValueError("LEGACY_3417_SNAPSHOT_HASH_MISMATCH")

    temporary_validation_snapshot = dict(existing_snapshot)
    temporary_validation_snapshot["campaign_store"] = campaign_store
    validate_sale_snapshot_store(temporary_validation_snapshot)

    return Legacy3417StoreContext(
        post_id=post_id,
        campaign_id=campaign_id,
        experiment_id=experiment_id,
        existing_snapshot_hash=existing_snapshot_hash,
        marker=marker,
        featured_media_id=featured_media_id,
        campaign_store=campaign_store,
    )


__all__ = [
    "Legacy3417StoreContext",
    "validate_legacy_3417_store_context",
]
