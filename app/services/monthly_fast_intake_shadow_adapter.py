from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EbookItem, StoreOffer
from app.services.ebook_fast_intake_canonical_identity import (
    CanonicalIdentityAmbiguousError,
    find_existing_fast_intake_item,
)


_STORE_INPUT_NAMES = {
    "rakuten_kobo": "kobo",
    "kobo": "kobo",
    "amazon": "amazon",
    "kindle": "amazon",
    "dmm": "dmm",
}


@dataclass(frozen=True)
class MonthlyFastIntakeShadowHandoff:
    status: str
    ebook_item_id: str
    offer_id: str
    database_store_name: str
    fast_intake_store_name: str
    product_input: str
    title: str
    reason_code: str = ""
    fast_intake_status: str = ""
    resolved_ebook_item_id: str = ""
    identity_reason_code: str = ""

    @property
    def ready(self) -> bool:
        return self.status == "READY"

    def to_fast_intake_input(self) -> dict[str, str]:
        if not self.ready:
            raise ValueError(
                f"HANDOFF_NOT_READY:{self.status}"
            )

        return {
            "store_name": self.fast_intake_store_name,
            "product_input": self.product_input,
            "title": self.title,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ready"] = self.ready
        return payload


def normalize_fast_intake_store_name(
    store_name: str,
) -> str:
    normalized = str(
        store_name or ""
    ).strip().lower()

    try:
        return _STORE_INPUT_NAMES[normalized]
    except KeyError as exc:
        raise ValueError(
            f"UNSUPPORTED_STORE:{normalized}"
        ) from exc


def build_monthly_fast_intake_shadow_handoff(
    *,
    ebook_item_id: str,
    title: str,
    database_store_name: str,
    offers: list[Any],
) -> MonthlyFastIntakeShadowHandoff:
    item_id = str(
        ebook_item_id or ""
    ).strip()

    normalized_title = str(
        title or ""
    ).strip()

    db_store = str(
        database_store_name or ""
    ).strip().lower()

    fast_store = normalize_fast_intake_store_name(
        db_store
    )

    if not item_id:
        raise ValueError(
            "EBOOK_ITEM_ID_REQUIRED"
        )

    if not normalized_title:
        raise ValueError(
            "TITLE_REQUIRED"
        )

    matching = [
        offer
        for offer in offers
        if str(
            getattr(
                offer,
                "store_name",
                "",
            )
            or ""
        ).strip().lower()
        == db_store
    ]

    if not matching:
        return MonthlyFastIntakeShadowHandoff(
            status="NO_OFFER",
            ebook_item_id=item_id,
            offer_id="",
            database_store_name=db_store,
            fast_intake_store_name=fast_store,
            product_input="",
            title=normalized_title,
            reason_code="STORE_OFFER_NOT_FOUND",
        )

    if len(matching) > 1:
        return MonthlyFastIntakeShadowHandoff(
            status="AMBIGUOUS_OFFERS",
            ebook_item_id=item_id,
            offer_id="",
            database_store_name=db_store,
            fast_intake_store_name=fast_store,
            product_input="",
            title=normalized_title,
            reason_code="MULTIPLE_STORE_OFFERS",
        )

    offer = matching[0]

    offer_id = str(
        getattr(
            offer,
            "id",
            "",
        )
        or ""
    ).strip()

    product_url = str(
        getattr(
            offer,
            "product_url",
            "",
        )
        or ""
    ).strip()

    store_item_id = str(
        getattr(
            offer,
            "store_item_id",
            "",
        )
        or ""
    ).strip()

    product_input = (
        product_url
        or store_item_id
    )

    if not product_input:
        return MonthlyFastIntakeShadowHandoff(
            status="IDENTITY_MISSING",
            ebook_item_id=item_id,
            offer_id=offer_id,
            database_store_name=db_store,
            fast_intake_store_name=fast_store,
            product_input="",
            title=normalized_title,
            reason_code="STORE_IDENTITY_MISSING",
        )

    return MonthlyFastIntakeShadowHandoff(
        status="READY",
        ebook_item_id=item_id,
        offer_id=offer_id,
        database_store_name=db_store,
        fast_intake_store_name=fast_store,
        product_input=product_input,
        title=normalized_title,
    )


def resolve_monthly_fast_intake_shadow_identity_state(
    session: Session,
    *,
    handoff: MonthlyFastIntakeShadowHandoff,
    offer: Any,
) -> MonthlyFastIntakeShadowHandoff:
    """Attach common fast-intake identity state without network or writes."""

    if not handoff.ready:
        return handoff

    store_item_id = str(
        getattr(
            offer,
            "store_item_id",
            "",
        )
        or ""
    ).strip()

    product_url = str(
        getattr(
            offer,
            "product_url",
            "",
        )
        or ""
    ).strip()

    try:
        resolved = find_existing_fast_intake_item(
            session,
            store_name=handoff.database_store_name,
            store_item_id=store_item_id,
            product_url=product_url,
            title=handoff.title,
        )
    except CanonicalIdentityAmbiguousError:
        return replace(
            handoff,
            fast_intake_status="REVIEW_REQUIRED",
            resolved_ebook_item_id="",
            identity_reason_code=(
                "CANONICAL_IDENTITY_AMBIGUOUS"
            ),
        )

    if resolved is None:
        return replace(
            handoff,
            fast_intake_status="REVIEW_REQUIRED",
            resolved_ebook_item_id="",
            identity_reason_code=(
                "CANONICAL_IDENTITY_NOT_FOUND"
            ),
        )

    resolved_item_id = str(
        getattr(
            resolved,
            "id",
            "",
        )
        or ""
    ).strip()

    if resolved_item_id != handoff.ebook_item_id:
        return replace(
            handoff,
            fast_intake_status="REVIEW_REQUIRED",
            resolved_ebook_item_id=resolved_item_id,
            identity_reason_code=(
                "CANONICAL_IDENTITY_OWNER_MISMATCH"
            ),
        )

    return replace(
        handoff,
        fast_intake_status="EXISTING",
        resolved_ebook_item_id=resolved_item_id,
        identity_reason_code="",
    )


def load_monthly_fast_intake_shadow_handoff(
    session: Session,
    *,
    ebook_item_id: str,
    store_name: str,
) -> MonthlyFastIntakeShadowHandoff:
    item_id = str(
        ebook_item_id or ""
    ).strip()

    db_store = str(
        store_name or ""
    ).strip().lower()

    fast_store = normalize_fast_intake_store_name(
        db_store
    )

    item = session.get(
        EbookItem,
        item_id,
    )

    if item is None:
        return MonthlyFastIntakeShadowHandoff(
            status="ITEM_NOT_FOUND",
            ebook_item_id=item_id,
            offer_id="",
            database_store_name=db_store,
            fast_intake_store_name=fast_store,
            product_input="",
            title="",
            reason_code="EBOOK_ITEM_NOT_FOUND",
        )

    offers = list(
        session.scalars(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id == item.id,
                StoreOffer.store_name == db_store,
            )
        )
    )

    handoff = build_monthly_fast_intake_shadow_handoff(
        ebook_item_id=str(item.id),
        title=str(item.title or ""),
        database_store_name=db_store,
        offers=offers,
    )

    if not handoff.ready:
        return handoff

    return resolve_monthly_fast_intake_shadow_identity_state(
        session,
        handoff=handoff,
        offer=offers[0],
    )



