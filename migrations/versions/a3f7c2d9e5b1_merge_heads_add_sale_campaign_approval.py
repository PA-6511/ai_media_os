"""merge heads and add sale campaign approval requests

Revision ID: a3f7c2d9e5b1
Revises: b6e1d4a8c3f2, c920a1b2c3d4, e8f1a6c4d2b7
Create Date: 2026-09-27
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3f7c2d9e5b1"
down_revision: Union[str, Sequence[str], None] = (
    "b6e1d4a8c3f2",
    "c920a1b2c3d4",
    "e8f1a6c4d2b7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sale_campaign_approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "request_nonce_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("slack_team_id", sa.String(length=64), nullable=True),
        sa.Column("slack_channel_id", sa.String(length=64), nullable=True),
        sa.Column("slack_message_ts", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ("
            "'PENDING', 'APPROVED', 'REJECTED', 'ON_HOLD', "
            "'EXPIRED', 'CANCELLED'"
            ")",
            name="valid_sale_campaign_approval_status",
        ),
        sa.CheckConstraint(
            "expires_at > requested_at",
            name="valid_sale_campaign_approval_expiration",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["sale_roundup_campaigns.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "request_nonce_hash",
            name="uq_sale_campaign_approval_nonce_hash",
        ),
    )
    op.create_index(
        "ix_sale_campaign_approval_campaign_id",
        "sale_campaign_approval_requests",
        ["campaign_id"],
    )
    op.create_index(
        "ix_sale_campaign_approval_status",
        "sale_campaign_approval_requests",
        ["status"],
    )
    op.create_index(
        "ix_sale_campaign_approval_expires_at",
        "sale_campaign_approval_requests",
        ["expires_at"],
    )
    op.create_index(
        "uq_sale_campaign_approval_pending_campaign",
        "sale_campaign_approval_requests",
        ["campaign_id"],
        unique=True,
        sqlite_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_sale_campaign_approval_pending_campaign",
        table_name="sale_campaign_approval_requests",
    )
    op.drop_index(
        "ix_sale_campaign_approval_expires_at",
        table_name="sale_campaign_approval_requests",
    )
    op.drop_index(
        "ix_sale_campaign_approval_status",
        table_name="sale_campaign_approval_requests",
    )
    op.drop_index(
        "ix_sale_campaign_approval_campaign_id",
        table_name="sale_campaign_approval_requests",
    )
    op.drop_table("sale_campaign_approval_requests")
