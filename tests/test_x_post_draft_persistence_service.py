from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base

# Load ebook_items before create_all because x_post_drafts has an FK.
from app.db.models.ebook import EbookItem  # noqa: F401
from app.db.models.x_post_draft import XPostDraft  # noqa: F401

from app.services.x_post_draft_persistence_service import (
    XPostDraftPersistenceService,
    XPostDraftSaveRequest,
)


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_new_release_draft_defaults_paid_partnership_true():
    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        result = service.save(
            XPostDraftSaveRequest(
                source_type="new_release",
                source_id="book-001",
                generated_text="新刊テスト #PR https://example.jp/book",
            )
        )

        assert result.status == "DRAFT"
        assert result.paid_partnership is True
        assert result.scheduled_at is None


def test_schedule_is_saved_with_paid_partnership():
    jst = timezone(timedelta(hours=9))
    scheduled_at = datetime(
        2026,
        9,
        28,
        12,
        15,
        tzinfo=jst,
    )

    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        result = service.save(
            XPostDraftSaveRequest(
                source_type="sale",
                source_id="sale-001",
                generated_text="セールテスト #PR https://example.jp/sale",
                scheduled_at=scheduled_at,
                paid_partnership=True,
            )
        )

        assert result.status == "DRAFT"
        assert result.scheduled_at is not None
        assert result.paid_partnership is True


def test_same_source_is_idempotent_upsert():
    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        first = service.save(
            XPostDraftSaveRequest(
                source_type="new_release",
                source_id="book-002",
                generated_text="first",
            )
        )

        second = service.save(
            XPostDraftSaveRequest(
                source_type="new_release",
                source_id="book-002",
                generated_text="second",
                paid_partnership=True,
            )
        )

        assert first.draft_id == second.draft_id
        assert second.generated_text == "second"

        rows = session.query(XPostDraft).all()
        assert len(rows) == 1


def test_naive_schedule_is_rejected():
    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        with pytest.raises(
            ValueError,
            match="timezone-aware",
        ):
            service.save(
                XPostDraftSaveRequest(
                    source_type="new_release",
                    source_id="book-003",
                    generated_text="draft",
                    scheduled_at=datetime(2026, 9, 28, 12, 15),
                )
            )


def test_paid_partnership_must_be_boolean():
    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        with pytest.raises(
            ValueError,
            match="paid_partnership must be boolean",
        ):
            service.save(
                XPostDraftSaveRequest(
                    source_type="sale",
                    source_id="sale-002",
                    generated_text="draft",
                    paid_partnership=1,  # type: ignore[arg-type]
                )
            )


def test_sqlite_schedule_roundtrip_restores_utc_timezone():
    jst = timezone(timedelta(hours=9))
    scheduled_at = datetime(
        2026,
        9,
        29,
        12,
        15,
        tzinfo=jst,
    )

    with make_session() as session:
        service = XPostDraftPersistenceService(session)

        result = service.save(
            XPostDraftSaveRequest(
                source_type="sale",
                source_id="timezone-roundtrip",
                generated_text="timezone test",
                scheduled_at=scheduled_at,
                paid_partnership=True,
            )
        )

        draft_id = result.draft_id
        session.commit()
        session.expire_all()

        stored = session.get(
            XPostDraft,
            draft_id,
        )

        assert stored is not None
        assert stored.scheduled_at is not None
        assert stored.scheduled_at.tzinfo is not None

        assert (
            stored.scheduled_at.utcoffset()
            == timedelta(0)
        )

        assert stored.scheduled_at == datetime(
            2026,
            9,
            29,
            3,
            15,
            tzinfo=timezone.utc,
        )
