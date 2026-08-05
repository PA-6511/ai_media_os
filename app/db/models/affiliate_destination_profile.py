from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AffiliateDestinationProfile(Base):
    __tablename__ = "affiliate_destination_profiles"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "destination_key",
            name="affiliate_destination_profile_identity",
        ),
        CheckConstraint(
            "length(trim(provider)) > 0",
            name="affiliate_destination_provider_not_blank",
        ),
        CheckConstraint(
            "length(trim(destination_type)) > 0",
            name="affiliate_destination_type_not_blank",
        ),
        CheckConstraint(
            "length(trim(destination_key)) > 0",
            name="affiliate_destination_key_not_blank",
        ),
        CheckConstraint(
            "length(trim(affiliate_id)) > 0",
            name="affiliate_destination_id_not_blank",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    provider: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    destination_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    destination_key: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    affiliate_id: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str | None] = mapped_column(String(64))
    channel_id: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
