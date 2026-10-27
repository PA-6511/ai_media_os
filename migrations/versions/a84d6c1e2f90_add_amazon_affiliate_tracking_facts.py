"""add amazon affiliate tracking facts

Revision ID: a84d6c1e2f90
Revises: f7c2a9d4e1b3
"""

from alembic import op
import sqlalchemy as sa


revision = "a84d6c1e2f90"
down_revision = "f7c2a9d4e1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "amazon_affiliate_tracking_performance_facts",

        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),

        sa.Column(
            "period_start",
            sa.Date(),
            nullable=False,
        ),

        sa.Column(
            "period_end",
            sa.Date(),
            nullable=False,
        ),

        sa.Column(
            "bucket_type",
            sa.String(length=16),
            nullable=False,
        ),

        sa.Column(
            "bucket_value",
            sa.String(length=128),
            nullable=False,
        ),

        sa.Column(
            "clicks",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "ordered_items",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "ordered_revenue",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),

        sa.Column(
            "shipped_items",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "shipped_revenue",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),

        sa.Column(
            "referral_fee",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=False,
        ),

        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),

        sa.Column(
            "attribution_basis",
            sa.String(length=40),
            nullable=False,
        ),

        sa.Column(
            "source_file_sha256",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "source_row_sha256",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "imported_at",
            sa.DateTime(
                timezone=True
            ),
            nullable=False,
        ),

        sa.CheckConstraint(
            "period_end >= period_start",
            name="ck_amazon_tracking_period",
        ),

        sa.CheckConstraint(
            "bucket_type IN "
            "('TRACKING_ID','OTHER')",
            name=(
                "ck_amazon_tracking_bucket_type"
            ),
        ),

        sa.CheckConstraint(
            "("
            "bucket_type = 'OTHER' "
            "AND bucket_value = 'Other'"
            ") OR ("
            "bucket_type = 'TRACKING_ID' "
            "AND bucket_value <> 'Other'"
            ")",
            name=(
                "ck_amazon_tracking_bucket_semantics"
            ),
        ),

        sa.CheckConstraint(
            "clicks >= 0",
            name="ck_amazon_tracking_clicks",
        ),

        sa.CheckConstraint(
            "ordered_items >= 0",
            name=(
                "ck_amazon_tracking_ordered_items"
            ),
        ),

        sa.CheckConstraint(
            "ordered_revenue >= 0",
            name=(
                "ck_amazon_tracking_ordered_revenue"
            ),
        ),

        sa.CheckConstraint(
            "shipped_items >= 0",
            name=(
                "ck_amazon_tracking_shipped_items"
            ),
        ),

        sa.CheckConstraint(
            "shipped_revenue >= 0",
            name=(
                "ck_amazon_tracking_shipped_revenue"
            ),
        ),

        sa.CheckConstraint(
            "referral_fee >= 0",
            name=(
                "ck_amazon_tracking_referral_fee"
            ),
        ),

        sa.PrimaryKeyConstraint(
            "id"
        ),

        sa.UniqueConstraint(
            "period_start",
            "period_end",
            "bucket_type",
            "bucket_value",
            name=(
                "uq_amazon_tracking_natural_identity"
            ),
        ),

        sa.UniqueConstraint(
            "source_row_sha256",
            name=(
                "uq_amazon_tracking_source_row"
            ),
        ),
    )

    op.create_index(
        "ix_amazon_tracking_period",
        "amazon_affiliate_tracking_performance_facts",
        [
            "period_start",
            "period_end",
        ],
        unique=False,
    )

    op.create_index(
        "ix_amazon_tracking_bucket_value",
        "amazon_affiliate_tracking_performance_facts",
        [
            "bucket_value",
        ],
        unique=False,
    )

    op.create_index(
        "ix_amazon_tracking_source_file",
        "amazon_affiliate_tracking_performance_facts",
        [
            "source_file_sha256",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_amazon_tracking_source_file",
        table_name=(
            "amazon_affiliate_tracking_performance_facts"
        ),
    )

    op.drop_index(
        "ix_amazon_tracking_bucket_value",
        table_name=(
            "amazon_affiliate_tracking_performance_facts"
        ),
    )

    op.drop_index(
        "ix_amazon_tracking_period",
        table_name=(
            "amazon_affiliate_tracking_performance_facts"
        ),
    )

    op.drop_table(
        "amazon_affiliate_tracking_performance_facts"
    )
