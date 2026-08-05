from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import create_engine, select

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.db.repositories.ebook_metadata_cas_repository import (
    EbookMetadataCasRepository,
)


def test_null_safe_cas_changes_only_author_and_publisher(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'cas-repository.db'}")
    Base.metadata.create_all(engine)
    created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            EbookItem.__table__.insert(),
            {
                "id": "target",
                "source_name": "fixture",
                "source_item_id": "fixture-1",
                "title": "作品 20",
                "normalized_title": "作品 20",
                "volume_label": "第20巻",
                "release_date": date(2026, 8, 1),
                "workflow_status": "NEW",
                "review_status": "NOT_REVIEWED",
                "publish_ready": False,
                "created_at": created_at,
                "updated_at": created_at,
            },
        )
        connection.execute(
            StoreOffer.__table__.insert(),
            {
                "id": "offer",
                "ebook_item_id": "target",
                "store_name": "rakuten_kobo",
                "store_item_id": "item-20",
                "last_checked_at": created_at,
            },
        )

    repository = EbookMetadataCasRepository()
    with engine.begin() as connection:
        before = repository.fetch_snapshot(connection, "target")
        offers_before = repository.store_offers_sha256(connection, "target")
        row_count = repository.compare_and_set(
            connection,
            ebook_item_id="target",
            expected_author_name=None,
            approved_author_name="著者",
            expected_publisher_name=None,
            approved_publisher_name="出版社",
        )
        after = repository.fetch_snapshot(connection, "target")
        offers_after = repository.store_offers_sha256(connection, "target")

    assert before is not None and after is not None
    assert row_count == 1
    assert (after.author_name, after.publisher_name) == ("著者", "出版社")
    assert after.immutable_values == before.immutable_values
    assert offers_after == offers_before
    with engine.connect() as connection:
        row = connection.execute(
            select(EbookItem).where(EbookItem.id == "target")
        ).one()
    assert row is not None