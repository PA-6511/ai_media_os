from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.ebook import EbookItem, StoreOffer
from app.services.amazon_manual_offer_service import AmazonManualOfferService


def test_generate_and_save_amazon_offer() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = EbookItem(
            source_name="manual_test",
            source_item_id="manual-offer-001",
            title="Amazon暫定保存テスト",
            item_type="tankobon",
        )
        session.add(item)
        session.flush()

        service = AmazonManualOfferService(session)

        result = service.save(
            ebook_item_id=item.id,
            asin="b0abcdefgh",
            tracking_id="example-22",
        )

        saved = session.scalar(
            select(StoreOffer).where(StoreOffer.id == result.offer_id)
        )

        assert saved is not None
        assert saved.ebook_item_id == item.id
        assert saved.store_name == "amazon"
        assert saved.store_item_id == "B0ABCDEFGH"
        assert (
            saved.product_url
            == "https://www.amazon.co.jp/dp/B0ABCDEFGH"
        )
        assert (
            saved.affiliate_url
            == "https://www.amazon.co.jp/dp/"
            "B0ABCDEFGH/ref=nosim?tag=example-22"
        )


def test_save_updates_same_amazon_offer() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = EbookItem(
            source_name="manual_test",
            source_item_id="manual-offer-002",
            title="Amazon暫定更新テスト",
            item_type="tankobon",
        )
        session.add(item)
        session.flush()

        service = AmazonManualOfferService(session)

        first = service.save(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
            tracking_id="oldtag-22",
        )

        second = service.save(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
            tracking_id="newtag-22",
        )

        offers = session.scalars(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id == item.id,
                StoreOffer.store_name == "amazon",
            )
        ).all()

        assert len(offers) == 1
        assert first.offer_id == second.offer_id
        assert offers[0].affiliate_url.endswith("tag=newtag-22")
