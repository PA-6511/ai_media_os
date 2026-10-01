"""add external evidence aggregate index

Revision ID: e8f1a6c4d2b7
Revises: a1c4e7f9b2d5
Create Date: 2026-08-26
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8f1a6c4d2b7"
down_revision: Union[str, Sequence[str], None] = "a1c4e7f9b2d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "external_evidence_index",
        sa.Column(
            "ebook_item_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "evidence_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "evidence_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name="ck_external_evidence_index_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint(
            "ebook_item_id",
            "evidence_type",
        ),
    )

    op.create_index(
        "ix_external_evidence_index_ebook_item_id",
        "external_evidence_index",
        ["ebook_item_id"],
    )

    op.create_table(
        "external_evidence_index_state",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "draft_directory_mtime_ns",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "schedule_directory_mtime_ns",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "indexed_json_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "indexed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "id = 1",
            name="ck_external_evidence_index_state_singleton",
        ),
        sa.CheckConstraint(
            "status IN ('EMPTY', 'READY', 'DIRTY')",
            name="ck_external_evidence_index_state_status",
        ),
        sa.CheckConstraint(
            "indexed_json_count >= 0",
            name="ck_external_evidence_index_state_count_nonnegative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        INSERT INTO external_evidence_index_state (
            id,
            status,
            indexed_json_count
        )
        VALUES (
            1,
            'EMPTY',
            0
        )
        """
    )


def downgrade() -> None:
    op.drop_table(
        "external_evidence_index_state"
    )

    op.drop_index(
        "ix_external_evidence_index_ebook_item_id",
        table_name="external_evidence_index",
    )

    op.drop_table(
        "external_evidence_index"
    )
