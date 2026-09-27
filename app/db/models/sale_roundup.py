"""Additive sale/copy tables; existing ebook and approval state stays untouched."""
from sqlalchemy import String, Text, Integer, Float, JSON, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class SaleCampaign(Base):
    __tablename__ = "sale_roundup_campaigns"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    starts_at: Mapped[str] = mapped_column(String(40))
    ends_at: Mapped[str] = mapped_column(String(40))
    imported_at: Mapped[str] = mapped_column(String(40))
    source_generated_at: Mapped[str] = mapped_column(String(40))

class SaleOffer(Base):
    __tablename__ = "sale_roundup_offers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("sale_roundup_campaigns.id"), index=True)
    ebook_item_id: Mapped[str] = mapped_column(String(128))
    data: Mapped[dict] = mapped_column(JSON)
    block_reasons: Mapped[list] = mapped_column(JSON)

class SaleExperiment(Base):
    __tablename__ = "sale_copy_experiments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("sale_roundup_campaigns.id"), index=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    payload: Mapped[dict] = mapped_column(JSON)
    wordpress_state: Mapped[str] = mapped_column(String(32), default="PREPARED")
    wordpress_post_id: Mapped[int | None] = mapped_column(Integer)
    article_url: Mapped[str | None] = mapped_column(Text)

class SaleCopyVariant(Base):
    __tablename__ = "sale_copy_variants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("sale_copy_experiments.id"), index=True)
    components: Mapped[dict] = mapped_column(JSON)
    text: Mapped[str] = mapped_column(Text)
    draft_request: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(16), default="PENDING")
    reviewed_by: Mapped[str | None] = mapped_column(String(128))
    reviewed_at: Mapped[str | None] = mapped_column(String(40))

class SaleMetricSnapshot(Base):
    __tablename__ = "sale_copy_metric_snapshots"
    __table_args__ = tuple(CheckConstraint(f"{name} IS NULL OR {name} >= 0", name=f"sale_{name}_nonnegative")
        for name in ("impressions","clicks","orders","order_revenue","referral_fee"))
    post_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    variant_id: Mapped[str] = mapped_column(ForeignKey("sale_copy_variants.id"), index=True)
    posted_at: Mapped[str] = mapped_column(String(40))
    observed_at: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(128))
    attribution_basis: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(3))
    impressions: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    orders: Mapped[int | None] = mapped_column(Integer)
    order_revenue: Mapped[float | None] = mapped_column(Float)
    referral_fee: Mapped[float | None] = mapped_column(Float)

class SaleOperationSetting(Base):
    __tablename__ = "sale_roundup_settings"
    __table_args__ = (CheckConstraint("mode IN ('STOP','MANUAL','SEMI_AUTO')",name="sale_valid_mode"),)
    id: Mapped[str] = mapped_column(String(32),primary_key=True)
    mode: Mapped[str] = mapped_column(String(16))
    last_run: Mapped[dict | None] = mapped_column(JSON)
