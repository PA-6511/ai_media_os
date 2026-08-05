from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

from sqlalchemy import Engine

from app.db.repositories.ebook_metadata_cas_repository import (
    EbookMetadataCasRepository,
    EbookMetadataCasSnapshot,
)


REQUEST_FIELD_NAMES = frozenset({
    "ebook_item_id",
    "expected_author_name",
    "approved_author_name",
    "expected_publisher_name",
    "approved_publisher_name",
})


class EbookMetadataCasUpdateError(ValueError):
    pass


@dataclass(frozen=True)
class EbookMetadataCasUpdateRequest:
    ebook_item_id: str
    expected_author_name: str | None
    approved_author_name: str
    expected_publisher_name: str | None
    approved_publisher_name: str

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
    ) -> "EbookMetadataCasUpdateRequest":
        if set(values) != REQUEST_FIELD_NAMES:
            raise EbookMetadataCasUpdateError("REQUEST_FIELDS_NOT_ALLOWED")
        ebook_item_id = values["ebook_item_id"]
        expected_author = values["expected_author_name"]
        expected_publisher = values["expected_publisher_name"]
        approved_author = values["approved_author_name"]
        approved_publisher = values["approved_publisher_name"]
        if not isinstance(ebook_item_id, str) or not ebook_item_id.strip():
            raise EbookMetadataCasUpdateError("INVALID_EBOOK_ITEM_ID")
        for field_name, value in (
            ("expected_author_name", expected_author),
            ("expected_publisher_name", expected_publisher),
        ):
            if value is not None and not isinstance(value, str):
                raise EbookMetadataCasUpdateError(f"INVALID_{field_name.upper()}")
        for field_name, value in (
            ("approved_author_name", approved_author),
            ("approved_publisher_name", approved_publisher),
        ):
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value) > 255
            ):
                raise EbookMetadataCasUpdateError(f"INVALID_{field_name.upper()}")
        return cls(
            ebook_item_id=ebook_item_id.strip(),
            expected_author_name=expected_author,
            approved_author_name=approved_author,
            expected_publisher_name=expected_publisher,
            approved_publisher_name=approved_publisher,
        )


@dataclass(frozen=True)
class EbookMetadataCasUpdateResult:
    ebook_item_id: str
    matched_row_count: int
    updated_row_count: int
    before_snapshot: EbookMetadataCasSnapshot
    after_snapshot: EbookMetadataCasSnapshot
    immutable_fields_unchanged: bool
    store_offers_sha256_before: str
    store_offers_sha256_after: str
    store_offers_unchanged: bool
    transaction_result: str

    def audit_values(self) -> dict[str, object]:
        return {
            "ebook_item_id": self.ebook_item_id,
            "matched_row_count": self.matched_row_count,
            "updated_row_count": self.updated_row_count,
            "before": {
                "author_name": self.before_snapshot.author_name,
                "publisher_name": self.before_snapshot.publisher_name,
            },
            "after": {
                "author_name": self.after_snapshot.author_name,
                "publisher_name": self.after_snapshot.publisher_name,
            },
            "immutable_before": dict(
                self.before_snapshot.immutable_values
            ),
            "immutable_after": dict(
                self.after_snapshot.immutable_values
            ),
            "immutable_fields_unchanged": self.immutable_fields_unchanged,
            "store_offers_sha256_before": self.store_offers_sha256_before,
            "store_offers_sha256_after": self.store_offers_sha256_after,
            "store_offers_unchanged": self.store_offers_unchanged,
            "transaction_result": self.transaction_result,
        }


class EbookMetadataCasUpdateService:
    def __init__(
        self,
        engine: Engine,
        *,
        repository: EbookMetadataCasRepository | None = None,
    ) -> None:
        self.engine = engine
        self.repository = repository or EbookMetadataCasRepository()

    def execute(
        self,
        request: EbookMetadataCasUpdateRequest,
    ) -> EbookMetadataCasUpdateResult:
        connection = self.engine.connect()
        transaction = connection.begin()
        try:
            before = self.repository.fetch_snapshot(
                connection, request.ebook_item_id
            )
            if before is None:
                raise EbookMetadataCasUpdateError("TARGET_NOT_FOUND")
            if (
                before.author_name != request.expected_author_name
                or before.publisher_name != request.expected_publisher_name
            ):
                raise EbookMetadataCasUpdateError("CAS_BEFORE_MISMATCH")
            offers_before = self.repository.store_offers_sha256(
                connection, request.ebook_item_id
            )
            updated = self.repository.compare_and_set(
                connection,
                ebook_item_id=request.ebook_item_id,
                expected_author_name=request.expected_author_name,
                approved_author_name=request.approved_author_name,
                expected_publisher_name=request.expected_publisher_name,
                approved_publisher_name=request.approved_publisher_name,
            )
            if updated != 1:
                raise EbookMetadataCasUpdateError(
                    f"UPDATED_ROW_COUNT_MISMATCH:{updated}"
                )
            after = self.repository.fetch_snapshot(
                connection, request.ebook_item_id
            )
            if after is None:
                raise EbookMetadataCasUpdateError("TARGET_MISSING_AFTER_UPDATE")
            if (
                after.author_name != request.approved_author_name
                or after.publisher_name != request.approved_publisher_name
            ):
                raise EbookMetadataCasUpdateError("AFTER_VALUE_MISMATCH")
            immutable_unchanged = (
                after.immutable_values == before.immutable_values
            )
            if not immutable_unchanged:
                raise EbookMetadataCasUpdateError("IMMUTABLE_FIELD_CHANGED")
            offers_after = self.repository.store_offers_sha256(
                connection, request.ebook_item_id
            )
            offers_unchanged = offers_after == offers_before
            if not offers_unchanged:
                raise EbookMetadataCasUpdateError("STORE_OFFERS_CHANGED")
            transaction.commit()
            return EbookMetadataCasUpdateResult(
                ebook_item_id=request.ebook_item_id,
                matched_row_count=updated,
                updated_row_count=updated,
                before_snapshot=before,
                after_snapshot=after,
                immutable_fields_unchanged=immutable_unchanged,
                store_offers_sha256_before=offers_before,
                store_offers_sha256_after=offers_after,
                store_offers_unchanged=offers_unchanged,
                transaction_result="COMMITTED",
            )
        except Exception:
            if transaction.is_active:
                transaction.rollback()
            raise
        finally:
            connection.close()