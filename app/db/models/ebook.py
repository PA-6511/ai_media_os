from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


_TRAILING_VOLUME_OR_EPISODE_PATTERN = re.compile(
    r"(?:\s*第?\s*\d+\s*[巻話])\s*$"
)


def normalize_series_classification_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def build_series_classification_identity(
    *,
    title: str | None,
    author_name: str | None,
    publisher_name: str | None,
) -> tuple[str, str, str, str] | None:
    normalized_title = normalize_series_classification_text(title)
    normalized_base_title = _TRAILING_VOLUME_OR_EPISODE_PATTERN.sub(
        "", normalized_title
    ).strip()
    normalized_author_name = normalize_series_classification_text(author_name)
    normalized_publisher_name = normalize_series_classification_text(
        publisher_name
    )
    if not all(
        (
            normalized_base_title,
            normalized_author_name,
            normalized_publisher_name,
        )
    ):
        return None
    key_material = "\0".join(
        (
            normalized_base_title,
            normalized_author_name,
            normalized_publisher_name,
        )
    )
    series_key = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
    return (
        series_key,
        normalized_base_title,
        normalized_author_name,
        normalized_publisher_name,
    )


class EbookItem(Base):
    __tablename__ = "ebook_items"
    __table_args__ = (
        UniqueConstraint(
            "source_name",
            "source_item_id",
            name="source_item_identity",
        ),
        CheckConstraint(
            "item_type IN "
            "('tankobon', 'light_novel', 'general_book', "
            "'single_chapter', 'magazine_episode', 'unknown')",
            name="valid_item_type",
        ),
        CheckConstraint(
            "workflow_status IN "
            "('NEW', 'REVIEW', 'READY', 'SCHEDULED', "
            "'PUBLISHED', 'HOLD', 'ERROR')",
            name="valid_workflow_status",
        ),
        CheckConstraint(
            "wordpress_status IN "
            "('NOT_CREATED', 'DRAFT', 'SCHEDULED', "
            "'PUBLISHED', 'ERROR')",
            name="valid_wordpress_status",
        ),
        CheckConstraint(
            "x_status IN "
            "('NOT_CREATED', 'DRAFT', 'POSTED', 'ERROR')",
            name="valid_x_status",
        ),
        CheckConstraint(
            "affiliate_status IN "
            "('UNCHECKED', 'MISSING', 'READY', 'REVIEW')",
            name="valid_affiliate_status",
        ),
        CheckConstraint(
            "image_status IN "
            "('UNCHECKED', 'MISSING', 'READY', 'REVIEW')",
            name="valid_image_status",
        ),
        CheckConstraint(
            "review_status IN "
            "('NOT_REVIEWED', 'IN_REVIEW', "
            "'APPROVED', 'REJECTED')",
            name="valid_review_status",
        ),
        CheckConstraint(
            "classification_source IS NULL OR classification_source IN "
            "('manual', 'series_rule')",
            name="valid_classification_source",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    source_name: Mapped[str] = mapped_column(String(64), nullable=False)
    source_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_discovery: Mapped[str | None] = mapped_column(String(64), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)

    isbn: Mapped[str | None] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    normalized_title: Mapped[str | None] = mapped_column(String(500), index=True)

    volume_label: Mapped[str | None] = mapped_column(String(100))
    author_name: Mapped[str | None] = mapped_column(String(255), index=True)
    publisher_name: Mapped[str | None] = mapped_column(String(255), index=True)
    series_name: Mapped[str | None] = mapped_column(String(255), index=True)

    release_date: Mapped[date | None] = mapped_column(Date, index=True)

    item_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unknown",
        index=True,
    )

    is_single_episode: Mapped[bool | None] = mapped_column(Boolean)
    is_split_edition: Mapped[bool | None] = mapped_column(Boolean)
    classification_source: Mapped[str | None] = mapped_column(String(32))

    is_excluded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    exclusion_reason: Mapped[str | None] = mapped_column(Text)

    workflow_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NEW",
        server_default="NEW",
        index=True,
    )

    wordpress_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NOT_CREATED",
        server_default="NOT_CREATED",
        index=True,
    )

    wordpress_post_id: Mapped[str | None] = mapped_column(
        String(64),
        index=True,
    )

    wordpress_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    x_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NOT_CREATED",
        server_default="NOT_CREATED",
        index=True,
    )

    x_post_id: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
    )

    affiliate_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UNCHECKED",
        server_default="UNCHECKED",
        index=True,
    )

    image_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="UNCHECKED",
        server_default="UNCHECKED",
        index=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="NOT_REVIEWED",
        server_default="NOT_REVIEWED",
        index=True,
    )

    publish_ready: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    last_error: Mapped[str | None] = mapped_column(Text)

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    offers: Mapped[list["StoreOffer"]] = relationship(
        back_populates="ebook_item",
        cascade="all, delete-orphan",
    )

    workflow_history: Mapped[list["WorkflowHistory"]] = relationship(
        back_populates="ebook_item",
        cascade="all, delete-orphan",
        order_by="WorkflowHistory.changed_at",
    )


