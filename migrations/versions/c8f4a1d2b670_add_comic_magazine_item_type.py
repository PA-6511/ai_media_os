"""Add comic magazine item type without changing existing classifications."""
from alembic import op
revision = "c8f4a1d2b670"
down_revision = "9d4e2a7c6b31"
branch_labels = None
depends_on = None
OLD_CHECK = "item_type IN ('tankobon', 'light_novel', 'general_book', 'single_chapter', 'magazine_episode', 'mook', 'setting_material', 'artbook', 'unknown')"
NEW_CHECK = OLD_CHECK.replace("'mook'", "'comic_magazine', 'mook'")
def upgrade():
    with op.batch_alter_table("ebook_items", recreate="always") as batch:
        batch.drop_constraint("valid_item_type", type_="check")
        batch.create_check_constraint("valid_item_type", NEW_CHECK)
def downgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql("SELECT 1 FROM ebook_items WHERE item_type = 'comic_magazine' LIMIT 1").first():
        raise RuntimeError("Reclassify comic magazine items before downgrading")
    with op.batch_alter_table("ebook_items", recreate="always") as batch:
        batch.drop_constraint("valid_item_type", type_="check")
        batch.create_check_constraint("valid_item_type", OLD_CHECK)
