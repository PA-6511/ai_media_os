"""add setting material and artbook item types

Revision ID: 4b5f7a9c2d10
Revises: 1add00dcdfbd
"""

from __future__ import annotations

from alembic import op


revision = "4b5f7a9c2d10"
down_revision = "1add00dcdfbd"
branch_labels = None
depends_on = None


NEW_CHECK = (
    "item_type IN ("
    "'tankobon', "
    "'light_novel', "
    "'general_book', "
    "'single_chapter', "
    "'magazine_episode', "
    "'mook', "
    "'setting_material', "
    "'artbook', "
    "'unknown'"
    ")"
)

OLD_CHECK = (
    "item_type IN ("
    "'tankobon', "
    "'light_novel', "
    "'general_book', "
    "'single_chapter', "
    "'magazine_episode', "
    "'mook', "
    "'unknown'"
    ")"
)


def upgrade() -> None:
    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "valid_item_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "valid_item_type",
            NEW_CHECK,
        )


def downgrade() -> None:
    op.execute(
        """
        UPDATE ebook_items
        SET item_type = 'mook'
        WHERE item_type IN (
            'setting_material',
            'artbook'
        )
        """
    )

    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "valid_item_type",
            type_="check",
        )
        batch_op.create_check_constraint(
            "valid_item_type",
            OLD_CHECK,
        )
