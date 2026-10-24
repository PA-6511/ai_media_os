"""add amazon affiliate performance facts

Revision ID: f7c2a9d4e1b3
Revises: e6a1b9c4d2f8
"""

from alembic import op
import sqlalchemy as sa


revision = "f7c2a9d4e1b3"
down_revision = "e6a1b9c4d2f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "amazon_affiliate_performance_facts",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "report_type",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "report_date",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "tracking_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "asin",
            sa.String(length=10),
            nullable=False,
        ),
        sa.Column(
            "product_title",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "clicks",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "ordered_items",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "ordered_revenue",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "shipped_items",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "shipped_revenue",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "referral_fee",
            sa.Numeric(
                precision=14,
                scale=2,
            ),
            nullable=True,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "attribution_basis",
            sa.String(length=32),
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
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "report_type IN "
                "('ORDER','EARNINGS')"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "valid_report_type"
            ),
        ),
        sa.CheckConstraint(
            "length(asin) = 10",
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "asin_length_10"
            ),
        ),
        sa.CheckConstraint(
            "length(currency) = 3",
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "currency_length_3"
            ),
        ),
        sa.CheckConstraint(
            "clicks IS NULL OR clicks >= 0",
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_clicks"
            ),
        ),
        sa.CheckConstraint(
            (
                "ordered_items IS NULL "
                "OR ordered_items >= 0"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_ordered_items"
            ),
        ),
        sa.CheckConstraint(
            (
                "ordered_revenue IS NULL "
                "OR ordered_revenue >= 0"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_ordered_revenue"
            ),
        ),
        sa.CheckConstraint(
            (
                "shipped_items IS NULL "
                "OR shipped_items >= 0"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_shipped_items"
            ),
        ),
        sa.CheckConstraint(
            (
                "shipped_revenue IS NULL "
                "OR shipped_revenue >= 0"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_shipped_revenue"
            ),
        ),
        sa.CheckConstraint(
            (
                "referral_fee IS NULL "
                "OR referral_fee >= 0"
            ),
            name=(
                "ck_amazon_affiliate_"
                "performance_facts_"
                "nonnegative_referral_fee"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=(
                "pk_amazon_affiliate_"
                "performance_facts"
            ),
        ),
        sa.UniqueConstraint(
            "source_row_sha256",
            name=(
                "amazon_affiliate_performance_"
                "source_row_identity"
            ),
        ),
    )

    op.create_index(
        "ix_amazon_affiliate_performance_facts_asin",
        "amazon_affiliate_performance_facts",
        ["asin"],
        unique=False,
    )

    op.create_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_report_date"
        ),
        "amazon_affiliate_performance_facts",
        ["report_date"],
        unique=False,
    )

    op.create_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_tracking_id"
        ),
        "amazon_affiliate_performance_facts",
        ["tracking_id"],
        unique=False,
    )

    op.create_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_source_file"
        ),
        "amazon_affiliate_performance_facts",
        ["source_file_sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_source_file"
        ),
        table_name=(
            "amazon_affiliate_performance_facts"
        ),
    )

    op.drop_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_tracking_id"
        ),
        table_name=(
            "amazon_affiliate_performance_facts"
        ),
    )

    op.drop_index(
        (
            "ix_amazon_affiliate_"
            "performance_facts_report_date"
        ),
        table_name=(
            "amazon_affiliate_performance_facts"
        ),
    )

    op.drop_index(
        "ix_amazon_affiliate_performance_facts_asin",
        table_name=(
            "amazon_affiliate_performance_facts"
        ),
    )

    op.drop_table(
        "amazon_affiliate_performance_facts"
    )
