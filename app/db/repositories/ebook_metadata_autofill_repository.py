from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import CatalogEditHistory, EbookItem
from src.rakuten_kobo_csv import normalize_isbn13


TRUSTED_VERIFICATION_METHODS = frozenset({
    "RAKUTEN_KOBO_API_RESPONSE",
})


@dataclass(frozen=True)
class VerifiedMetadataRecord:
    source_type: str
    confidence: str
    volume_label: str | None
    author_name: str | None
    publisher_name: str | None


@dataclass(frozen=True)
class EbookMetadataAutofillContext:
    ebook_item_id: str
    title: str
    volume_label: str | None
    author_name: str | None
    publisher_name: str | None
    human_reviewed_fields: frozenset[str]
    verified_records: tuple[VerifiedMetadataRecord, ...]


class EbookMetadataAutofillRepository:
    """Read verified metadata and write only approved, empty catalog fields."""

    FIELD_NAMES = ("volume_label", "author_name", "publisher_name")

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _offer_is_verified(offer: object) -> bool:
        source_row_sha256 = str(
            getattr(offer, "source_row_sha256", None) or ""
        ).strip()
        method = str(
            getattr(offer, "verification_method", None) or ""
        ).strip()
        return bool(
            getattr(offer, "store_name", None) == "rakuten_kobo"
            and getattr(offer, "verified_at", None) is not None
            and method in TRUSTED_VERIFICATION_METHODS
            and re.fullmatch(r"[0-9a-fA-F]{64}", source_row_sha256)
        )

    @classmethod
    def _record_for_item(
        cls, item: EbookItem
    ) -> VerifiedMetadataRecord | None:
        verified_kobo_offers = [
            offer for offer in item.offers if cls._offer_is_verified(offer)
        ]
        if not verified_kobo_offers:
            return None
        return VerifiedMetadataRecord(
            source_type="RAKUTEN_KOBO",
            confidence="VERIFIED",
            volume_label=item.volume_label,
            author_name=item.author_name,
            publisher_name=item.publisher_name,
        )

    def load_context(self, ebook_item_id: str) -> EbookMetadataAutofillContext | None:
        item = self.session.scalar(
            select(EbookItem)
            .options(selectinload(EbookItem.offers))
            .where(EbookItem.id == ebook_item_id)
        )
        if item is None:
            return None

        reviewed_fields = frozenset(
            self.session.scalars(
                select(CatalogEditHistory.field_name).where(
                    CatalogEditHistory.ebook_item_id == item.id,
                    CatalogEditHistory.field_name.in_(self.FIELD_NAMES),
                    or_(
                        CatalogEditHistory.changed_by == "human",
                        CatalogEditHistory.changed_by.like("human:%"),
                    ),
                )
            ).all()
        )

        records: list[VerifiedMetadataRecord] = []
        # ISBN is the only existing cross-source key strong enough to merge
        # bibliographic values without guessing by a similar title.
        try:
            target_isbn = normalize_isbn13(item.isbn)
        except ValueError:
            target_isbn = ""
        if target_isbn:
            peers = self.session.scalars(
                select(EbookItem)
                .options(selectinload(EbookItem.offers))
                .where(
                    EbookItem.id != item.id,
                    EbookItem.isbn.is_not(None),
                )
                .order_by(EbookItem.created_at, EbookItem.id)
            ).all()
            for peer in peers:
                try:
                    peer_isbn = normalize_isbn13(peer.isbn)
                except ValueError:
                    continue
                if not peer_isbn or peer_isbn != target_isbn:
                    continue
                record = self._record_for_item(peer)
                if record is not None:
                    records.append(record)

        return EbookMetadataAutofillContext(
            ebook_item_id=item.id,
            title=item.title,
            volume_label=item.volume_label,
            author_name=item.author_name,
            publisher_name=item.publisher_name,
            human_reviewed_fields=reviewed_fields,
            verified_records=tuple(records),
        )

    def apply_empty_fields(
        self,
        *,
        ebook_item_id: str,
        expected_before: dict[str, str | None],
        values: dict[str, str],
        changed_by: str,
    ) -> tuple[str, ...]:
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise ValueError("item_not_found")

        changed: list[str] = []
        for field_name, after_value in values.items():
            if field_name not in self.FIELD_NAMES:
                raise ValueError(f"unsupported metadata field: {field_name}")
            before_value = getattr(item, field_name)
            if before_value != expected_before.get(field_name):
                raise ValueError(f"stale_metadata:{field_name}")
            if str(before_value or "").strip():
                raise ValueError(f"existing_value_protected:{field_name}")
            setattr(item, field_name, after_value)
            self.session.add(
                CatalogEditHistory(
                    ebook_item_id=item.id,
                    field_name=field_name,
                    before_value=before_value,
                    after_value=after_value,
                    change_reason="verified ebook metadata autofill",
                    changed_by=changed_by,
                )
            )
            changed.append(field_name)

        if changed:
            if item.review_status != "NOT_REVIEWED":
                before_review_status = item.review_status
                item.review_status = "NOT_REVIEWED"
                self.session.add(
                    CatalogEditHistory(
                        ebook_item_id=item.id,
                        field_name="review_status",
                        before_value=before_review_status,
                        after_value="NOT_REVIEWED",
                        change_reason="metadata changed; review reset to safe state",
                        changed_by=changed_by,
                    )
                )
            if item.publish_ready:
                item.publish_ready = False
                self.session.add(
                    CatalogEditHistory(
                        ebook_item_id=item.id,
                        field_name="publish_ready",
                        before_value="True",
                        after_value="False",
                        change_reason="metadata changed; publish readiness reset",
                        changed_by=changed_by,
                    )
                )

        self.session.flush()
        return tuple(changed)
