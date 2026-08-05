from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EbookItem


class EbookRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_source_identity(
        self,
        *,
        source_name: str,
        source_item_id: str,
    ) -> EbookItem | None:
        statement = select(EbookItem).where(
            EbookItem.source_name == source_name,
            EbookItem.source_item_id == source_item_id,
        )
        return self.session.scalar(statement)

    def find_by_isbn(self, isbn: str) -> EbookItem | None:
        if not isbn:
            return None

        statement = select(EbookItem).where(EbookItem.isbn == isbn)
        return self.session.scalar(statement)

    def create(
        self,
        *,
        source_name: str,
        source_item_id: str,
        title: str,
        isbn: str | None = None,
        normalized_title: str | None = None,
        volume_label: str | None = None,
        author_name: str | None = None,
        publisher_name: str | None = None,
        series_name: str | None = None,
        release_date: date | None = None,
        item_type: str = "unknown",
    ) -> EbookItem:
        item = EbookItem(
            source_name=source_name,
            source_item_id=source_item_id,
            isbn=isbn,
            title=title,
            normalized_title=normalized_title,
            volume_label=volume_label,
            author_name=author_name,
            publisher_name=publisher_name,
            series_name=series_name,
            release_date=release_date,
            item_type=item_type,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def update(
        self,
        item: EbookItem,
        *,
        title: str,
        isbn: str | None,
        normalized_title: str | None,
        volume_label: str | None,
        author_name: str | None,
        publisher_name: str | None,
        series_name: str | None,
        release_date: date | None,
        item_type: str,
    ) -> EbookItem:
        item.title = title
        item.isbn = isbn or item.isbn
        item.normalized_title = normalized_title or item.normalized_title
        item.volume_label = volume_label or item.volume_label
        item.author_name = author_name or item.author_name
        item.publisher_name = publisher_name or item.publisher_name
        item.series_name = series_name or item.series_name
        item.release_date = release_date or item.release_date
        item.item_type = item_type or item.item_type

        self.session.flush()
        return item

    def delete(self, item: EbookItem) -> None:
        self.session.delete(item)
        self.session.flush()
