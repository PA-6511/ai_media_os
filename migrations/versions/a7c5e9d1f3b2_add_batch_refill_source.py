"""add batch refill source

Revision ID: a7c5e9d1f3b2
Revises: f6b3d8a2c4e1
Create Date: 2026-08-08

Adds a durable source-batch link so one completed
batch can create at most one next reserved batch.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c5e9d1f3b2"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "f6b3d8a2c4e1"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.add_column(
        "ebook_batch_runs",
        sa.Column(
            "source_batch_id",
            sa.String(length=36),
            nullable=True,
        ),
    )

    op.create_index(
        "ux_ebook_batch_runs_source_batch_id",
        "ebook_batch_runs",
        ["source_batch_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_ebook_batch_runs_source_batch_id",
        table_name="ebook_batch_runs",
    )

    with op.batch_alter_table(
        "ebook_batch_runs"
    ) as batch_op:
        batch_op.drop_column(
            "source_batch_id"
        )
