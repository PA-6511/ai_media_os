"""add sale crawl checkpoints

Revision ID: f2a6c1d8e4b7
Revises: c7a9e2f4b6d1
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a6c1d8e4b7"
down_revision = "c7a9e2f4b6d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sale_crawl_checkpoints",
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
            "store_name",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "check_result",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "review_state",
            sa.String(length=32),
            nullable=True,
        ),
        sa.Column(
            "sale_end_at_snapshot",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "store_name IN "
            "('amazon', 'rakuten_kobo', 'dmm')",
            name="valid_sale_crawl_checkpoint_store",
        ),
        sa.CheckConstraint(
            "check_result IN ('SUCCESS', 'FAILED')",
            name="valid_sale_crawl_checkpoint_result",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_sale_crawl_checkpoints_ebook_item_id",
        "sale_crawl_checkpoints",
        ["ebook_item_id"],
    )

    op.create_index(
        "ix_sale_crawl_checkpoints_store_name",
        "sale_crawl_checkpoints",
        ["store_name"],
    )

    op.create_index(
        "ix_sale_crawl_checkpoints_checked_at",
        "sale_crawl_checkpoints",
        ["checked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sale_crawl_checkpoints_checked_at",
        table_name="sale_crawl_checkpoints",
    )

    op.drop_index(
        "ix_sale_crawl_checkpoints_store_name",
        table_name="sale_crawl_checkpoints",
    )

    op.drop_index(
        "ix_sale_crawl_checkpoints_ebook_item_id",
        table_name="sale_crawl_checkpoints",
    )

    op.drop_table(
        "sale_crawl_checkpoints"
    )
