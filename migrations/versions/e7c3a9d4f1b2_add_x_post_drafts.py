"""add x post drafts

Revision ID: e7c3a9d4f1b2
Revises: a3f7c2d9e5b1
"""

from alembic import op
import sqlalchemy as sa


revision = "e7c3a9d4f1b2"
down_revision = "a3f7c2d9e5b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "x_post_drafts",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "ebook_item_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "feedback_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "generated_text",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "paid_partnership",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="DRAFT",
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
            "source_type IN ('new_release', 'sale')",
            name="ck_x_post_drafts_source_type",
        ),
        sa.CheckConstraint(
            "status IN "
            "('DRAFT', 'READY_TO_POST', 'POSTED', 'EXPIRED', 'ERROR')",
            name="ck_x_post_drafts_status",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"],
            ["ebook_items.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            name="uq_x_post_drafts_source",
        ),
    )

    op.create_index(
        "ix_x_post_drafts_source_type",
        "x_post_drafts",
        ["source_type"],
        unique=False,
    )

    op.create_index(
        "ix_x_post_drafts_ebook_item_id",
        "x_post_drafts",
        ["ebook_item_id"],
        unique=False,
    )

    op.create_index(
        "ix_x_post_drafts_scheduled_at",
        "x_post_drafts",
        ["scheduled_at"],
        unique=False,
    )

    op.create_index(
        "ix_x_post_drafts_status",
        "x_post_drafts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_x_post_drafts_status",
        table_name="x_post_drafts",
    )
    op.drop_index(
        "ix_x_post_drafts_scheduled_at",
        table_name="x_post_drafts",
    )
    op.drop_index(
        "ix_x_post_drafts_ebook_item_id",
        table_name="x_post_drafts",
    )
    op.drop_index(
        "ix_x_post_drafts_source_type",
        table_name="x_post_drafts",
    )
    op.drop_table("x_post_drafts")
