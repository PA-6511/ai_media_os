"""add DMM discovery retry jobs

Revision ID: b6e1d4a8c3f2
Revises: a4d9c2e7f1b6
Create Date: 2026-08-13
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6e1d4a8c3f2"
down_revision: Union[str, Sequence[str], None] = "a4d9c2e7f1b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dmm_discovery_retry_jobs",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "ebook_item_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_evidence_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column(
            "retry_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "search_url",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "found_product_url",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "found_product_title",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "last_error",
            sa.Text(),
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
            "status IN ("
            "'QUEUED',"
            "'RUNNING',"
            "'COMPLETED_NOT_FOUND',"
            "'FOUND_PENDING_REVIEW',"
            "'FAILED',"
            "'CANCELLED'"
            ")",
            name="valid_dmm_discovery_retry_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="valid_dmm_discovery_retry_attempt_count",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"],
            ["ebook_items.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_evidence_id"],
            ["store_discovery_evidence.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_evidence_id",
            name="uq_dmm_discovery_retry_source_evidence",
        ),
    )

    op.create_index(
        "ix_dmm_discovery_retry_jobs_ebook_item_id",
        "dmm_discovery_retry_jobs",
        ["ebook_item_id"],
    )

    op.create_index(
        "ix_dmm_discovery_retry_jobs_source_evidence_id",
        "dmm_discovery_retry_jobs",
        ["source_evidence_id"],
        unique=True,
    )

    op.create_index(
        "ix_dmm_discovery_retry_jobs_status",
        "dmm_discovery_retry_jobs",
        ["status"],
    )

    op.create_index(
        "ix_dmm_discovery_retry_jobs_retry_at",
        "dmm_discovery_retry_jobs",
        ["retry_at"],
    )

    op.create_index(
        "ix_dmm_discovery_retry_jobs_last_attempt_at",
        "dmm_discovery_retry_jobs",
        ["last_attempt_at"],
    )

    op.create_index(
        "ix_dmm_discovery_retry_due",
        "dmm_discovery_retry_jobs",
        ["status", "retry_at"],
    )

    op.create_index(
        "ix_dmm_discovery_retry_item_status",
        "dmm_discovery_retry_jobs",
        ["ebook_item_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dmm_discovery_retry_item_status",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_due",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_jobs_last_attempt_at",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_jobs_retry_at",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_jobs_status",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_jobs_source_evidence_id",
        table_name="dmm_discovery_retry_jobs",
    )
    op.drop_index(
        "ix_dmm_discovery_retry_jobs_ebook_item_id",
        table_name="dmm_discovery_retry_jobs",
    )

    op.drop_table("dmm_discovery_retry_jobs")
