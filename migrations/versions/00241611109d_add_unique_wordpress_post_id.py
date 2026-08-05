"""Add fail-closed uniqueness for WordPress post IDs.

Revision ID: 00241611109d
Revises: 29962ac6d9a5
"""

from __future__ import annotations

from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "00241611109d"
down_revision = "29962ac6d9a5"
branch_labels = None
depends_on = None


INDEX_NAME = "uq_ebook_items_wordpress_post_id_not_null"

MIGRATION_PREFLIGHT_ERROR = (
    "WORDPRESS_POST_ID_MIGRATION_PREFLIGHT_FAILED"
)


def _valid_post_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value.isascii()
        and value.isdigit()
        and not value.startswith("0")
        and len(value) <= 20
    )


def preflight(connection: Any) -> None:
    rows = connection.execute(
        sa.text(
            """
            SELECT id, wordpress_post_id
            FROM ebook_items
            WHERE wordpress_post_id IS NOT NULL
            ORDER BY id
            """
        )
    ).all()

    seen: dict[str, str] = {}

    for item_id, post_id in rows:
        if not _valid_post_id(post_id):
            raise RuntimeError(
                f"{MIGRATION_PREFLIGHT_ERROR}:"
                f"INVALID_VALUE:{item_id}"
            )

        previous_item_id = seen.get(post_id)

        if previous_item_id is not None:
            raise RuntimeError(
                f"{MIGRATION_PREFLIGHT_ERROR}:"
                f"DUPLICATE:{post_id}:"
                f"{previous_item_id}:{item_id}"
            )

        seen[post_id] = item_id


def apply_with_connection(connection: Any) -> None:
    """Apply only to an explicitly supplied isolated connection."""
    preflight(connection)

    connection.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX {INDEX_NAME}
            ON ebook_items (wordpress_post_id)
            WHERE wordpress_post_id IS NOT NULL
            """
        )
    )


def remove_with_connection(connection: Any) -> None:
    """Remove only from an explicitly supplied isolated connection."""
    connection.execute(
        sa.text(
            f"DROP INDEX IF EXISTS {INDEX_NAME}"
        )
    )


def upgrade() -> None:
    connection = op.get_bind()
    preflight(connection)

    op.create_index(
        INDEX_NAME,
        "ebook_items",
        ["wordpress_post_id"],
        unique=True,
        sqlite_where=sa.text(
            "wordpress_post_id IS NOT NULL"
        ),
        postgresql_where=sa.text(
            "wordpress_post_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="ebook_items",
    )
