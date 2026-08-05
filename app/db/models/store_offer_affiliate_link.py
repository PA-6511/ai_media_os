from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoreOfferAffiliateLink(Base):
    __tablename__ = "store_offer_affiliate_links"
    __table_args__ = (
        UniqueConstraint(
            "store_offer_id",
            "profile_id",
            name="store_offer_affiliate_profile_identity",
        ),
        CheckConstraint(
            "length(trim(affiliate_url)) > 0",
            name="store_offer_affiliate_url_not_blank",
        ),
        CheckConstraint(
            "length(trim(source_affiliate_id)) > 0",
            name="store_offer_source_affiliate_id_not_blank",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    store_offer_id: Mapped[str] = mapped_column(
        ForeignKey("store_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("affiliate_destination_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    affiliate_url: Mapped[str] = mapped_column(Text, nullable=False)
    generation_method: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    source_affiliate_id: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
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
