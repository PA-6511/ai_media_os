from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import DailySummarySelection, EbookItem
from app.services.daily_summary_selection_service import (
    AUTO_INCLUDED,
    HUMAN_INCLUDED,
)


INCLUDED_STATES = frozenset({AUTO_INCLUDED, HUMAN_INCLUDED})


def safe_https_url(value: Any) -> str | None:
    normalized = str(value or "").strip()
    parsed = urlsplit(normalized)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username:
        return None
    return normalized


@dataclass(frozen=True)
class DailySummaryItem:
    ebook_item_id: str
    release_date: date
    title: str
    volume_label: str
    author_name: str
    publisher_name: str
    is_excluded: bool
    workflow_status: str
    review_status: str
    wordpress_status: str
    wordpress_post_id: str
    inclusion_state: str | None
    kindle_url: str | None
    rakuten_kobo_url: str | None
    dmm_url: str | None
    image_url: str | None = None
    internal_url: str | None = None
    remote_status: str | None = None

    @property
    def selected(self) -> bool:
        return self.inclusion_state in INCLUDED_STATES

    @property
    def three_store_complete(self) -> bool:
        return all((self.kindle_url, self.rakuten_kobo_url, self.dmm_url))

    @property
    def locally_generation_ready(self) -> bool:
        return bool(
            not self.is_excluded
            and self.workflow_status == "READY"
            and self.review_status == "APPROVED"
            and self.wordpress_status == "PUBLISHED"
            and self.wordpress_post_id
        )


@dataclass(frozen=True)
class DailySummarySnapshot:
    summary_date: date
    items: tuple[DailySummaryItem, ...]
    target_count: int
    selected_count: int
    published_count: int
    unpublished_count: int
    three_store_complete_count: int
    link_missing_count: int
    inconsistent_count: int
    error_count: int

    @property
    def selected_items(self) -> tuple[DailySummaryItem, ...]:
        return tuple(item for item in self.items if item.selected)

    @property
    def generation_allowed_locally(self) -> bool:
        return self.selected_count > 0 and self.inconsistent_count == 0


class DailySummaryQueryService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_snapshot(self, summary_date: date) -> DailySummarySnapshot:
        selections = {
            selection.ebook_item_id: selection.inclusion_state
            for selection in self.session.scalars(
                select(DailySummarySelection).where(
                    DailySummarySelection.summary_date == summary_date
                )
            )
        }
        records = self.session.scalars(
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.release_date == summary_date)
            .order_by(
                EbookItem.release_date,
                EbookItem.title,
                EbookItem.volume_label,
                EbookItem.id,
            )
        ).all()
        items: list[DailySummaryItem] = []
        for item in records:
            urls: dict[str, str | None] = {
                "amazon": None,
                "rakuten_kobo": None,
                "dmm": None,
            }
            for offer in sorted(item.offers, key=lambda value: (value.store_name, value.id)):
                if offer.store_name in urls and urls[offer.store_name] is None:
                    urls[offer.store_name] = safe_https_url(offer.affiliate_url)
            items.append(
                DailySummaryItem(
                    ebook_item_id=item.id,
                    release_date=summary_date,
                    title=item.title,
                    volume_label=item.volume_label or "",
                    author_name=item.author_name or "",
                    publisher_name=item.publisher_name or "",
                    is_excluded=item.is_excluded,
                    workflow_status=item.workflow_status,
                    review_status=item.review_status,
                    wordpress_status=item.wordpress_status,
                    wordpress_post_id=str(item.wordpress_post_id or "").strip(),
                    inclusion_state=selections.get(item.id),
                    kindle_url=urls["amazon"],
                    rakuten_kobo_url=urls["rakuten_kobo"],
                    dmm_url=urls["dmm"],
                )
            )
        selected = [item for item in items if item.selected]
        inconsistent = [item for item in selected if not item.locally_generation_ready]
        published = [
            item
            for item in items
            if item.wordpress_status == "PUBLISHED" and item.wordpress_post_id
        ]
        return DailySummarySnapshot(
            summary_date=summary_date,
            items=tuple(items),
            target_count=len(items),
            selected_count=len(selected),
            published_count=len(published),
            unpublished_count=len(items) - len(published),
            three_store_complete_count=sum(item.three_store_complete for item in selected),
            link_missing_count=sum(not item.three_store_complete for item in selected),
            inconsistent_count=len(inconsistent),
            error_count=sum(bool(item.is_excluded or item.workflow_status == "ERROR") for item in selected),
        )

    @staticmethod
    def with_remote_values(
        item: DailySummaryItem,
        *,
        remote_status: str,
        internal_url: str | None,
        affiliate_meta: dict[str, str],
        image_url: str | None = None,
    ) -> DailySummaryItem:
        return replace(
            item,
            remote_status=remote_status,
            internal_url=safe_https_url(internal_url),
            kindle_url=safe_https_url(affiliate_meta.get("kindle_url")) or item.kindle_url,
            rakuten_kobo_url=(
                safe_https_url(affiliate_meta.get("rakuten_kobo_url"))
                or item.rakuten_kobo_url
            ),
            dmm_url=safe_https_url(affiliate_meta.get("dmm_url")) or item.dmm_url,
            image_url=safe_https_url(image_url),
        )