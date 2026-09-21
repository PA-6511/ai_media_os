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


def test_upsert_manual_offer_creates_shared_store_offer_contract() -> None:
    from decimal import Decimal

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        offer, changes = repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="dmm",
            store_item_id="dmm-product-001",
            product_url="https://book.dmm.com/product/12345/",
            affiliate_url="https://example.com/dmm-affiliate",
            price_amount=Decimal("770"),
            currency="JPY",
            verification_method="DMM_INITIAL_DISCOVERY",
        )

        assert offer.id
        assert offer.ebook_item_id == item.id
        assert offer.store_name == "dmm"
        assert offer.store_item_id == "dmm-product-001"
        assert offer.product_url == "https://book.dmm.com/product/12345/"
        assert offer.affiliate_url == "https://example.com/dmm-affiliate"
        assert offer.price_amount == Decimal("770")
        assert offer.price_yen == 770
        assert offer.currency == "JPY"
        assert offer.availability_status == "FOUND_CONFIRMED"
        assert offer.verification_method == "DMM_INITIAL_DISCOVERY"
        assert offer.verified_at is not None
        assert offer.last_checked_at is not None

        assert "product_url" in changes
        assert "affiliate_url" in changes
        assert "price_amount" in changes
        assert "price_yen" in changes
        assert "currency" in changes
        assert "availability_status" in changes
        assert "verification_method" in changes

        saved = repository.find(
            ebook_item_id=item.id,
            store_name="dmm",
            store_item_id="dmm-product-001",
        )

        assert saved is not None
        assert saved.id == offer.id


def test_upsert_manual_offer_updates_existing_row_without_duplicate() -> None:
    from decimal import Decimal

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        first, _ = repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="amazon",
            store_item_id="B0ABCDEFGH",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url="https://example.com/amazon-old",
            price_amount=Decimal("700"),
            currency="JPY",
            verification_method="MANUAL_WEB_EDIT",
        )

        first_id = first.id

        second, changes = repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="amazon",
            store_item_id="B0ABCDEFGH",
            product_url="https://www.amazon.co.jp/dp/B0ABCDEFGH",
            affiliate_url="https://example.com/amazon-new",
            price_amount=Decimal("880"),
            currency="JPY",
            verification_method="CREATORS_API",
        )

        assert second.id == first_id
        assert second.affiliate_url == "https://example.com/amazon-new"
        assert second.price_amount == Decimal("880")
        assert second.price_yen == 880
        assert second.currency == "JPY"
        assert second.verification_method == "CREATORS_API"

        assert changes["affiliate_url"] == (
            "https://example.com/amazon-old",
            "https://example.com/amazon-new",
        )
        assert changes["price_amount"] == (
            Decimal("700"),
            Decimal("880"),
        )
        assert changes["price_yen"] == (700, 880)
        assert changes["verification_method"] == (
            "MANUAL_WEB_EDIT",
            "CREATORS_API",
        )

        all_amazon = list(
            session.scalars(
                __import__("sqlalchemy").select(
                    type(second)
                ).where(
                    type(second).ebook_item_id == item.id,
                    type(second).store_name == "amazon",
                )
            )
        )

        assert len(all_amazon) == 1


def test_upsert_manual_offer_identical_payload_is_idempotent() -> None:
    from decimal import Decimal

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        item = create_ebook_item(session)
        repository = StoreOfferRepository(session)

        first, first_changes = repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="rakuten_kobo",
            store_item_id="8922000000001",
            product_url="https://books.rakuten.co.jp/rk/test-contract/",
            affiliate_url="https://example.com/kobo-affiliate",
            price_amount=Decimal("660"),
            currency="JPY",
            verification_method="MANUAL_WEB_EDIT",
        )

        first_id = first.id
        verified_at_before = first.verified_at
        checked_at_before = first.last_checked_at

        assert first_changes

        second, second_changes = repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="rakuten_kobo",
            store_item_id="8922000000001",
            product_url="https://books.rakuten.co.jp/rk/test-contract/",
            affiliate_url="https://example.com/kobo-affiliate",
            price_amount=Decimal("660"),
            currency="JPY",
            verification_method="MANUAL_WEB_EDIT",
        )

        assert second.id == first_id
        assert second_changes == {}
        assert second.verified_at == verified_at_before
        assert second.last_checked_at == checked_at_before

        saved = repository.find_for_store(
            ebook_item_id=item.id,
            store_name="rakuten_kobo",
        )

        assert saved is not None
        assert saved.id == first_id
