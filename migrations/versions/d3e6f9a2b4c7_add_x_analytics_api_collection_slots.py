"""add X Analytics API collection slots

Revision ID: d3e6f9a2b4c7
Revises: c9d4e7a1b2f6
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e6f9a2b4c7"
down_revision: Union[str, Sequence[str], None] = "c9d4e7a1b2f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "x_analytics_api_collection_slots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("post_id", sa.String(length=128), nullable=False),
        sa.Column("slot_id", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_path", sa.Text(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_sha256", sa.String(length=64), nullable=True),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("public_only", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(18, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("import_run_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('CLAIMED', 'FETCHED', 'SUCCEEDED', 'FAILED')",
            name="valid_x_analytics_api_collection_status",
        ),
        sa.CheckConstraint(
            "request_count >= 0",
            name="nonnegative_x_analytics_api_request_count",
        ),
        sa.CheckConstraint(
            "estimated_cost_usd >= 0",
            name="nonnegative_x_analytics_api_estimated_cost",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["x_analytics_import_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "account_identifier",
            "post_id",
            "slot_id",
            name="x_analytics_api_collection_identity",
        ),
    )
    for column in (
        "source",
        "account_identifier",
        "post_id",
        "scheduled_for",
        "status",
    ):
        op.create_index(
            f"ix_x_analytics_api_collection_slots_{column}",
            "x_analytics_api_collection_slots",
            [column],
        )


def downgrade() -> None:
    for column in (
        "status",
        "scheduled_for",
        "post_id",
        "account_identifier",
        "source",
    ):
        op.drop_index(
            f"ix_x_analytics_api_collection_slots_{column}",
            table_name="x_analytics_api_collection_slots",
        )
    op.drop_table("x_analytics_api_collection_slots")