"""add amazon x tracking id pool

Revision ID: d2e7c4a91b30
Revises: b17e4c9a2d60
"""

from alembic import op
import sqlalchemy as sa


revision = "d2e7c4a91b30"
down_revision = "b17e4c9a2d60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "amazon_x_tracking_id_pool",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "tracking_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "experiment_id",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "variant_id",
            sa.String(length=64),
            nullable=True,
        ),
        sa.Column(
            "wordpress_post_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "registered_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "length(trim(tracking_id)) > 0",
            name=(
                "ck_amazon_x_tracking_pool_"
                "tracking_id_not_blank"
            ),
        ),
        sa.CheckConstraint(
            "status IN "
            "('AVAILABLE','ASSIGNED','DISABLED')",
            name=(
                "ck_amazon_x_tracking_pool_status"
            ),
        ),
        sa.CheckConstraint(
            "("
            "status IN ('AVAILABLE','DISABLED') "
            "AND experiment_id IS NULL "
            "AND variant_id IS NULL "
            "AND wordpress_post_id IS NULL "
            "AND assigned_at IS NULL"
            ") OR ("
            "status = 'ASSIGNED' "
            "AND experiment_id IS NOT NULL "
            "AND length(experiment_id) = 64 "
            "AND variant_id IS NOT NULL "
            "AND length(variant_id) = 64 "
            "AND wordpress_post_id IS NOT NULL "
            "AND wordpress_post_id > 0 "
            "AND assigned_at IS NOT NULL"
            ")",
            name=(
                "ck_amazon_x_tracking_pool_"
                "state_semantics"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
        sa.UniqueConstraint(
            "tracking_id",
            name=(
                "uq_amazon_x_tracking_pool_"
                "tracking_id"
            ),
        ),
        sa.UniqueConstraint(
            "variant_id",
            name=(
                "uq_amazon_x_tracking_pool_"
                "variant_id"
            ),
        ),
    )

    op.create_index(
        "ix_amazon_x_tracking_pool_status",
        "amazon_x_tracking_id_pool",
        ["status"],
        unique=False,
    )

    op.create_index(
        "ix_amazon_x_tracking_pool_experiment",
        "amazon_x_tracking_id_pool",
        ["experiment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_amazon_x_tracking_pool_experiment",
        table_name="amazon_x_tracking_id_pool",
    )

    op.drop_index(
        "ix_amazon_x_tracking_pool_status",
        table_name="amazon_x_tracking_id_pool",
    )

    op.drop_table(
        "amazon_x_tracking_id_pool"
    )
