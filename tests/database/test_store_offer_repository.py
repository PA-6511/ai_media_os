from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.ebook import EbookItem
from app.db.repositories.store_offer_repository import StoreOfferRepository


def create_ebook_item(session: Session) -> EbookItem:
    item = EbookItem(
        source_name="manual_test",
        source_item_id="manual-test-001",
        title="暫定Amazonリンクテスト",
        item_type="tankobon",
    )
    session.add(item)
    session.flush()
    return item


def test_save_and_find_amazon_offer() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        offer = repository.save_amazon_offer(
            ebook_item_id=item.id,
            asin="b0abcdefgh",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url=(
                "https://www.amazon.co.jp/dp/"
                "B0ABCDEFGH/ref=nosim?tag=test-22"
            ),
        )

        assert offer.store_name == "amazon"
        assert offer.store_item_id == "B0ABCDEFGH"

        saved = repository.find_amazon_offer(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
        )

        assert saved is not None
        assert saved.id == offer.id
        assert saved.affiliate_url.endswith("tag=test-22")


def test_save_amazon_offer_updates_existing_row() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        first = repository.save_amazon_offer(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url="https://example.com/old",
        )

        second = repository.save_amazon_offer(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url=(
                "https://www.amazon.co.jp/dp/"
                "B0ABCDEFGH/ref=nosim?tag=test-22"
            ),
        )

        assert second.id == first.id
        assert second.affiliate_url.endswith("tag=test-22")


def test_delete_amazon_offer() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        repository.save_amazon_offer(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url=(
                "https://www.amazon.co.jp/dp/"
                "B0ABCDEFGH/ref=nosim?tag=test-22"
            ),
        )

        deleted = repository.delete_amazon_offer(
            ebook_item_id=item.id,
            asin="B0ABCDEFGH",
        )

        assert deleted is True
        assert (
            repository.find_amazon_offer(
                ebook_item_id=item.id,
                asin="B0ABCDEFGH",
            )
            is None
        )