_ENRICHMENT_STORE_TO_DATABASE_STORE = {
    "rakuten_kobo": "rakuten_kobo",
    "dmm": "dmm",
    "kindle": "amazon",
}


def collect_monthly_fast_intake_shadow_handoffs(
    session: Session,
    enrichment: dict[str, Any],
) -> dict[str, Any]:
    stores: dict[str, Any] = {}

    total_rows = 0
    ready_count = 0

    for (
        enrichment_store,
        database_store_name,
    ) in (
        _ENRICHMENT_STORE_TO_DATABASE_STORE.items()
    ):
        raw_entries = (
            enrichment.get(
                enrichment_store,
                [],
            )
            or []
        )

        rows: list[dict[str, Any]] = []
        status_counts: dict[str, int] = {}

        for raw_entry in raw_entries:
            total_rows += 1

            entry = (
                raw_entry
                if isinstance(
                    raw_entry,
                    dict,
                )
                else {}
            )

            ebook_item_id = str(
                entry.get(
                    "ebook_item_id"
                )
                or ""
            ).strip()

            source_status = str(
                entry.get(
                    "status"
                )
                or ""
            ).strip()

            if not ebook_item_id:
                shadow_status = (
                    "INVALID_ITEM_ID"
                )

                status_counts[
                    shadow_status
                ] = (
                    status_counts.get(
                        shadow_status,
                        0,
                    )
                    + 1
                )

                rows.append({
                    "ebook_item_id": "",
                    "source_status":
                        source_status,
                    "shadow_status":
                        shadow_status,
                    "ready": False,
                    "reason_code":
                        "EBOOK_ITEM_ID_MISSING",
                })

                continue

            handoff = (
                load_monthly_fast_intake_shadow_handoff(
                    session,
                    ebook_item_id=(
                        ebook_item_id
                    ),
                    store_name=(
                        database_store_name
                    ),
                )
            )

            handoff_payload = (
                handoff.to_dict()
            )

            shadow_status = (
                handoff.status
            )

            status_counts[
                shadow_status
            ] = (
                status_counts.get(
                    shadow_status,
                    0,
                )
                + 1
            )

            if handoff.ready:
                ready_count += 1

            rows.append({
                "source_status":
                    source_status,
                "shadow_status":
                    shadow_status,
                **handoff_payload,
            })

        stores[
            enrichment_store
        ] = {
            "database_store_name":
                database_store_name,
            "row_count":
                len(rows),
            "status_counts":
                status_counts,
            "rows":
                rows,
        }

    return {
        "status": "OK",
        "row_count": total_rows,
        "ready_count": ready_count,
        "stores": stores,
    }
