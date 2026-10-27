from __future__ import annotations

from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AmazonXTrackingIdPool(Base):
    __tablename__ = "amazon_x_tracking_id_pool"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    tracking_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="AVAILABLE",
    )

    experiment_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    variant_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    wordpress_post_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "tracking_id",
            name="uq_amazon_x_tracking_pool_tracking_id",
        ),
        UniqueConstraint(
            "variant_id",
            name="uq_amazon_x_tracking_pool_variant_id",
        ),
        CheckConstraint(
            "length(trim(tracking_id)) > 0",
            name="ck_amazon_x_tracking_pool_tracking_id_not_blank",
        ),
        CheckConstraint(
            "status IN ('AVAILABLE','ASSIGNED','DISABLED')",
            name="ck_amazon_x_tracking_pool_status",
        ),
        CheckConstraint(
            "("
            "status IN ('AVAILABLE','DISABLED') "
            "AND experiment_id IS NULL "
            "AND variant_id IS NULL "
            "AND wordpress_post_id IS NULL "
            "AND assigned_at IS NULL"
            ") OR ("
            "status = 'ASSIGNED' "
            "AND experiment_id IS NOT NULL "
            "AND length(experiment_id) = 64 "
            "AND variant_id IS NOT NULL "
            "AND length(variant_id) = 64 "
            "AND wordpress_post_id IS NOT NULL "
            "AND wordpress_post_id > 0 "
            "AND assigned_at IS NOT NULL"
            ")",
            name="ck_amazon_x_tracking_pool_state_semantics",
        ),
        Index(
            "ix_amazon_x_tracking_pool_status",
            "status",
        ),
        Index(
            "ix_amazon_x_tracking_pool_experiment",
            "experiment_id",
        ),
    )
