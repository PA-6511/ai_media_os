"""add edition type

Revision ID: 9d4e2a7c6b31
Revises: 4b5f7a9c2d10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "9d4e2a7c6b31"
down_revision = "4b5f7a9c2d10"
branch_labels = None
depends_on = None


EDITION_CHECK = (
    "edition_type IN ("
    "'normal', "
    "'special_edition', "
    "'special_release', "
    "'limited_edition'"
    ")"
)


def upgrade() -> None:
    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "edition_type",
                sa.String(length=32),
                nullable=False,
                server_default="normal",
            )
        )
        batch_op.create_check_constraint(
            "valid_edition_type",
            EDITION_CHECK,
        )
        batch_op.create_index(
            "ix_ebook_items_edition_type",
            ["edition_type"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_index(
            "ix_ebook_items_edition_type"
        )
        batch_op.drop_constraint(
            "valid_edition_type",
            type_="check",
        )
        batch_op.drop_column(
            "edition_type"
        )
