"""add X Analytics API budget requests

Revision ID: f4a7c1d9e2b5
Revises: d3e6f9a2b4c7
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a7c1d9e2b5"
down_revision: Union[str, Sequence[str], None] = "d3e6f9a2b4c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "x_analytics_api_budget_requests",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("budget_month_utc", sa.String(7), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("base_limit_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("approved_limit_usd", sa.Numeric(18, 6), nullable=True),
        sa.Column("estimated_used_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("reserved_cost_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("additional_cost_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("targets_json", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("impact_if_skipped", sa.Text(), nullable=False),
        sa.Column("private_metrics_deadline_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("notification_status", sa.String(32), server_default="NOT_REQUESTED", nullable=False),
        sa.Column("notification_error", sa.String(255)),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True)),
        sa.Column("decision", sa.String(16)),
        sa.Column("decided_by", sa.String(128)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_note", sa.Text),
        sa.Column("decision_notification_status", sa.String(32), server_default="NOT_REQUESTED", nullable=False),
        sa.Column("decision_notification_error", sa.String(255)),
        sa.Column("decision_notified_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('RESERVED', 'AWAITING_BUDGET_APPROVAL', 'APPROVED', 'REJECTED', 'CONSUMED', 'CANCELLED')",
            name="valid_x_analytics_api_budget_status",
        ),
        sa.CheckConstraint(
            "reserved_cost_usd >= 0 AND additional_cost_usd >= 0 AND estimated_used_usd >= 0",
            name="nonnegative_x_analytics_api_budget_amounts",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key", name="x_analytics_api_budget_request_key"),
    )
    op.create_index("ix_x_analytics_api_budget_requests_budget_month_utc", "x_analytics_api_budget_requests", ["budget_month_utc"])
    op.create_index("ix_x_analytics_api_budget_requests_status", "x_analytics_api_budget_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_x_analytics_api_budget_requests_status", table_name="x_analytics_api_budget_requests")
    op.drop_index("ix_x_analytics_api_budget_requests_budget_month_utc", table_name="x_analytics_api_budget_requests")
    op.drop_table("x_analytics_api_budget_requests")