from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    StoreCoverPolicyAgreement,
    StoreOffer,
)
from app.integrations.amazon_creators_api_client import (
    AmazonCreatorsItem,
)
from app.services.amazon_creators_cover_persistence_service import (
    AmazonCreatorsCoverPersistenceService,
)
from app.services.official_cover_automation_service import (
    AMAZON_COVER_POLICY_VERSION,
)


NOW = datetime(
    2026,
    9,
    23,
    tzinfo=timezone.utc,
)

ASIN = "B0HJ7C2K1D"

COVER_URL = (
    "https://m.media-amazon.com/"
    "images/I/example._SL500_.jpg"
)

DESTINATION = (
    "https://www.amazon.co.jp/"
    f"dp/{ASIN}/ref=nosim?tag=example-22"
)


class FakeClient:
    def __init__(
        self,
        *,
        asin: str = ASIN,
        cover_url: str | None = COVER_URL,
    ) -> None:
        self.asin = asin
        self.cover_url = cover_url
        self.calls = []

    def get_items(self, asins):
        self.calls.append(
            tuple(asins)
        )

        return (
            AmazonCreatorsItem(
                asin=self.asin,
                title="target",
                detail_page_url=(
                    "https://www.amazon.co.jp/"
                    f"dp/{self.asin}"
                ),
                cover_url=self.cover_url,
                authors=(),
                publisher=None,
                isbn_values=(),
                is_kindle=True,
                raw={},
            ),
        )


def make_engine(tmp_path):
    engine = create_engine(
        "sqlite:///"
        + str(
            tmp_path
            / "amazon_cover_persistence.db"
        )
    )
    Base.metadata.create_all(engine)
    return engine


def seed(
    session: Session,
    *,
    agreed: bool = True,
) -> None:
    session.add(
        EbookItem(
            id="target",
            source_name="fixture",
            source_item_id="fixture-target",
            title="target",
            item_type="tankobon",
            image_status="MISSING",
            cover_source="UNKNOWN",
            cover_status="HIDDEN_UNVERIFIED",
        )
    )

    session.add(
        StoreOffer(
            id="offer-amazon",
            ebook_item_id="target",
            store_name="amazon",
            store_item_id=ASIN,
            product_url=(
                "https://www.amazon.co.jp/"
                f"dp/{ASIN}"
            ),
            affiliate_url=DESTINATION,
            verification_method=(
                "CREATORS_API"
            ),
        )
    )

    session.add(
        StoreCoverPolicyAgreement(
            store_name="amazon",
            responsible_name="fixture",
            agreed=agreed,
            agreed_at=NOW,
            policy_version=(
                AMAZON_COVER_POLICY_VERSION
            ),
            updated_at=NOW,
        )
    )

    session.commit()


def test_execute_persists_exact_asin_cover(
    tmp_path,
):
    engine = make_engine(
        tmp_path
    )

    with Session(engine) as session:
        seed(session)

        client = FakeClient()

        result = (
            AmazonCreatorsCoverPersistenceService(
                session,
                client,
                now=lambda: NOW,
            ).persist_item(
                "target",
                execute=True,
            )
        )

        assert result.status == (
            "AUTO_ALLOWED"
        )
        assert result.changed is True
        assert client.calls == [
            (ASIN,)
        ]

        item = session.get(
            EbookItem,
            "target",
        )

        assert item.cover_source == (
            "AMAZON_PA_API"
        )
        assert (
            item.cover_source_item_id
            == ASIN
        )
        assert (
            item.cover_image_url
            == COVER_URL
        )
        assert (
            item.cover_destination_url
            == DESTINATION
        )
        assert item.cover_status == (
            "AUTO_ALLOWED"
        )
        assert item.image_status == (
            "READY"
        )
        assert (
            item.cover_policy_version
            == AMAZON_COVER_POLICY_VERSION
        )

    engine.dispose()


def test_dry_run_does_not_write(
    tmp_path,
):
    engine = make_engine(
        tmp_path
    )

    with Session(engine) as session:
        seed(session)

        client = FakeClient()

        result = (
            AmazonCreatorsCoverPersistenceService(
                session,
                client,
            ).persist_item(
                "target",
                execute=False,
            )
        )

        assert result.status == (
            "VERIFIED_DRY_RUN"
        )

        session.expire_all()

        item = session.get(
            EbookItem,
            "target",
        )

        assert item.cover_source == (
            "UNKNOWN"
        )
        assert item.cover_image_url is None
        assert item.cover_status == (
            "HIDDEN_UNVERIFIED"
        )

    engine.dispose()


def test_existing_allowed_cover_is_noop(
    tmp_path,
):
    engine = make_engine(
        tmp_path
    )

    with Session(engine) as session:
        seed(session)

        item = session.get(
            EbookItem,
            "target",
        )
        item.cover_source = (
            "RAKUTEN_KOBO_API"
        )
        item.cover_source_item_id = (
            "4335060800320"
        )
        item.cover_image_url = (
            "https://thumbnail.image."
            "rakuten.co.jp/test.jpg"
        )
        item.cover_destination_url = (
            "https://books.rakuten.co.jp/"
        )
        item.cover_status = (
            "AUTO_ALLOWED"
        )
        item.image_status = (
            "READY"
        )
        session.commit()

        client = FakeClient()

        result = (
            AmazonCreatorsCoverPersistenceService(
                session,
                client,
            ).persist_item(
                "target",
                execute=True,
            )
        )

        assert result.status == (
            "NOOP_ALREADY_ALLOWED"
        )
        assert client.calls == []

    engine.dispose()


def test_asin_mismatch_does_not_write(
    tmp_path,
):
    engine = make_engine(
        tmp_path
    )

    with Session(engine) as session:
        seed(session)

        client = FakeClient(
            asin="B000000000",
        )

        result = (
            AmazonCreatorsCoverPersistenceService(
                session,
                client,
            ).persist_item(
                "target",
                execute=True,
            )
        )

        assert result.status == (
            "UNAVAILABLE"
        )
        assert result.reason_code == (
            "AMAZON_ASIN_MISMATCH"
        )

        item = session.get(
            EbookItem,
            "target",
        )

        assert item.cover_image_url is None
        assert item.cover_source == (
            "UNKNOWN"
        )

    engine.dispose()
