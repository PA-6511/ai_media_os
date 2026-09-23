from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models import EbookItem, StoreOffer
from scripts import process_cover_registration_jobs as worker


ASIN = "B0HHM2YH53"


def _build_db(tmp_path):
    engine = create_engine(
        "sqlite:///"
        + str(
            tmp_path / "cover_worker.db"
        )
    )

    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE cover_registration_jobs (
                ebook_item_id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL DEFAULT 1,
                attempts INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PENDING',
                reason TEXT NOT NULL DEFAULT 'URL_REGISTERED',
                next_attempt_at INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0
            )
            """
        )

    factory = sessionmaker(bind=engine)

    with Session(engine) as session:
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
                id="amazon-target",
                ebook_item_id="target",
                store_name="amazon",
                store_item_id=ASIN,
                product_url=(
                    "https://www.amazon.co.jp/"
                    f"dp/{ASIN}"
                ),
                affiliate_url=(
                    "https://www.amazon.co.jp/"
                    f"dp/{ASIN}/ref=nosim?"
                    "tag=example-22"
                ),
                verification_method="CREATORS_API",
            )
        )

        session.commit()

        session.execute(
            text(
                """
                INSERT INTO cover_registration_jobs (
                    ebook_item_id,
                    revision,
                    attempts,
                    status,
                    reason,
                    next_attempt_at,
                    updated_at
                )
                VALUES (
                    'target',
                    1,
                    0,
                    'PENDING',
                    'URL_REGISTERED',
                    0,
                    0
                )
                """
            )
        )

        session.commit()

    return engine, factory


def test_exactly_one_amazon_offer_routes_to_fallback(
    tmp_path,
    monkeypatch,
):
    engine, factory = _build_db(
        tmp_path
    )

    calls = []

    def fake_amazon_fallback(
        item_id,
    ):
        calls.append(item_id)

        return SimpleNamespace(
            status="AUTO_ALLOWED",
            reason_code=None,
        )

    monkeypatch.setattr(
        worker,
        "SessionLocal",
        factory,
    )

    monkeypatch.setattr(
        worker,
        "_run_amazon_fallback",
        fake_amazon_fallback,
    )

    monkeypatch.setattr(
        worker.time,
        "sleep",
        lambda _: None,
    )

    worker.run(limit=1)

    assert calls == ["target"]

    with Session(engine) as session:
        row = session.execute(
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
        ).one()

        assert row == (
            "RESOLVED",
            "AMAZON_COVER_SAVED",
            1,
        )

    engine.dispose()
