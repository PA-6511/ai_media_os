from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import CatalogEditHistory, EbookItem, StoreOffer
from app.services.manual_store_offer_service import (
    ManualStoreOfferError,
    ManualStoreOfferService,
)


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def item(session: Session, *, source_name: str, source_discovery: str | None = None) -> EbookItem:
    value = EbookItem(
        source_name=source_name,
        source_item_id=f"{source_name}-1",
        source_discovery=source_discovery,
        title=f"{source_name}作品",
        workflow_status="NEW",
        review_status="NOT_REVIEWED",
        wordpress_status="NOT_CREATED",
    )
    session.add(value)
    session.commit()
    return value


@pytest.mark.parametrize(
    ("source_name", "source_discovery"),
    [
        ("manual", None),
        ("rakuten_books_comic_calendar", "RAKUTEN_BOOKS_COMIC_CALENDAR"),
        ("csv_import", "CSV"),
    ],
)
def test_create_rakuten_offer_for_any_item_source(
    session: Session, source_name: str, source_discovery: str | None
) -> None:
    target = item(
        session, source_name=source_name, source_discovery=source_discovery
    )
    observed_at = datetime(2026, 8, 3, 1, 2, 3, tzinfo=timezone.utc)

    result = ManualStoreOfferService(session).create_offer(
        ebook_item_id=target.id,
        store_name="rakuten_kobo",
        product_url="",
        affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real-link/",
        price="",
        currency="JPY",
        availability_status="FOUND",
        observed_at=observed_at,
        operator="human:test",
    )
    session.commit()

    offer = session.get(StoreOffer, result.offer_id)
    assert offer is not None
    assert offer.store_name == "rakuten_kobo"
    assert offer.product_url is None
    assert offer.affiliate_url == "https://hb.afl.rakuten.co.jp/hgc/real-link/"
    assert offer.price_amount is None
    assert offer.currency == "JPY"
    assert offer.availability_status == "FOUND_CONFIRMED"
    assert offer.verification_method == "MANUAL_WEB_EDIT"
    assert offer.verified_at.replace(tzinfo=timezone.utc) == observed_at
    assert target.workflow_status == "NEW"
    assert target.review_status == "NOT_REVIEWED"
    history = session.scalars(
        select(CatalogEditHistory).where(
            CatalogEditHistory.ebook_item_id == target.id
        )
    ).all()
    assert any(row.field_name == "rakuten_kobo.offer_created" for row in history)
    assert all("real-link" not in str(row.after_value or "") for row in history)


def test_create_with_product_url_and_price(session: Session) -> None:
    target = item(session, source_name="manual")

    result = ManualStoreOfferService(session).create_offer(
        ebook_item_id=target.id,
        store_name="rakuten_kobo",
        product_url="https://books.rakuten.co.jp/rk/real-item/",
        affiliate_url="https://a.r10.to/hRealLink",
        price="780",
        currency="JPY",
        availability_status="FOUND",
        observed_at=None,
        operator="human:test",
    )

    offer = session.get(StoreOffer, result.offer_id)
    assert offer is not None
    assert offer.product_url == "https://books.rakuten.co.jp/rk/real-item/"
    assert offer.price_amount == Decimal("780")
    assert offer.price_yen == 780


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("affiliate_url", "", "AFFILIATE_URL_REQUIRED"),
        ("affiliate_url", "http://hb.afl.rakuten.co.jp/hgc/real/", "URL_HTTPS_REQUIRED"),
        ("affiliate_url", "javascript:alert(1)", "URL_HTTPS_REQUIRED"),
        ("affiliate_url", "data:text/plain,test", "URL_HTTPS_REQUIRED"),
        ("affiliate_url", "/relative", "URL_HTTPS_REQUIRED"),
        ("affiliate_url", "https://example.com/affiliate", "URL_PLACEHOLDER_FORBIDDEN"),
        ("affiliate_url", "https://evil.example.net/affiliate", "URL_HOST_NOT_ALLOWED"),
        ("product_url", "https://hb.afl.rakuten.co.jp/hgc/real/", "URL_HOST_NOT_ALLOWED"),
    ],
)
def test_rejects_unsafe_urls(
    session: Session, field: str, value: str, code: str
) -> None:
    target = item(session, source_name="manual")
    values = {
        "product_url": "",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/hgc/real/",
    }
    values[field] = value

    with pytest.raises(ManualStoreOfferError, match=code):
        ManualStoreOfferService(session).preview_create(
            ebook_item_id=target.id,
            store_name="rakuten_kobo",
            product_url=values["product_url"],
            affiliate_url=values["affiliate_url"],
            price="",
            currency="JPY",
            availability_status="FOUND",
            observed_at=None,
        )


