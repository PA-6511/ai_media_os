from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.new_release_wordpress_draft_lite import WordPressStoreOffer


@dataclass(frozen=True)
class EbookIdentity:
    id: str
    source_name: str
    source_item_id: str
    isbn: str | None


@dataclass(frozen=True)
class EbookStore:
    name: str
    item_id: str
    product_url: str | None
    affiliate_url: str | None
    availability_status: str | None


@dataclass(frozen=True)
class EbookCover:
    source: str | None
    source_item_id: str | None
    image_url: str | None
    destination_url: str | None
    status: str | None


@dataclass(frozen=True)
class EbookDisplayCover:
    url: str | None
    source: str
    status: str
    reason: str
    candidate_count: int = 0


@dataclass(frozen=True)
class EbookAffiliate:
    status: str | None


@dataclass(frozen=True)
class EbookPublication:
    workflow_status: str | None
    review_status: str | None
    publish_ready: bool
    wordpress_status: str | None
    wordpress_post_id: str | None
    article_url: str | None = None


@dataclass(frozen=True)
class EbookX:
    status: str | None
    post_id: str | None


@dataclass(frozen=True)
class EbookContext:
    identity: EbookIdentity
    title: str
    volume: str | None
    release: date | None
    stores: tuple[EbookStore, ...]
    cover: EbookCover
    affiliate: EbookAffiliate
    publication: EbookPublication
    x: EbookX
    display_cover: EbookDisplayCover | None = None
    author_name: str | None = None
    item_type: str | None = None
    publisher_name: str | None = None
    wordpress_offers: tuple[WordPressStoreOffer, ...] | None = None
