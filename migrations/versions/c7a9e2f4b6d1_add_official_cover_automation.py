"""add official API cover automation and store policy agreements

Revision ID: c7a9e2f4b6d1
Revises: b6f1d8e3c2a7
Create Date: 2026-08-14

Existing cover data is deliberately migrated to UNKNOWN/HIDDEN_UNVERIFIED.
No existing page-derived image URL is promoted to an approved API cover.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7a9e2f4b6d1"
down_revision: Union[str, Sequence[str], None] = "b6f1d8e3c2a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebook_items",
        sa.Column(
            "cover_source",
            sa.String(length=32),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )
    op.add_column(
        "ebook_items",
        sa.Column("cover_source_item_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "ebook_items",
        sa.Column("cover_image_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "ebook_items",
        sa.Column("cover_destination_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "ebook_items",
        sa.Column("cover_retrieved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "ebook_items",
        sa.Column("cover_policy_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "ebook_items",
        sa.Column(
            "cover_status",
            sa.String(length=32),
            nullable=False,
            server_default="HIDDEN_UNVERIFIED",
        ),
    )
    op.create_index(
        "ix_ebook_items_cover_source", "ebook_items", ["cover_source"]
    )
    op.create_index(
        "ix_ebook_items_cover_status", "ebook_items", ["cover_status"]
    )

    op.create_table(
        "store_cover_policy_agreements",
        sa.Column("store_name", sa.String(length=32), nullable=False),
        sa.Column("responsible_name", sa.String(length=255), nullable=False),
        sa.Column("agreed", sa.Boolean(), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "store_name IN ('rakuten_kobo', 'amazon', 'dmm')",
            name="valid_store_cover_policy_store",
        ),
        sa.CheckConstraint(
            "length(trim(responsible_name)) > 0",
            name="store_cover_policy_responsible_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(policy_version)) > 0",
            name="store_cover_policy_version_not_blank",
        ),
        sa.PrimaryKeyConstraint("store_name"),
    )

    op.create_table(
        "cover_automation_audit_queue",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ebook_item_id", sa.String(length=36), nullable=False),
        sa.Column("store_name", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("safe_detail", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "store_name IN ('rakuten_kobo', 'amazon', 'dmm')",
            name="valid_cover_audit_store",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'NOTIFIED', 'RESOLVED')",
            name="valid_cover_audit_status",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"], ["ebook_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cover_automation_audit_queue_ebook_item_id",
        "cover_automation_audit_queue",
        ["ebook_item_id"],
    )
    op.create_index(
        "ix_cover_automation_audit_queue_store_name",
        "cover_automation_audit_queue",
        ["store_name"],
    )
    op.create_index(
        "ix_cover_automation_audit_queue_reason_code",
        "cover_automation_audit_queue",
        ["reason_code"],
    )
    op.create_index(
        "ix_cover_audit_item_reason_status",
        "cover_automation_audit_queue",
        ["ebook_item_id", "reason_code", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cover_audit_item_reason_status",
        table_name="cover_automation_audit_queue",
    )
    op.drop_index(
        "ix_cover_automation_audit_queue_reason_code",
        table_name="cover_automation_audit_queue",
    )
    op.drop_index(
        "ix_cover_automation_audit_queue_store_name",
        table_name="cover_automation_audit_queue",
    )
    op.drop_index(
        "ix_cover_automation_audit_queue_ebook_item_id",
        table_name="cover_automation_audit_queue",
    )
    op.drop_table("cover_automation_audit_queue")
    op.drop_table("store_cover_policy_agreements")
    op.drop_index("ix_ebook_items_cover_status", table_name="ebook_items")
    op.drop_index("ix_ebook_items_cover_source", table_name="ebook_items")
    for name in (
        "cover_status",
        "cover_policy_version",
        "cover_retrieved_at",
        "cover_destination_url",
        "cover_image_url",
        "cover_source_item_id",
        "cover_source",
    ):
        op.drop_column("ebook_items", name)
