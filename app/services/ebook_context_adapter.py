from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.new_release_wordpress_draft_lite import WordPressStoreOffer

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import EbookItem
from app.services.ebook_context import (
    EbookAffiliate,
    EbookContext,
    EbookCover,
    EbookDisplayCover,
    EbookIdentity,
    EbookPublication,
    EbookStore,
    EbookX,
)
from app.services.display_cover_resolver import DisplayCover, DisplayCoverResolver


class EbookContextAdapter:
    """Read an existing EbookItem into the Package 1A context contract."""

    def __init__(
        self, session: Session, *, wordpress_base_url: str | None = None,
        wordpress_offers_by_item_id: Mapping[str, tuple[WordPressStoreOffer, ...]] | None = None,
    ) -> None:
        self._session = session
        self._wordpress_base_url = wordpress_base_url
        self._wordpress_offers_by_item_id = wordpress_offers_by_item_id or {}

    def get(self, ebook_item_id: str) -> EbookContext | None:
        """Return a context for one item without mutating the supplied session."""
        with self._session.no_autoflush:
            item = self._session.scalar(
                select(EbookItem)
                .options(selectinload(EbookItem.offers))
                .where(EbookItem.id == ebook_item_id)
            )
        if item is None:
            return None
        return self.from_items((item,))[item.id]

    def from_items(self, items: Sequence[EbookItem]) -> dict[str, EbookContext]:
        """Adapt loaded items using one batch of resolved display covers."""
        with self._session.no_autoflush:
            display_covers = DisplayCoverResolver(self._session).resolve_many(items)
            return {
                item.id: self.from_item(
                    item, display_cover=display_covers.get(item.id),
                    article_url=self._article_url(item),
                    wordpress_offers=self._wordpress_offers_by_item_id.get(item.id),
                )
                for item in items
            }

    def _article_url(self, item: EbookItem) -> str | None:
        if self._wordpress_base_url is None or item.wordpress_post_id is None:
            return None
        from app.services.workflow_approved_x_draft_read_service import build_wordpress_article_url

        return build_wordpress_article_url(
            wordpress_base_url=self._wordpress_base_url,
            wordpress_post_id=item.wordpress_post_id,
        )

    @staticmethod
    def from_item(
        item: EbookItem,
        *,
        display_cover: DisplayCover | None = None,
        article_url: str | None = None,
        wordpress_offers: tuple[WordPressStoreOffer, ...] | None = None,
    ) -> EbookContext:
        stores = tuple(
            EbookStore(
                name=offer.store_name,
                item_id=offer.store_item_id,
                product_url=offer.product_url,
                affiliate_url=offer.affiliate_url,
                availability_status=offer.availability_status,
            )
            for offer in sorted(
                item.offers,
                key=lambda offer: (offer.store_name, offer.store_item_id, offer.id),
            )
        )
        return EbookContext(
            identity=EbookIdentity(
                id=item.id,
                source_name=item.source_name,
                source_item_id=item.source_item_id,
                isbn=item.isbn,
            ),
            title=item.title,
            author_name=item.author_name,
            item_type=item.item_type,
            publisher_name=item.publisher_name,
            wordpress_offers=wordpress_offers,
            volume=item.volume_label,
            release=item.release_date,
            stores=stores,
            cover=EbookCover(
                source=item.cover_source,
                source_item_id=item.cover_source_item_id,
                image_url=item.cover_image_url,
                destination_url=item.cover_destination_url,
                status=item.cover_status,
            ),
            affiliate=EbookAffiliate(status=item.affiliate_status),
            publication=EbookPublication(
                workflow_status=item.workflow_status,
                review_status=item.review_status,
                publish_ready=item.publish_ready,
                wordpress_status=item.wordpress_status,
                wordpress_post_id=item.wordpress_post_id,
                article_url=article_url,
            ),
            x=EbookX(status=item.x_status, post_id=item.x_post_id),
            display_cover=(
                EbookDisplayCover(
                    url=display_cover.display_cover_url,
                    source=display_cover.display_cover_source,
                    status=display_cover.display_cover_status,
                    reason=display_cover.display_cover_reason,
                    candidate_count=display_cover.candidate_count,
                )
                if display_cover is not None
                else None
            ),
        )
