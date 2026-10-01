"""add Kobo global catalog identity unique index

Revision ID: a1c4e7f9b2d5
Revises: f2a6c1d8e4b7
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1c4e7f9b2d5"
down_revision = "f2a6c1d8e4b7"
branch_labels = None
depends_on = None


INDEX_NAME = (
    "uq_store_offers_"
    "rakuten_kobo_catalog_id_13"
)


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "store_offers",
        [
            "store_item_id",
        ],
        unique=True,
        sqlite_where=sa.text(
            "store_name = 'rakuten_kobo' "
            "AND LENGTH(store_item_id) = 13 "
            "AND store_item_id "
            "NOT GLOB '*[^0-9]*'"
        ),
        postgresql_where=sa.text(
            "store_name = 'rakuten_kobo' "
            "AND store_item_id "
            "~ '^[0-9]{13}$'"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="store_offers",
    )
