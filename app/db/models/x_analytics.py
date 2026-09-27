from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class XAnalyticsImportRun(Base):
    __tablename__ = "x_analytics_import_runs"
    __table_args__ = (
        UniqueConstraint("import_key", name="x_analytics_import_key"),
        CheckConstraint(
            "metric_scope IN ('lifetime', 'interval', 'unknown')",
            name="valid_x_analytics_import_scope",
        ),
        CheckConstraint(
            "status IN ('PROCESSING', 'SUCCEEDED')",
            name="valid_x_analytics_import_status",
        ),
        CheckConstraint(
            "metric_scope != 'interval' OR "
            "(interval_start_at IS NOT NULL AND interval_end_at IS NOT NULL "
            "AND interval_end_at > interval_start_at)",
            name="valid_x_analytics_import_interval",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    import_key: Mapped[str] = mapped_column(String(64), nullable=False)
    csv_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    interval_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    interval_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    csv_timezone: Mapped[str | None] = mapped_column(String(64))
    reach_metric_name: Mapped[str | None] = mapped_column(String(32))
    headers_json: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PROCESSING"
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    rows: Mapped[list["XAnalyticsImportRow"]] = relationship(
        back_populates="import_run", cascade="all, delete-orphan"
    )


class XAnalyticsMetricSnapshot(Base):
    __tablename__ = "x_analytics_metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "observation_key", name="x_analytics_observation_identity"
        ),
        CheckConstraint(
            "metric_scope IN ('lifetime', 'interval', 'unknown')",
            name="valid_x_analytics_snapshot_scope",
        ),
        CheckConstraint(
            "metric_scope != 'interval' OR "
            "(interval_start_at IS NOT NULL AND interval_end_at IS NOT NULL "
            "AND interval_end_at > interval_start_at)",
            name="valid_x_analytics_snapshot_interval",
        ),
        CheckConstraint(
            "link_status IN ('MATCHED', 'UNMATCHED', 'AMBIGUOUS')",
            name="valid_x_analytics_link_status",
        ),
        *(
            CheckConstraint(
                f"{field_name} IS NULL OR {field_name} >= 0",
                name=f"nonnegative_x_analytics_{field_name}",
            )
            for field_name in (
                "impressions",
                "views",
                "engagements",
                "link_clicks",
                "profile_clicks",
                "likes",
                "reposts",
                "replies",
                "follows",
            )
        ),
        CheckConstraint(
            "engagement_rate IS NULL OR engagement_rate >= 0",
            name="nonnegative_x_analytics_engagement_rate",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    observation_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    post_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    text: Mapped[str | None] = mapped_column(Text)
    post_type: Mapped[str | None] = mapped_column(String(64))
    post_type_source: Mapped[str | None] = mapped_column(String(64))
    metric_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    interval_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    interval_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    impressions: Mapped[int | None] = mapped_column(Integer)
    views: Mapped[int | None] = mapped_column(Integer)
    engagements: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    engagement_rate_format: Mapped[str | None] = mapped_column(String(32))
    link_clicks: Mapped[int | None] = mapped_column(Integer)
    profile_clicks: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    reposts: Mapped[int | None] = mapped_column(Integer)
    replies: Mapped[int | None] = mapped_column(Integer)
    follows: Mapped[int | None] = mapped_column(Integer)
    reach_metric_name: Mapped[str | None] = mapped_column(String(32))
    reach_metric_source_header: Mapped[str | None] = mapped_column(String(255))
    ebook_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("ebook_items.id", ondelete="SET NULL"), index=True
    )
    store_name: Mapped[str | None] = mapped_column(String(64))
    has_cover: Mapped[bool | None] = mapped_column()
    link_status: Mapped[str] = mapped_column(String(16), nullable=False)
    link_source: Mapped[str | None] = mapped_column(String(128))
    post_evidence_path: Mapped[str | None] = mapped_column(Text)
    first_import_run_id: Mapped[str] = mapped_column(
        ForeignKey("x_analytics_import_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    last_import_run_id: Mapped[str] = mapped_column(
        ForeignKey("x_analytics_import_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class XAnalyticsImportRow(Base):
    __tablename__ = "x_analytics_import_rows"
    __table_args__ = (
        UniqueConstraint(
            "import_run_id", "row_number", name="x_analytics_import_row_identity"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    import_run_id: Mapped[str] = mapped_column(
        ForeignKey("x_analytics_import_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("x_analytics_metric_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    unknown_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_headers_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    import_run: Mapped[XAnalyticsImportRun] = relationship(back_populates="rows")


class XAnalyticsApiCollectionSlot(Base):
    __tablename__ = "x_analytics_api_collection_slots"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "account_identifier",
            "post_id",
            "slot_id",
            name="x_analytics_api_collection_identity",
        ),
        CheckConstraint(
            "status IN ('CLAIMED', 'FETCHED', 'SUCCEEDED', 'FAILED')",
            name="valid_x_analytics_api_collection_status",
        ),
        CheckConstraint(
            "request_count >= 0",
            name="nonnegative_x_analytics_api_request_count",
        ),
        CheckConstraint(
            "estimated_cost_usd >= 0",
            name="nonnegative_x_analytics_api_estimated_cost",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    account_identifier: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    post_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    slot_id: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    evidence_path: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_sha256: Mapped[str | None] = mapped_column(String(64))
    response_json: Mapped[str | None] = mapped_column(Text)
    public_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    request_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    estimated_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal("0"), server_default="0"
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    import_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("x_analytics_import_runs.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class XAnalyticsApiBudgetRequest(Base):
    __tablename__ = "x_analytics_api_budget_requests"
    __table_args__ = (
        UniqueConstraint("request_key", name="x_analytics_api_budget_request_key"),
        CheckConstraint(
            "status IN ('RESERVED', 'AWAITING_BUDGET_APPROVAL', 'APPROVED', "
            "'REJECTED', 'CONSUMED', 'CANCELLED')",
            name="valid_x_analytics_api_budget_status",
        ),
        CheckConstraint(
            "reserved_cost_usd >= 0 AND additional_cost_usd >= 0 "
            "AND estimated_used_usd >= 0",
            name="nonnegative_x_analytics_api_budget_amounts",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    request_key: Mapped[str] = mapped_column(String(64), nullable=False)
    budget_month_utc: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    base_limit_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    approved_limit_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    estimated_used_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    additional_cost_usd: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    targets_json: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    impact_if_skipped: Mapped[str] = mapped_column(Text, nullable=False)
    private_metrics_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    notification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_REQUESTED", server_default="NOT_REQUESTED"
    )
    notification_error: Mapped[str | None] = mapped_column(String(255))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reservation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    decision: Mapped[str | None] = mapped_column(String(16))
    decided_by: Mapped[str | None] = mapped_column(String(128))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_note: Mapped[str | None] = mapped_column(Text)
    decision_notification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NOT_REQUESTED", server_default="NOT_REQUESTED"
    )
    decision_notification_error: Mapped[str | None] = mapped_column(String(255))
    decision_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )