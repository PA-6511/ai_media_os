from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import Connection, select, text

from app.db.models import EbookItem, StoreOffer


IMMUTABLE_FIELD_NAMES = (
    "id",
    "source_name",
    "source_item_id",
    "title",
    "normalized_title",
    "volume_label",
    "release_date",
    "workflow_status",
    "review_status",
    "publish_ready",
    "created_at",
    "updated_at",
)


@dataclass(frozen=True)
class EbookMetadataCasSnapshot:
    ebook_item_id: str
    author_name: str | None
    publisher_name: str | None
    immutable_values: dict[str, object]


class EbookMetadataCasRepository:
    def fetch_snapshot(
        self,
        connection: Connection,
        ebook_item_id: str,
    ) -> EbookMetadataCasSnapshot | None:
        columns = (
            EbookItem.id,
            EbookItem.author_name,
            EbookItem.publisher_name,
            *(getattr(EbookItem, name) for name in IMMUTABLE_FIELD_NAMES[1:]),
        )
        row = connection.execute(
            select(*columns).where(EbookItem.id == ebook_item_id)
        ).mappings().one_or_none()
        if row is None:
            return None
        return EbookMetadataCasSnapshot(
            ebook_item_id=str(row["id"]),
            author_name=row["author_name"],
            publisher_name=row["publisher_name"],
            immutable_values={name: row[name] for name in IMMUTABLE_FIELD_NAMES},
        )

    def compare_and_set(
        self,
        connection: Connection,
        *,
        ebook_item_id: str,
        expected_author_name: str | None,
        approved_author_name: str,
        expected_publisher_name: str | None,
        approved_publisher_name: str,
    ) -> int:
        result = connection.execute(
            text(
                "UPDATE ebook_items "
                "SET author_name = :approved_author_name, "
                "publisher_name = :approved_publisher_name "
                "WHERE id = :ebook_item_id "
                "AND author_name IS :expected_author_name "
                "AND publisher_name IS :expected_publisher_name"
            ),
            {
                "ebook_item_id": ebook_item_id,
                "expected_author_name": expected_author_name,
                "approved_author_name": approved_author_name,
                "expected_publisher_name": expected_publisher_name,
                "approved_publisher_name": approved_publisher_name,
            },
        )
        return int(result.rowcount or 0)

    def store_offers_sha256(
        self,
        connection: Connection,
        ebook_item_id: str,
    ) -> str:
        rows = connection.execute(
            select(StoreOffer.__table__)
            .where(StoreOffer.ebook_item_id == ebook_item_id)
            .order_by(StoreOffer.id)
        ).mappings().all()
        canonical = [
            {
                key: _canonical_value(value)
                for key, value in sorted(dict(row).items())
            }
            for row in rows
        ]
        encoded = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _canonical_value(value: Any) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value