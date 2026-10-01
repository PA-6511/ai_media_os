"""add mook item type

Revision ID: b7e2c4d9f1a6
Revises: a3f7c2d9e5b1
"""

from alembic import op


revision = "b7e2c4d9f1a6"
down_revision = "a3f7c2d9e5b1"
branch_labels = None
depends_on = None


_NEW_ITEM_TYPE_CHECK = (
    "item_type IN "
    "('tankobon', 'light_novel', 'general_book', "
    "'single_chapter', 'magazine_episode', 'mook', 'unknown')"
)

_OLD_ITEM_TYPE_CHECK = (
    "item_type IN "
    "('tankobon', 'light_novel', 'general_book', "
    "'single_chapter', 'magazine_episode', 'unknown')"
)


def upgrade() -> None:
    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_ebook_items_valid_item_type"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_ebook_items_valid_item_type"),
            _NEW_ITEM_TYPE_CHECK,
        )


def downgrade() -> None:
    # Preserve downgrade compatibility if mook rows have already been created.
    op.execute(
        "UPDATE ebook_items "
        "SET item_type = 'general_book' "
        "WHERE item_type = 'mook'"
    )

    with op.batch_alter_table(
        "ebook_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            op.f("ck_ebook_items_valid_item_type"),
            type_="check",
        )
        batch_op.create_check_constraint(
            op.f("ck_ebook_items_valid_item_type"),
            _OLD_ITEM_TYPE_CHECK,
        )
