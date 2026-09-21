from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.db.models import EbookItem, StoreOffer
from app.services.rakuten_comic_calendar_parser import (
    split_title_volume_imprint,
)
from app.services.supplement_candidate_match_service import (
    normalize_match_title,
    normalize_volume,
)


MONTHLY_SOURCE_NAME = "new_release_multistore"
UNPUBLISHED_WORDPRESS_STATUS = "NOT_CREATED"


class CanonicalIdentityAmbiguousError(RuntimeError):
    pass


def canonical_series_volume(
    title: str,
    volume_label: str | None = None,
) -> tuple[str, str | None]:
    (
        parsed_series,
        parsed_volume,
        _imprint,
        _warnings,
    ) = split_title_volume_imprint(
        str(title or "")
    )

    series_key = normalize_match_title(
        parsed_series
    )

    volume_key = (
        normalize_volume(volume_label)
        or normalize_volume(parsed_volume)
    )

    return (
        series_key,
        volume_key,
    )


def find_reusable_monthly_placeholders(
    *,
    title: str,
    items: Iterable[Any],
) -> tuple[Any, ...]:
    candidate_key = canonical_series_volume(
        title
    )

    candidate_series, candidate_volume = (
        candidate_key
    )

    if not candidate_series or not candidate_volume:
        return ()

    matches = []

    for item in items:
        if (
            str(
                getattr(
                    item,
                    "source_name",
                    "",
                )
                or ""
            )
            != MONTHLY_SOURCE_NAME
        ):
            continue

        if (
            str(
                getattr(
                    item,
                    "wordpress_status",
                    "",
                )
                or ""
            )
            != UNPUBLISHED_WORDPRESS_STATUS
        ):
            continue

        offers = tuple(
            getattr(
                item,
                "offers",
                (),
            )
            or ()
        )

        if offers:
            continue

        existing_key = canonical_series_volume(
            str(
                getattr(
                    item,
                    "title",
                    "",
                )
                or ""
            ),
            getattr(
                item,
                "volume_label",
                None,
            ),
        )

        if existing_key == candidate_key:
            matches.append(item)

    return tuple(matches)


def find_reusable_monthly_placeholder(
    *,
    title: str,
    items: Iterable[Any],
):
    matches = find_reusable_monthly_placeholders(
        title=title,
        items=items,
    )

    return (
        matches[0]
        if len(matches) == 1
        else None
    )

def find_existing_fast_intake_item(
    session,
    *,
    store_name: str,
    store_item_id: str = "",
    product_url: str = "",
    title: str,
):
    """Resolve an existing EbookItem without network or persistence."""

    identities = []

    if store_item_id:
        identities.append(
            StoreOffer.store_item_id
            == store_item_id
        )

    if product_url:
        identities.append(
            StoreOffer.product_url
            == product_url
        )

    if identities:
        item = session.scalar(
            select(EbookItem)
            .join(StoreOffer)
            .where(
                StoreOffer.store_name
                == store_name,
                or_(*identities),
            )
            .limit(1)
        )

        if item is not None:
            return item

    exact_item = session.scalar(
        select(EbookItem)
        .where(
            or_(
                EbookItem.title == title,
                EbookItem.normalized_title
                == title,
            )
        )
        .order_by(
            EbookItem.created_at.desc()
        )
        .limit(1)
    )

    if exact_item is not None:
        return exact_item

    monthly_candidates = tuple(
        session.scalars(
            select(EbookItem)
            .options(
                selectinload(
                    EbookItem.offers
                )
            )
            .where(
                EbookItem.source_name
                == MONTHLY_SOURCE_NAME,
                EbookItem.wordpress_status
                == UNPUBLISHED_WORDPRESS_STATUS,
            )
        )
    )

    canonical_matches = (
        find_reusable_monthly_placeholders(
            title=title,
            items=monthly_candidates,
        )
    )

    if len(canonical_matches) > 1:
        raise CanonicalIdentityAmbiguousError(
            "CANONICAL_IDENTITY_AMBIGUOUS"
        )

    return (
        canonical_matches[0]
        if canonical_matches
        else None
    )
