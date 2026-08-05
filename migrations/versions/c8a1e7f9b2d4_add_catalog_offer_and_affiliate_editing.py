"""Add catalog metadata, offer verification, settings, and audit history.

Revision ID: c8a1e7f9b2d4
Revises: 00241611109d

The production SQLite may contain the legacy ``affiliate_account_settings``
table created before Alembic managed it.  The upgrade extends that table in
place and never drops existing rows.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c8a1e7f9b2d4"
down_revision = "00241611109d"
branch_labels = None
depends_on = None


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())

    ebook_columns = _columns(inspector, "ebook_items")
    if "series_name" not in ebook_columns:
        with op.batch_alter_table("ebook_items") as batch_op:
            batch_op.add_column(sa.Column("series_name", sa.String(length=255), nullable=True))
            batch_op.create_index("ix_ebook_items_series_name", ["series_name"], unique=False)

    store_columns = _columns(inspector, "store_offers")
    store_additions = (
        ("price_amount", sa.Column("price_amount", sa.Numeric(precision=12, scale=2), nullable=True)),
        ("currency", sa.Column("currency", sa.String(length=12), nullable=True)),
        ("availability_status", sa.Column("availability_status", sa.String(length=32), nullable=True)),
        ("verified_at", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True)),
        ("verification_method", sa.Column("verification_method", sa.String(length=64), nullable=True)),
        ("source_row_sha256", sa.Column("source_row_sha256", sa.String(length=64), nullable=True)),
    )
    missing_store_columns = [column for name, column in store_additions if name not in store_columns]
    if missing_store_columns:
        with op.batch_alter_table("store_offers") as batch_op:
            for column in missing_store_columns:
                batch_op.add_column(column)
    inspector = sa.inspect(connection)
    if "ix_store_offers_source_row_sha256" not in _indexes(inspector, "store_offers"):
        op.create_index(
            "ix_store_offers_source_row_sha256",
            "store_offers",
            ["source_row_sha256"],
            unique=False,
        )

    op.execute("UPDATE store_offers SET price_amount = price_yen WHERE price_amount IS NULL AND price_yen IS NOT NULL")
    op.execute("UPDATE store_offers SET currency = 'JPY' WHERE price_yen IS NOT NULL AND currency IS NULL")

    if "catalog_edit_history" not in tables:
        op.create_table(
            "catalog_edit_history",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("ebook_item_id", sa.String(length=36), nullable=False),
            sa.Column("field_name", sa.String(length=128), nullable=False),
            sa.Column("before_value", sa.Text(), nullable=True),
            sa.Column("after_value", sa.Text(), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=False),
            sa.Column("changed_by", sa.String(length=128), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["ebook_item_id"], ["ebook_items.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        for name, columns in (
            ("ix_catalog_edit_history_ebook_item_id", ["ebook_item_id"]),
            ("ix_catalog_edit_history_field_name", ["field_name"]),
            ("ix_catalog_edit_history_changed_by", ["changed_by"]),
            ("ix_catalog_edit_history_changed_at", ["changed_at"]),
        ):
            op.create_index(name, "catalog_edit_history", columns)

    if "affiliate_account_settings" not in tables:
        op.create_table(
            "affiliate_account_settings",
            sa.Column("service_name", sa.String(length=64), nullable=False),
            sa.Column("affiliate_id", sa.Text(), nullable=True),
            sa.Column("url_template", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_by", sa.String(length=128), server_default="system", nullable=False),
            sa.PrimaryKeyConstraint("service_name"),
        )
    else:
        setting_columns = _columns(sa.inspect(connection), "affiliate_account_settings")
        with op.batch_alter_table("affiliate_account_settings") as batch_op:
            if "url_template" not in setting_columns:
                batch_op.add_column(sa.Column("url_template", sa.Text(), nullable=True))
            if "updated_by" not in setting_columns:
                batch_op.add_column(
                    sa.Column(
                        "updated_by",
                        sa.String(length=128),
                        nullable=False,
                        server_default="system",
                    )
                )

    if "affiliate_setting_history" not in tables:
        op.create_table(
            "affiliate_setting_history",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("service_name", sa.String(length=64), nullable=False),
            sa.Column("field_name", sa.String(length=64), nullable=False),
            sa.Column("before_value", sa.Text(), nullable=True),
            sa.Column("after_value", sa.Text(), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("changed_by", sa.String(length=128), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_affiliate_setting_history_service_name", "affiliate_setting_history", ["service_name"])
        op.create_index("ix_affiliate_setting_history_changed_at", "affiliate_setting_history", ["changed_at"])


def downgrade() -> None:
    # Downgrade intentionally removes only objects introduced by this
    # revision.  It is destructive and is never used by the local Web app.
    op.drop_index("ix_affiliate_setting_history_changed_at", table_name="affiliate_setting_history")
    op.drop_index("ix_affiliate_setting_history_service_name", table_name="affiliate_setting_history")
    op.drop_table("affiliate_setting_history")
    op.drop_table("affiliate_account_settings")
    op.drop_index("ix_catalog_edit_history_changed_at", table_name="catalog_edit_history")
    op.drop_index("ix_catalog_edit_history_changed_by", table_name="catalog_edit_history")
    op.drop_index("ix_catalog_edit_history_field_name", table_name="catalog_edit_history")
    op.drop_index("ix_catalog_edit_history_ebook_item_id", table_name="catalog_edit_history")
    op.drop_table("catalog_edit_history")
    with op.batch_alter_table("store_offers") as batch_op:
        batch_op.drop_index("ix_store_offers_source_row_sha256")
        batch_op.drop_column("source_row_sha256")
        batch_op.drop_column("verification_method")
        batch_op.drop_column("verified_at")
        batch_op.drop_column("availability_status")
        batch_op.drop_column("currency")
        batch_op.drop_column("price_amount")
    with op.batch_alter_table("ebook_items") as batch_op:
        batch_op.drop_index("ix_ebook_items_series_name")
        batch_op.drop_column("series_name")
