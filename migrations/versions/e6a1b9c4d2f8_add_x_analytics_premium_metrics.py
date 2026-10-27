"""add X Analytics Premium metric columns

Revision ID: e6a1b9c4d2f8
Revises: c8f4a1d2b670
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e6a1b9c4d2f8"
down_revision: Union[str, Sequence[str], None] = "c8f4a1d2b670"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "x_analytics_metric_snapshots",
        sa.Column("detail_clicks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "x_analytics_metric_snapshots",
        sa.Column("bookmarks", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(
        "x_analytics_metric_snapshots",
        "bookmarks",
    )
    op.drop_column(
        "x_analytics_metric_snapshots",
        "detail_clicks",
    )
