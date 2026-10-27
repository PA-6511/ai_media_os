from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.orm import (
    sessionmaker,
)

from app.db.base import Base
from app.db.models import (
    EbookItem,
    StoreCoverPolicyAgreement,
    StoreOffer,
)
from app.integrations.amazon_creators_api_client import (
    AmazonCreatorsItem,
)
from app.services.official_cover_automation_service import (
    AMAZON_COVER_POLICY_VERSION,
)
from scripts import (
    process_cover_registration_jobs
    as worker,
)
from scripts.cover_registration_queue import (
    install,
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
    f"dp/{ASIN}/ref=nosim?"
    "tag=example-22"
)


class FakeAmazonClient:
    def __init__(self):
        self.calls = []
        self.closed = False

    def get_items(
        self,
        asins,
    ):
        self.calls.append(
            tuple(
                asins
            )
        )

        return (
            AmazonCreatorsItem(
                asin=ASIN,
                title="target",
                detail_page_url=(
                    "https://www.amazon.co.jp/"
                    f"dp/{ASIN}"
                ),
                cover_url=COVER_URL,
                authors=(),
                publisher=None,
                isbn_values=(),
                is_kindle=True,
                raw={},
            ),
        )

    def close(self):
        self.closed = True


def test_worker_uses_amazon_exact_asin_fallback(
    tmp_path,
    monkeypatch,
):
    db_path = (
        tmp_path
        / "cover-worker.db"
    )

    engine = create_engine(
        "sqlite:///"
        + str(
            db_path
        )
    )

    Base.metadata.create_all(
        engine
    )

    with sqlite3.connect(
        db_path
    ) as raw:
        install(
            raw
        )

    Factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with Factory() as session:
        session.add(
            EbookItem(
                id="target",
                source_name="fixture",
                source_item_id=(
                    "fixture-target"
                ),
                title="target",
                item_type="tankobon",
                image_status="MISSING",
                cover_source="UNKNOWN",
                cover_status=(
                    "HIDDEN_UNVERIFIED"
                ),
            )
        )

        session.add(
            StoreCoverPolicyAgreement(
                store_name="amazon",
                responsible_name="fixture",
                agreed=True,
                agreed_at=NOW,
                policy_version=(
                    AMAZON_COVER_POLICY_VERSION
                ),
                updated_at=NOW,
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
                affiliate_url=(
                    DESTINATION
                ),
                verification_method=(
                    "CREATORS_API"
                ),
            )
        )

        session.commit()

    with engine.connect() as conn:
        queued = conn.execute(
            text(
                """
                SELECT status
                FROM cover_registration_jobs
                WHERE ebook_item_id='target'
                """
            )
        ).scalar_one()

    assert queued == "PENDING"

    client = FakeAmazonClient()
    intervals = []

    def fake_from_environment(
        **kwargs,
    ):
        intervals.append(
            kwargs.get(
                "minimum_request_interval_seconds"
            )
        )
        return client

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        Factory,
    )

    monkeypatch.setattr(
        worker.AmazonCreatorsApiClient,
        "from_environment",
        staticmethod(
            fake_from_environment
        ),
    )

    monkeypatch.setattr(
        worker.time,
        "sleep",
        lambda _seconds: None,
    )

    worker.run(
        limit=20
    )

    with Factory() as session:
        item = session.get(
            EbookItem,
            "target",
        )

        assert (
            item.cover_source
            == "AMAZON_PA_API"
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
        assert (
            item.cover_status
            == "AUTO_ALLOWED"
        )
        assert (
            item.image_status
            == "READY"
        )

    with engine.connect() as conn:
        job = conn.execute(
            text(
                """
                SELECT
                    status,
                    reason,
                    attempts
                FROM cover_registration_jobs
                WHERE ebook_item_id='target'
                """
            )
        ).mappings().one()

    assert (
        job["status"]
        == "RESOLVED"
    )
    assert (
        job["reason"]
        == "AMAZON_COVER_SAVED"
    )
    assert (
        job["attempts"]
        == 1
    )

    assert client.calls == [
        (ASIN,)
    ]

    assert client.closed is True

    assert intervals == [
        1.1
    ]

    engine.dispose()



def test_worker_rejects_amazon_cover_after_revision_change(
    tmp_path,
    monkeypatch,
):
    db_path = tmp_path / "cover-worker-race.db"

    engine = create_engine(
        "sqlite:///" + str(db_path)
    )

    Base.metadata.create_all(engine)

    with sqlite3.connect(db_path) as raw:
        install(raw)

    Factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with Factory() as session:
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
            StoreCoverPolicyAgreement(
                store_name="amazon",
                responsible_name="fixture",
                agreed=True,
                agreed_at=NOW,
                policy_version=(
                    AMAZON_COVER_POLICY_VERSION
                ),
                updated_at=NOW,
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
                verification_method="CREATORS_API",
            )
        )

        session.commit()

    class VerifiedResult:
        status = "VERIFIED_DRY_RUN"
        reason_code = None
        changed = False
        source_item_id = ASIN
        cover_image_url = COVER_URL
        cover_destination_url = DESTINATION

    def fake_amazon_fetch(item_id):
        assert item_id == "target"

        # Simulate StoreOffer changing while
        # the external Amazon request is in flight.
        with Factory() as session:
            offer = session.get(
                StoreOffer,
                "offer-amazon",
            )
            offer.product_url = (
                "https://www.amazon.co.jp/"
                f"dp/{ASIN}?race=1"
            )
            session.commit()

        return VerifiedResult()

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        Factory,
    )

    monkeypatch.setattr(
        worker,
        "_run_amazon_fallback",
        fake_amazon_fetch,
    )

    monkeypatch.setattr(
        worker.time,
        "sleep",
        lambda _seconds: None,
    )

    worker.run(limit=20)

    with Factory() as session:
        item = session.get(
            EbookItem,
            "target",
        )

        assert item.cover_source == "UNKNOWN"
        assert item.cover_source_item_id is None
        assert item.cover_image_url is None
        assert item.cover_destination_url is None
        assert (
            item.cover_status
            == "HIDDEN_UNVERIFIED"
        )
        assert item.image_status == "MISSING"

    with engine.connect() as conn:
        job = conn.execute(
            text(
                """
                SELECT
                    revision,
                    status,
                    reason,
                    attempts
                FROM cover_registration_jobs
                WHERE ebook_item_id='target'
                """
            )
        ).mappings().one()

    assert job["revision"] == 2
    assert job["status"] == "PENDING"
    assert job["reason"] == "URL_REGISTERED"
    assert job["attempts"] == 0

    engine.dispose()