@pytest.mark.parametrize("wordpress_status", ["SCHEDULED", "PUBLISHED"])
def test_rejects_scheduled_or_published(
    session: Session, wordpress_status: str
) -> None:
    target = item(session, source_name="manual")
    target.wordpress_status = wordpress_status
    session.commit()

    with pytest.raises(ManualStoreOfferError, match="WORDPRESS_STATUS_BLOCKED"):
        ManualStoreOfferService(session).preview_create(
            ebook_item_id=target.id,
            store_name="rakuten_kobo",
            product_url="",
            affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
            price="",
            currency="JPY",
            availability_status="FOUND",
            observed_at=None,
        )


def test_allows_wordpress_draft_without_remote_write(session: Session) -> None:
    target = item(session, source_name="manual")
    target.wordpress_status = "DRAFT"
    target.wordpress_post_id = "123"
    session.commit()

    ManualStoreOfferService(session).create_offer(
        ebook_item_id=target.id,
        store_name="rakuten_kobo",
        product_url="",
        affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
        price="",
        currency="JPY",
        availability_status="FOUND",
        observed_at=None,
        operator="human:test",
    )

    assert target.wordpress_status == "DRAFT"
    assert target.wordpress_post_id == "123"


def test_rejects_missing_item_and_duplicate_store(session: Session) -> None:
    service = ManualStoreOfferService(session)
    with pytest.raises(ManualStoreOfferError, match="ITEM_NOT_FOUND"):
        service.preview_create(
            ebook_item_id="missing",
            store_name="rakuten_kobo",
            product_url="",
            affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
            price="",
            currency="JPY",
            availability_status="FOUND",
            observed_at=None,
        )

    target = item(session, source_name="manual")
    service.create_offer(
        ebook_item_id=target.id,
        store_name="rakuten_kobo",
        product_url="",
        affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
        price="",
        currency="JPY",
        availability_status="FOUND",
        observed_at=None,
        operator="human:test",
    )
    with pytest.raises(ManualStoreOfferError, match="STORE_OFFER_ALREADY_EXISTS"):
        service.create_offer(
            ebook_item_id=target.id,
            store_name="rakuten_kobo",
            product_url="",
            affiliate_url="https://hb.afl.rakuten.co.jp/hgc/other-real/",
            price="",
            currency="JPY",
            availability_status="FOUND",
            observed_at=None,
            operator="human:test",
        )
    assert session.scalar(select(func.count()).select_from(StoreOffer)) == 1


def test_failure_rolls_back_offer_and_history(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = item(session, source_name="manual")
    service = ManualStoreOfferService(session)

    def fail_history(*args, **kwargs):
        raise RuntimeError("history failed")

    monkeypatch.setattr(service, "_add_history", fail_history)
    with pytest.raises(RuntimeError, match="history failed"):
        with session.begin():
            service.create_offer(
                ebook_item_id=target.id,
                store_name="rakuten_kobo",
                product_url="",
                affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
                price="",
                currency="JPY",
                availability_status="FOUND",
                observed_at=None,
                operator="human:test",
            )

    assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
    assert session.scalar(select(func.count()).select_from(CatalogEditHistory)) == 0


def test_other_item_is_unchanged(session: Session) -> None:
    target = item(session, source_name="manual")
    other = item(session, source_name="other")

    ManualStoreOfferService(session).create_offer(
        ebook_item_id=target.id,
        store_name="rakuten_kobo",
        product_url="",
        affiliate_url="https://hb.afl.rakuten.co.jp/hgc/real/",
        price="",
        currency="JPY",
        availability_status="FOUND",
        observed_at=None,
        operator="human:test",
    )

    assert session.scalar(
        select(func.count()).select_from(StoreOffer).where(
            StoreOffer.ebook_item_id == other.id
        )
    ) == 0
