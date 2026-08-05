from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.affiliate_account_settings_service import (
    AffiliateAccountSettingsService,
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

        connection.execute(
            text(
                """
                INSERT INTO affiliate_account_settings (
                    service_name,
                    affiliate_id,
                    enabled,
                    updated_at
                ) VALUES
                    ('amazon', NULL, 0, '2026-07-21T00:00:00+00:00'),
                    ('rakuten_kobo', NULL, 0, '2026-07-21T00:00:00+00:00'),
                    ('dmm', NULL, 0, '2026-07-21T00:00:00+00:00')
                """
            )
        )

    return Session(engine)


def test_register_and_get_affiliate_id() -> None:
    with create_session() as session:
        service = AffiliateAccountSettingsService(session)

        result = service.register(
            service_name="amazon",
            affiliate_id="ktkr77-22",
        )

        assert result.configured is True
        assert result.enabled is True
        assert result.masked_affiliate_id != "ktkr77-22"
        assert service.get_affiliate_id(
            service_name="amazon"
        ) == "ktkr77-22"


def test_unregister_disables_future_generation() -> None:
    with create_session() as session:
        service = AffiliateAccountSettingsService(session)

        service.register(
            service_name="amazon",
            affiliate_id="ktkr77-22",
        )

        result = service.unregister(
            service_name="amazon",
        )

        assert result.configured is False
        assert result.enabled is False
        assert service.get_affiliate_id(
            service_name="amazon"
        ) is None


def test_list_settings_returns_all_services() -> None:
    with create_session() as session:
        service = AffiliateAccountSettingsService(session)

        settings = service.list_settings()

        assert {
            setting.service_name
            for setting in settings
        } == {
            "amazon",
            "rakuten_kobo",
            "dmm",
        }


def test_mask_affiliate_id() -> None:
    assert (
        AffiliateAccountSettingsService.mask_affiliate_id(None)
        == "未登録"
    )

    masked = (
        AffiliateAccountSettingsService.mask_affiliate_id(
            "ktkr77-22"
        )
    )

    assert masked.startswith("ktk")
    assert masked.endswith("-22")
    assert "ktkr77-22" not in masked
