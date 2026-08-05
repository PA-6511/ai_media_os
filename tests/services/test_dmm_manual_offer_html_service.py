from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import create_engine, func, select
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
from app.services.dmm_manual_offer_service import (
    DmmManualOfferError,
    DmmManualOfferService,
)


TITLE = "悪役をやめたら義弟に溺愛されました3【電子限定特典付き】"
AFFILIATE_URL = (
    "https://al.dmm.com/?lurl=https%3A%2F%2Fbook.dmm.com%2Fproduct%2F"
    "4493998%2Fb000fhftx08481%2F&af_id=xuanyilugang-008&ch=toolbar&ch_id=text"
)
HTML = f'<a href="{AFFILIATE_URL}" rel="sponsored">{TITLE}</a>'


def _item_and_settings(
    session: Session, *, include_x: bool = True
) -> EbookItem:
    item = EbookItem(
        source_name="manual_test",
        source_item_id="dmm-html-001",
        title=TITLE,
        item_type="light_novel",
    )
    session.add(item)
    session.flush()
    profiles = AffiliateDestinationProfileRepository(session)
    profiles.upsert(
        provider="dmm",
        destination_type="wordpress",
        destination_key="blog_main",
        display_name="メインブログ",
        affiliate_id="xuanyilugang-008",
        channel="toolbar",
        channel_id="text",
    )
    if include_x:
        profiles.upsert(
            provider="dmm",
            destination_type="x",
            destination_key="x_main",
            display_name="公式X",
            affiliate_id="xuanyilugang-x-009",
            channel="toolbar",
            channel_id="text",
        )
    return item


def test_preview_does_not_write_and_save_writes_only_on_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_external_network(*_args, **_kwargs):
        pytest.fail("DMM parse/save must not call an external network")

    monkeypatch.setattr("socket.create_connection", forbid_external_network)
    monkeypatch.setattr("urllib.request.urlopen", forbid_external_network)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        service = DmmManualOfferService(session)

        preview = service.preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
        )
        assert preview.registration_allowed is True
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0
        with pytest.raises(DmmManualOfferError, match="confirmation"):
            service.save(preview=preview, confirmed=False)
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0

        result = service.save(preview=preview, confirmed=True)
        saved = session.get(StoreOffer, result.offer_id)
        assert saved is not None
        assert saved.store_name == "dmm"
        assert saved.store_item_id == "b000fhftx08481"
        assert saved.product_url == (
            "https://book.dmm.com/product/4493998/b000fhftx08481/"
        )
        assert saved.affiliate_url == AFFILIATE_URL
        assert saved.verification_method == "MANUAL_DMM_HTML_PARSE"
        assert session.scalar(
            select(func.count()).select_from(StoreOfferAffiliateLink)
        ) == 2
        assert len(result.affiliate_link_ids) == 2
        assert item.wordpress_status == "NOT_CREATED"
        assert item.x_status == "NOT_CREATED"


def test_affiliate_id_mismatch_warns_and_blocks_save() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML.replace("xuanyilugang-008", "other-user-999"),
        )

        assert "affiliate_profile_not_found" in preview.warnings
        assert preview.registration_allowed is False
        with pytest.raises(DmmManualOfferError, match="blocked"):
            DmmManualOfferService(session).save(
                preview=preview, confirmed=True
            )
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0


def test_large_title_mismatch_warns_and_blocks_without_changing_title() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML.replace(TITLE, "まったく別のゲーム攻略本"),
        )

        assert "title_mismatch" in preview.blocking_warnings
        assert item.title == TITLE
        assert session.scalar(select(func.count()).select_from(StoreOffer)) == 0


def test_normal_product_url_uses_saved_dmm_setting() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=(
                "https://book.dmm.com/product/4493998/b000fhftx08481/"
            ),
        )

        result = DmmManualOfferService(session).save(
            preview=preview, confirmed=True
        )
        saved = session.get(StoreOffer, result.offer_id)
        assert saved is not None
        assert saved.store_item_id == "b000fhftx08481"
        assert saved.affiliate_url.startswith("https://al.dmm.com/")


def test_html_id_matches_x_without_reusing_it_for_blog() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML.replace(
                "xuanyilugang-008", "xuanyilugang-x-009"
            ),
        )

        assert preview.registration_allowed is True
        assert preview.matched_destination_key == "x_main"
        blog = next(
            link
            for link in preview.destination_links
            if link.destination_key == "blog_main"
        )
        x_link = next(
            link
            for link in preview.destination_links
            if link.destination_key == "x_main"
        )
        assert "af_id=xuanyilugang-008" in blog.affiliate_url
        assert "af_id=xuanyilugang-x-009" in x_link.affiliate_url
        assert preview.affiliate_url == blog.affiliate_url


