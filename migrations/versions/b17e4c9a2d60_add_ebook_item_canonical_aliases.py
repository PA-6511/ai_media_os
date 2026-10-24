"""add ebook item canonical aliases

Revision ID: b17e4c9a2d60
Revises: a84d6c1e2f90
"""

from alembic import op
import sqlalchemy as sa


revision = "b17e4c9a2d60"
down_revision = "a84d6c1e2f90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ebook_item_canonical_aliases",
        sa.Column("alias_item_id", sa.Text(), nullable=False),
        sa.Column("canonical_item_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("merge_reason", sa.Text(), nullable=False),
        sa.Column("merge_plan_sha256", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "alias_item_id <> canonical_item_id",
            name="ck_ebook_item_canonical_alias_distinct_ids",
        ),
        sa.ForeignKeyConstraint(
            ["canonical_item_id"],
            ["ebook_items.id"],
            name="fk_ebook_item_canonical_alias_canonical_item",
            onupdate="NO ACTION",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("alias_item_id"),
    )
    op.create_index(
        "ix_ebook_item_canonical_aliases_canonical_item_id",
        "ebook_item_canonical_aliases",
        ["canonical_item_id"],
        unique=False,
    )


def downgrade() -> None:
    connection = op.get_bind()
    row_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM ebook_item_canonical_aliases")
    ).scalar_one()
    if row_count:
        raise RuntimeError(
            "refusing to downgrade while canonical aliases exist"
        )
    op.drop_index(
        "ix_ebook_item_canonical_aliases_canonical_item_id",
        table_name="ebook_item_canonical_aliases",
    )
    op.drop_table("ebook_item_canonical_aliases")
