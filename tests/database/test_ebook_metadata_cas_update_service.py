from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, select

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from app.db.repositories.ebook_metadata_cas_repository import (
    EbookMetadataCasRepository,
)
from app.services.ebook_metadata_cas_update_service import (
    EbookMetadataCasUpdateError,
    EbookMetadataCasUpdateRequest,
    EbookMetadataCasUpdateService,
)


def _engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'cas-service.db'}")
    Base.metadata.create_all(engine)
    created_at = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            EbookItem.__table__.insert(),
            {
                "id": "target",
                "source_name": "fixture",
                "source_item_id": "source-20",
                "title": "作品 20",
                "normalized_title": "作品 20",
                "volume_label": "第20巻",
                "release_date": date(2026, 8, 1),
                "workflow_status": "READY",
                "review_status": "APPROVED",
                "publish_ready": True,
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
                "product_url": "https://example.invalid/item",
                "affiliate_url": "https://example.invalid/affiliate-secret",
                "price_yen": 244,
                "last_checked_at": created_at,
            },
        )
    return engine


def _request(**overrides) -> EbookMetadataCasUpdateRequest:
    values = {
        "ebook_item_id": "target",
        "expected_author_name": None,
        "approved_author_name": "著者",
        "expected_publisher_name": None,
        "approved_publisher_name": "出版社",
    }
    values.update(overrides)
    return EbookMetadataCasUpdateRequest.from_mapping(values)


def _metadata(engine) -> tuple[object, ...]:
    with engine.connect() as connection:
        row = connection.execute(
            select(
                EbookItem.author_name,
                EbookItem.publisher_name,
                EbookItem.title,
                EbookItem.normalized_title,
                EbookItem.volume_label,
                EbookItem.release_date,
                EbookItem.workflow_status,
                EbookItem.review_status,
                EbookItem.publish_ready,
                EbookItem.updated_at,
            ).where(EbookItem.id == "target")
        ).one()
    return tuple(row)


def test_service_commits_exactly_two_fields_and_preserves_everything_else(
    tmp_path,
) -> None:
    engine = _engine(tmp_path)
    before = _metadata(engine)
    result = EbookMetadataCasUpdateService(engine).execute(_request())
    after = _metadata(engine)
    assert result.matched_row_count == result.updated_row_count == 1
    assert result.transaction_result == "COMMITTED"
    assert result.immutable_fields_unchanged is True
    assert result.store_offers_unchanged is True
    assert after[:2] == ("著者", "出版社")
    assert after[2:] == before[2:]


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected_author_name": "別著者"},
        {"expected_publisher_name": "別出版社"},
        {"ebook_item_id": "missing"},
    ],
)
def test_before_mismatch_or_missing_target_rolls_back(tmp_path, overrides) -> None:
    engine = _engine(tmp_path)
    before = _metadata(engine)
    with pytest.raises(EbookMetadataCasUpdateError):
        EbookMetadataCasUpdateService(engine).execute(_request(**overrides))
    assert _metadata(engine) == before


def test_second_execution_fails_cas_without_changing_first_result(tmp_path) -> None:
    engine = _engine(tmp_path)
    service = EbookMetadataCasUpdateService(engine)
    service.execute(_request())
    first = _metadata(engine)
    with pytest.raises(EbookMetadataCasUpdateError, match="CAS_BEFORE_MISMATCH"):
        service.execute(_request())
    assert _metadata(engine) == first


@pytest.mark.parametrize("field_name", ["title", "workflow_status"])
def test_request_rejects_any_field_outside_exact_contract(field_name) -> None:
    values = {
        "ebook_item_id": "target",
        "expected_author_name": None,
        "approved_author_name": "著者",
        "expected_publisher_name": None,
        "approved_publisher_name": "出版社",
        field_name: "forbidden",
    }
    with pytest.raises(
        EbookMetadataCasUpdateError,
        match="REQUEST_FIELDS_NOT_ALLOWED",
    ):
        EbookMetadataCasUpdateRequest.from_mapping(values)


class _WrongRowCountRepository(EbookMetadataCasRepository):
    def compare_and_set(self, *args, **kwargs) -> int:
        super().compare_and_set(*args, **kwargs)
        return 2


class _BadAfterRepository(EbookMetadataCasRepository):
    calls = 0

    def fetch_snapshot(self, *args, **kwargs):
        snapshot = super().fetch_snapshot(*args, **kwargs)
        self.calls += 1
        if snapshot is not None and self.calls == 2:
            return replace(snapshot, publisher_name="検証失敗")
        return snapshot


class _ExceptionRepository(EbookMetadataCasRepository):
    def compare_and_set(self, *args, **kwargs) -> int:
        super().compare_and_set(*args, **kwargs)
        raise RuntimeError("forced failure")


@pytest.mark.parametrize(
    ("repository", "message"),
    [
        (_WrongRowCountRepository(), "UPDATED_ROW_COUNT_MISMATCH:2"),
        (_BadAfterRepository(), "AFTER_VALUE_MISMATCH"),
        (_ExceptionRepository(), "forced failure"),
    ],
)
def test_any_post_update_failure_rolls_back(tmp_path, repository, message) -> None:
    engine = _engine(tmp_path)
    before = _metadata(engine)
    with pytest.raises(Exception, match=message):
        EbookMetadataCasUpdateService(
            engine, repository=repository
        ).execute(_request())
    assert _metadata(engine) == before