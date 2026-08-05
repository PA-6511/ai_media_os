from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    AffiliateDestinationProfile,
    EbookItem,
    StoreOffer,
    StoreOfferAffiliateLink,
)
from app.db.repositories.affiliate_destination_profile_repository import (
    AffiliateDestinationProfileRepository,
)
from app.db.repositories.store_offer_affiliate_link_repository import (
    StoreOfferAffiliateLinkRepository,
)
from app.services.dmm_destination_affiliate_link_service import (
    DmmDestinationAffiliateLinkError,
    DmmDestinationAffiliateLinkService,
)


PRODUCT_URL = "https://book.dmm.com/product/4493998/b000fhftx08481/"


def _profile(
    repository: AffiliateDestinationProfileRepository,
    *,
    key: str,
    destination_type: str,
    affiliate_id: str,
    active: bool = True,
) -> AffiliateDestinationProfile:
    profile, _ = repository.upsert(
        provider="dmm",
        destination_type=destination_type,
        destination_key=key,
        display_name="メインブログ" if key == "blog_main" else "公式X",
        affiliate_id=affiliate_id,
        channel="toolbar",
        channel_id="text",
        is_active=active,
    )
    return profile


def _offer(session: Session) -> StoreOffer:
    item = EbookItem(
        source_name="destination-profile-test",
        source_item_id="item-1",
        title="掲載先テスト",
        item_type="tankobon",
    )
    session.add(item)
    session.flush()
    offer = StoreOffer(
        ebook_item_id=item.id,
        store_name="dmm",
        store_item_id="b000fhftx08481",
        product_url=PRODUCT_URL,
    )
    session.add(offer)
    session.flush()
    return offer


def test_save_and_get_blog_and_x_profiles() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = AffiliateDestinationProfileRepository(session)
        blog = _profile(
            repository,
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )
        x_profile = _profile(
            repository,
            key="x_main",
            destination_type="x",
            affiliate_id="x-user-009",
        )

        assert repository.get(
            provider="dmm", destination_key="blog_main"
        ).id == blog.id
        assert repository.get(
            provider="dmm", destination_key="x_main"
        ).id == x_profile.id
        assert [
            profile.destination_key
            for profile in repository.list_active(provider="dmm")
        ] == ["blog_main", "x_main"]


def test_database_rejects_duplicate_provider_destination_key() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                AffiliateDestinationProfile(
                    provider="dmm",
                    destination_type="wordpress",
                    destination_key="blog_main",
                    display_name="A",
                    affiliate_id="a-001",
                ),
                AffiliateDestinationProfile(
                    provider="dmm",
                    destination_type="wordpress",
                    destination_key="blog_main",
                    display_name="B",
                    affiliate_id="b-001",
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_database_rejects_blank_affiliate_id() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            AffiliateDestinationProfile(
                provider="dmm",
                destination_type="wordpress",
                destination_key="blog_main",
                display_name="メインブログ",
                affiliate_id="   ",
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_profile_blank_update_preserves_existing_values() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = AffiliateDestinationProfileRepository(session)
        profile = _profile(
            repository,
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )

        updated, _ = repository.upsert(
            provider="dmm",
            destination_type="wordpress",
            destination_key="blog_main",
            display_name="メインブログ",
            affiliate_id="",
            channel="",
            channel_id="",
            is_active=False,
        )

        assert updated.id == profile.id
        assert updated.affiliate_id == "blog-user-008"
        assert updated.channel == "toolbar"
        assert updated.channel_id == "text"
        assert updated.is_active is False
        assert repository.list_active(provider="dmm") == []


def test_destination_link_upsert_deduplicates_and_preserves_blanks() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        profile = _profile(
            AffiliateDestinationProfileRepository(session),
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )
        offer = _offer(session)
        repository = StoreOfferAffiliateLinkRepository(session)
        first, _ = repository.upsert(
            store_offer_id=offer.id,
            profile_id=profile.id,
            affiliate_url="https://al.dmm.com/?first=1",
            generation_method="TEST",
            source_affiliate_id="blog-user-008",
        )
        second, _ = repository.upsert(
            store_offer_id=offer.id,
            profile_id=profile.id,
            affiliate_url="",
            generation_method="",
            source_affiliate_id="",
        )

        assert first.id == second.id
        assert second.affiliate_url == "https://al.dmm.com/?first=1"
        assert second.source_affiliate_id == "blog-user-008"
        assert session.scalar(
            select(func.count()).select_from(StoreOfferAffiliateLink)
        ) == 1
        assert repository.get_dmm_wordpress_link(
            store_offer_id=offer.id
        ).id == first.id
        assert repository.get_dmm_x_link(store_offer_id=offer.id) is None


def test_generate_destination_urls_without_mixing_ids() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        repository = AffiliateDestinationProfileRepository(session)
        blog = _profile(
            repository,
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )
        x_profile = _profile(
            repository,
            key="x_main",
            destination_type="x",
            affiliate_id="x-user-009",
        )
        service = DmmDestinationAffiliateLinkService(session)

        blog_link = service.generate(product_url=PRODUCT_URL, profile=blog)
        x_link = service.generate(product_url=PRODUCT_URL, profile=x_profile)

        assert blog_link is not None and x_link is not None
        blog_query = parse_qs(urlsplit(blog_link.affiliate_url).query)
        x_query = parse_qs(urlsplit(x_link.affiliate_url).query)
        assert blog_query["af_id"] == ["blog-user-008"]
        assert x_query["af_id"] == ["x-user-009"]
        assert blog_query["lurl"] == [PRODUCT_URL]
        assert x_query["lurl"] == [PRODUCT_URL]
        assert "%2Fproduct%2F4493998%2F" in blog_link.affiliate_url
        assert "x-user-009" not in blog_link.affiliate_url
        assert "blog-user-008" not in x_link.affiliate_url


def test_inactive_or_missing_profile_does_not_generate() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        profile = _profile(
            AffiliateDestinationProfileRepository(session),
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
            active=False,
        )
        service = DmmDestinationAffiliateLinkService(session)

        assert service.generate(product_url=PRODUCT_URL, profile=profile) is None
        assert service.generate_for_active_profiles(product_url=PRODUCT_URL) == ()


def test_reject_non_dmm_books_product_url() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        profile = _profile(
            AffiliateDestinationProfileRepository(session),
            key="blog_main",
            destination_type="wordpress",
            affiliate_id="blog-user-008",
        )

        with pytest.raises(DmmDestinationAffiliateLinkError):
            DmmDestinationAffiliateLinkService(session).generate(
                product_url="https://video.dmm.com/product/a/b/",
                profile=profile,
            )
