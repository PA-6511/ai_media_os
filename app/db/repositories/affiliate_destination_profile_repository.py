from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AffiliateDestinationProfile


SAFE_KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SAFE_AFFILIATE_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._:@/+\-=]{1,255}$"
)
SAFE_CHANNEL_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class AffiliateDestinationProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(
        self, *, provider: str, destination_key: str
    ) -> AffiliateDestinationProfile | None:
        return self.session.scalar(
            select(AffiliateDestinationProfile).where(
                AffiliateDestinationProfile.provider
                == self._normalize_key(provider, "provider"),
                AffiliateDestinationProfile.destination_key
                == self._normalize_key(destination_key, "destination_key"),
            )
        )

    def list_for_provider(
        self, *, provider: str, active_only: bool = False
    ) -> list[AffiliateDestinationProfile]:
        statement = select(AffiliateDestinationProfile).where(
            AffiliateDestinationProfile.provider
            == self._normalize_key(provider, "provider")
        )
        if active_only:
            statement = statement.where(
                AffiliateDestinationProfile.is_active.is_(True)
            )
        return list(
            self.session.scalars(
                statement.order_by(
                    AffiliateDestinationProfile.destination_key,
                    AffiliateDestinationProfile.id,
                )
            )
        )

    def list_active(
        self, *, provider: str
    ) -> list[AffiliateDestinationProfile]:
        return self.list_for_provider(provider=provider, active_only=True)

    def find_by_affiliate_id(
        self, *, provider: str, affiliate_id: str
    ) -> list[AffiliateDestinationProfile]:
        normalized_id = str(affiliate_id or "").strip()
        if not normalized_id:
            return []
        return list(
            self.session.scalars(
                select(AffiliateDestinationProfile)
                .where(
                    AffiliateDestinationProfile.provider
                    == self._normalize_key(provider, "provider"),
                    AffiliateDestinationProfile.affiliate_id
                    == normalized_id,
                )
                .order_by(
                    AffiliateDestinationProfile.destination_key,
                    AffiliateDestinationProfile.id,
                )
            )
        )

    def upsert(
        self,
        *,
        provider: str,
        destination_type: str,
        destination_key: str,
        display_name: str,
        affiliate_id: str = "",
        channel: str = "",
        channel_id: str = "",
        is_active: bool | None = None,
    ) -> tuple[AffiliateDestinationProfile, dict[str, tuple[object, object]]]:
        normalized_provider = self._normalize_key(provider, "provider")
        normalized_type = self._normalize_key(
            destination_type, "destination_type"
        )
        normalized_key = self._normalize_key(
            destination_key, "destination_key"
        )
        normalized_name = str(display_name or "").strip()
        normalized_id = str(affiliate_id or "").strip()
        normalized_channel = str(channel or "").strip()
        normalized_channel_id = str(channel_id or "").strip()

        current = self.get(
            provider=normalized_provider,
            destination_key=normalized_key,
        )
        if current is None and not normalized_name:
            raise ValueError("display_name is required")
        if current is None and not normalized_id:
            raise ValueError("affiliate_id is required")
        effective_id = normalized_id or (
            current.affiliate_id if current is not None else ""
        )
        self._validate_affiliate_id(effective_id)
        effective_channel = normalized_channel or (
            current.channel if current is not None else "toolbar"
        )
        effective_channel_id = normalized_channel_id or (
            current.channel_id if current is not None else "text"
        )
        self._validate_channel(effective_channel, "channel")
        self._validate_channel(effective_channel_id, "channel_id")

        created = current is None
        profile = current or AffiliateDestinationProfile(
            provider=normalized_provider,
            destination_key=normalized_key,
        )
        if created:
            self.session.add(profile)

        desired = {
            "destination_type": normalized_type,
            "display_name": normalized_name or profile.display_name,
            "affiliate_id": effective_id,
            "channel": effective_channel,
            "channel_id": effective_channel_id,
            "is_active": (
                bool(is_active)
                if is_active is not None
                else (profile.is_active if not created else True)
            ),
        }
        changes: dict[str, tuple[object, object]] = {}
        for field_name, after_value in desired.items():
            before_value = getattr(profile, field_name)
            if before_value != after_value:
                changes[field_name] = (before_value, after_value)
                setattr(profile, field_name, after_value)
        self.session.flush()
        return profile, changes

    @staticmethod
    def _normalize_key(value: str, field_name: str) -> str:
        normalized = str(value or "").strip().lower()
        if not SAFE_KEY_PATTERN.fullmatch(normalized):
            raise ValueError(f"{field_name} is invalid")
        return normalized

    @staticmethod
    def _validate_affiliate_id(value: str) -> None:
        if not SAFE_AFFILIATE_ID_PATTERN.fullmatch(value):
            raise ValueError("affiliate_id is invalid")

    @staticmethod
    def _validate_channel(value: str | None, field_name: str) -> None:
        if value and not SAFE_CHANNEL_PATTERN.fullmatch(value):
            raise ValueError(f"{field_name} is invalid")