def test_inactive_matching_profile_blocks_registration() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        AffiliateDestinationProfileRepository(session).upsert(
            provider="dmm",
            destination_type="wordpress",
            destination_key="blog_main",
            display_name="メインブログ",
            is_active=False,
        )

        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
        )

        assert "affiliate_profile_inactive" in preview.blocking_warnings


def test_duplicate_profile_affiliate_id_is_ambiguous() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        AffiliateDestinationProfileRepository(session).upsert(
            provider="dmm",
            destination_type="x",
            destination_key="x_main",
            display_name="公式X",
            affiliate_id="xuanyilugang-008",
        )

        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
        )

        assert "affiliate_profile_ambiguous" in preview.blocking_warnings


def test_repeated_html_save_does_not_duplicate_destination_links() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        service = DmmManualOfferService(session)
        preview = service.preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
        )

        first = service.save(preview=preview, confirmed=True)
        second = service.save(preview=preview, confirmed=True)

        links = session.scalars(select(StoreOfferAffiliateLink)).all()
        assert len(links) == 2
        assert first.affiliate_link_ids == second.affiliate_link_ids


def test_save_generates_links_for_active_profiles_only() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        AffiliateDestinationProfileRepository(session).upsert(
            provider="dmm",
            destination_type="x",
            destination_key="x_main",
            display_name="公式X",
            is_active=False,
        )
        service = DmmManualOfferService(session)
        preview = service.preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
        )

        service.save(preview=preview, confirmed=True)

        links = session.scalars(select(StoreOfferAffiliateLink)).all()
        assert len(links) == 1
        profile = session.get(
            AffiliateDestinationProfile, links[0].profile_id
        )
        assert profile.destination_key == "blog_main"


def test_x_only_profile_never_populates_legacy_blog_url() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = EbookItem(
            source_name="manual_test",
            source_item_id="dmm-x-only",
            title=TITLE,
            item_type="light_novel",
        )
        session.add(item)
        session.flush()
        AffiliateDestinationProfileRepository(session).upsert(
            provider="dmm",
            destination_type="x",
            destination_key="x_main",
            display_name="公式X",
            affiliate_id="xuanyilugang-x-009",
        )
        service = DmmManualOfferService(session)
        preview = service.preview_input(
            ebook_item_id=item.id,
            dmm_input=(
                "https://book.dmm.com/product/4493998/b000fhftx08481/"
            ),
        )

        result = service.save(preview=preview, confirmed=True)
        offer = session.get(StoreOffer, result.offer_id)
        links = session.scalars(select(StoreOfferAffiliateLink)).all()

        assert offer.affiliate_url is None
        assert len(links) == 1
        assert "af_id=xuanyilugang-x-009" in links[0].affiliate_url


def test_existing_dmm_offer_is_updated_once_and_blanks_are_preserved() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        item = _item_and_settings(session)
        existing = StoreOffer(
            ebook_item_id=item.id,
            store_name="dmm",
            store_item_id="old-product",
            product_url="https://book.dmm.com/product/old/old-product/",
            affiliate_url="https://al.dmm.com/old",
            currency="JPY",
            price_amount=700,
            verification_method="MANUAL_WEB_EDIT",
        )
        session.add(existing)
        session.flush()
        existing_id = existing.id

        preview = DmmManualOfferService(session).preview_input(
            ebook_item_id=item.id,
            dmm_input=HTML,
            price="",
            currency="",
        )
        result = DmmManualOfferService(session).save(
            preview=preview, confirmed=True
        )

        offers = session.scalars(
            select(StoreOffer).where(
                StoreOffer.ebook_item_id == item.id,
                StoreOffer.store_name == "dmm",
            )
        ).all()
        assert len(offers) == 1
        assert result.offer_id == existing_id
        assert offers[0].currency == "JPY"
        assert int(offers[0].price_amount) == 700

        DmmManualOfferService(session).save(
            preview=replace(
                preview,
                product_url="",
                affiliate_url="",
                price_amount=None,
                currency=None,
            ),
            confirmed=True,
        )
        assert offers[0].product_url == (
            "https://book.dmm.com/product/4493998/b000fhftx08481/"
        )
        assert offers[0].affiliate_url == AFFILIATE_URL
        assert offers[0].currency == "JPY"
        assert int(offers[0].price_amount) == 700
