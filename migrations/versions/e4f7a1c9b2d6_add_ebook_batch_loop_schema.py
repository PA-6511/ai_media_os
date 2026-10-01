"""add ebook five-item batch loop schema

Revision ID: e4f7a1c9b2d6
Revises: d9a4c7e2f1b6
Create Date: 2026-08-08

This migration creates only the persistent batch-loop state.

It does not:
- create approval gates;
- publish WordPress posts;
- post to X;
- start workers;
- reserve ebook items automatically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f7a1c9b2d6"
down_revision: Union[str, Sequence[str], None] = "d9a4c7e2f1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BATCH_STATES = (
    "'QUEUED',"
    "'RESERVED',"
    "'PREFLIGHT',"
    "'EXECUTING',"
    "'WP_DRAFTED',"
    "'X_DRAFTED',"
    "'VERIFYING',"
    "'COMPLETED',"
    "'HOLD',"
    "'FAILED',"
    "'RECONCILIATION_REQUIRED'"
)


def upgrade() -> None:
    op.create_table(
        "ebook_batch_runs",
        sa.Column(
            "id",
            sa.String(length=36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column(
            "target_size",
            sa.Integer(),
            nullable=False,
            server_default="5",
        ),
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
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            f"status IN ({BATCH_STATES})",
            name="ck_ebook_batch_runs_status",
        ),
        sa.CheckConstraint(
            "target_size >= 1 AND target_size <= 5",
            name="ck_ebook_batch_runs_target_size",
        ),
    )

    op.create_index(
        "ix_ebook_batch_runs_status",
        "ebook_batch_runs",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_ebook_batch_runs_created_at",
        "ebook_batch_runs",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "ebook_batch_items",
        sa.Column(
            "id",
            sa.String(length=36),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.String(length=36),
            sa.ForeignKey(
                "ebook_batch_runs.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "ebook_item_id",
            sa.String(length=36),
            sa.ForeignKey(
                "ebook_items.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "slot_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="RESERVED",
        ),
        sa.Column(
            "last_error_code",
            sa.String(length=128),
            nullable=True,
        ),
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
            f"status IN ({BATCH_STATES})",
            name="ck_ebook_batch_items_status",
        ),
        sa.CheckConstraint(
            "slot_index >= 1 AND slot_index <= 5",
            name="ck_ebook_batch_items_slot",
        ),
        sa.UniqueConstraint(
            "batch_id",
            "ebook_item_id",
            name="uq_ebook_batch_items_batch_item",
        ),
        sa.UniqueConstraint(
            "batch_id",
            "slot_index",
            name="uq_ebook_batch_items_batch_slot",
        ),
    )

    op.create_index(
        "ix_ebook_batch_items_batch_id",
        "ebook_batch_items",
        ["batch_id"],
        unique=False,
    )

    op.create_index(
        "ix_ebook_batch_items_ebook_item_id",
        "ebook_batch_items",
        ["ebook_item_id"],
        unique=False,
    )

    op.create_index(
        "ix_ebook_batch_items_status",
        "ebook_batch_items",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ebook_batch_items_status",
        table_name="ebook_batch_items",
    )

    op.drop_index(
        "ix_ebook_batch_items_ebook_item_id",
        table_name="ebook_batch_items",
    )

    op.drop_index(
        "ix_ebook_batch_items_batch_id",
        table_name="ebook_batch_items",
    )

    op.drop_table(
        "ebook_batch_items"
    )

    op.drop_index(
        "ix_ebook_batch_runs_created_at",
        table_name="ebook_batch_runs",
    )

    op.drop_index(
        "ix_ebook_batch_runs_status",
        table_name="ebook_batch_runs",
    )

    op.drop_table(
        "ebook_batch_runs"
    )
