"""Add ebook single/split classification and future-series rules.

Revision ID: f6c8d2a4b1e9
Revises: e4b7c9d2a6f1
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f6c8d2a4b1e9"
down_revision = "e4b7c9d2a6f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ebook_items") as batch_op:
        batch_op.add_column(
            sa.Column("is_single_episode", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("is_split_edition", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("classification_source", sa.String(length=32), nullable=True)
        )
        batch_op.create_check_constraint(
            "valid_classification_source",
            "classification_source IS NULL OR classification_source IN "
            "('manual', 'series_rule')",
        )

    op.create_table(
        "ebook_series_classification_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("series_key", sa.String(length=64), nullable=False),
        sa.Column("normalized_base_title", sa.String(length=500), nullable=False),
        sa.Column("normalized_author_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_publisher_name", sa.String(length=255), nullable=False),
        sa.Column("is_single_episode", sa.Boolean(), nullable=False),
        sa.Column("is_split_edition", sa.Boolean(), nullable=False),
        sa.Column(
            "source_ebook_item_id", sa.String(length=36), nullable=False
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_ebook_item_id"],
            ["ebook_items.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_ebook_series_classification_rules_series_key",
        "ebook_series_classification_rules",
        ["series_key"],
        unique=True,
    )
    op.create_index(
        "ix_ebook_series_classification_rules_active",
        "ebook_series_classification_rules",
        ["active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ebook_series_classification_rules_active",
        table_name="ebook_series_classification_rules",
    )
    op.drop_index(
        "ux_ebook_series_classification_rules_series_key",
        table_name="ebook_series_classification_rules",
    )
    op.drop_table("ebook_series_classification_rules")

    with op.batch_alter_table("ebook_items") as batch_op:
        batch_op.drop_constraint(
            "valid_classification_source", type_="check"
        )
        batch_op.drop_column("classification_source")
        batch_op.drop_column("is_split_edition")
        batch_op.drop_column("is_single_episode")