class EbookSeriesClassificationRule(Base):
    __tablename__ = "ebook_series_classification_rules"
    __table_args__ = (
        Index(
            "ux_ebook_series_classification_rules_series_key",
            "series_key",
            unique=True,
        ),
        Index(
            "ix_ebook_series_classification_rules_active",
            "active",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    series_key: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_base_title: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    normalized_author_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    normalized_publisher_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_single_episode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_split_edition: Mapped[bool] = mapped_column(Boolean, nullable=False)
    source_ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class StoreOffer(Base):
    __tablename__ = "store_offers"
    __table_args__ = (
        UniqueConstraint(
            "ebook_item_id",
            "store_name",
            "store_item_id",
            name="ebook_store_offer_identity",
        ),
        CheckConstraint(
            "price_yen IS NULL OR price_yen >= 0",
            name="non_negative_price",
        ),
        CheckConstraint(
            "price_amount IS NULL OR price_amount >= 0",
            name="non_negative_price_amount",
        ),
        CheckConstraint(
            "discount_rate IS NULL "
            "OR (discount_rate >= 0 AND discount_rate <= 100)",
            name="valid_discount_rate",
        ),
        CheckConstraint(
            "point_rate IS NULL "
            "OR (point_rate >= 0 AND point_rate <= 100)",
            name="valid_point_rate",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    store_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    store_item_id: Mapped[str] = mapped_column(String(255), nullable=False)

    product_url: Mapped[str | None] = mapped_column(Text)
    affiliate_url: Mapped[str | None] = mapped_column(Text)

    price_yen: Mapped[int | None] = mapped_column()
    price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(12))
    availability_status: Mapped[str | None] = mapped_column(String(32))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_method: Mapped[str | None] = mapped_column(String(64))
    source_row_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    discount_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    point_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    sale_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    sale_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )

    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    ebook_item: Mapped[EbookItem] = relationship(back_populates="offers")


class WorkflowHistory(Base):
    __tablename__ = "workflow_history"
    __table_args__ = (
        CheckConstraint(
            "field_name IN "
            "('workflow_status', 'wordpress_status', 'x_status', "
            "'affiliate_status', 'image_status', 'review_status', "
            "'publish_ready', 'last_error')",
            name="valid_workflow_history_field",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    field_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)

    changed_by: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="system",
        server_default="system",
        index=True,
    )

    note: Mapped[str | None] = mapped_column(Text)

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        index=True,
    )

    ebook_item: Mapped[EbookItem] = relationship(
        back_populates="workflow_history",
    )


class CatalogEditHistory(Base):
    __tablename__ = "catalog_edit_history"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    ebook_item_id: Mapped[str] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )


class AffiliateAccountSettingRecord(Base):
    __tablename__ = "affiliate_account_settings"

    service_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    affiliate_id: Mapped[str | None] = mapped_column(Text)
    url_template: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")


class AffiliateSettingHistory(Base):
    __tablename__ = "affiliate_setting_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text)
    after_value: Mapped[str | None] = mapped_column(Text)
    change_reason: Mapped[str] = mapped_column(
        Text, nullable=False, default="local_web_edit"
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    changed_by: Mapped[str] = mapped_column(String(128), nullable=False)
