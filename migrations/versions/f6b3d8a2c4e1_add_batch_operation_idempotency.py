"""add batch operation idempotency

Revision ID: f6b3d8a2c4e1
Revises: e4f7a1c9b2d6
Create Date: 2026-08-08

Adds only the agreed WordPress-draft duplicate prevention
boundary to the five-item batch queue.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6b3d8a2c4e1"
down_revision: Union[str, Sequence[str], None] = "e4f7a1c9b2d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ebook_batch_items",
        sa.Column(
            "operation",
            sa.String(length=32),
            nullable=False,
            server_default="WORDPRESS_DRAFT",
        ),
    )

    op.create_index(
        "ux_ebook_batch_items_operation_item",
        "ebook_batch_items",
        [
            "operation",
            "ebook_item_id",
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_ebook_batch_items_operation_item",
        table_name="ebook_batch_items",
    )

    with op.batch_alter_table(
        "ebook_batch_items"
    ) as batch_op:
        batch_op.drop_column(
            "operation"
        )
