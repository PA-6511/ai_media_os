from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.repositories.affiliate_account_settings_repository import (
    AffiliateAccountSettingsRepository,
)


def create_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE affiliate_account_settings (
                    service_name TEXT PRIMARY KEY,
                    affiliate_id TEXT,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )
        )

    return Session(engine)


def test_save_and_get_affiliate_setting() -> None:
    with create_session() as session:
        repository = AffiliateAccountSettingsRepository(session)

        saved = repository.save(
            service_name="amazon",
            affiliate_id="example-22",
        )

        assert saved.service_name == "amazon"
        assert saved.affiliate_id == "example-22"
        assert saved.enabled is True

        loaded = repository.get(service_name="amazon")

        assert loaded is not None
        assert loaded.affiliate_id == "example-22"
        assert loaded.enabled is True


def test_save_updates_existing_setting() -> None:
    with create_session() as session:
        repository = AffiliateAccountSettingsRepository(session)

        repository.save(
            service_name="amazon",
            affiliate_id="old-22",
        )

        updated = repository.save(
            service_name="amazon",
            affiliate_id="new-22",
        )

        assert updated.affiliate_id == "new-22"
        assert updated.enabled is True


def test_unregister_keeps_row_and_clears_id() -> None:
    with create_session() as session:
        repository = AffiliateAccountSettingsRepository(session)

        repository.save(
            service_name="rakuten_kobo",
            affiliate_id="rakuten-test",
        )

        result = repository.unregister(
            service_name="rakuten_kobo",
        )

        assert result.service_name == "rakuten_kobo"
        assert result.affiliate_id is None
        assert result.enabled is False


def test_unsupported_service_is_rejected() -> None:
    with create_session() as session:
        repository = AffiliateAccountSettingsRepository(session)

        try:
            repository.save(
                service_name="unknown_store",
                affiliate_id="test",
            )
        except ValueError as error:
            assert str(error) == "unsupported service_name"
        else:
            raise AssertionError("ValueError was not raised")
