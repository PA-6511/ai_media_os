"""add monthly comic release sync evidence tables

Revision ID: f7b2c8d9e1a3
Revises: c7a9e2f4b6d1
Create Date: 2026-08-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "f7b2c8d9e1a3"
down_revision = "c7a9e2f4b6d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comic_release_sync_runs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("target_month", sa.String(length=7), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.CheckConstraint("mode = 'EXECUTE'", name="comic_release_sync_run_mode"),
        sa.CheckConstraint("status IN ('RUNNING', 'PASS', 'ERROR')", name="comic_release_sync_run_status"),
    )
    op.create_table(
        "comic_release_metadata",
        sa.Column("ebook_item_id", sa.String(length=36), sa.ForeignKey("ebook_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("imprint_name", sa.String(length=255)),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("source_item_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_discovery", sa.String(length=64), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comic_release_metadata_source_identity", "comic_release_metadata", ["source_name", "source_item_id"], unique=True)
    op.create_table(
        "comic_release_sync_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=64), sa.ForeignKey("comic_release_sync_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ebook_item_id", sa.String(length=36), sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("change_type", sa.String(length=16), nullable=False),
        sa.Column("changed_fields", sa.Text(), nullable=False),
        sa.Column("before_json", sa.Text()),
        sa.Column("after_json", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("change_type IN ('NEW', 'UPDATED')", name="comic_release_sync_event_type"),
    )
    op.create_index("ix_comic_release_sync_events_ebook_item_id", "comic_release_sync_events", ["ebook_item_id"])
    op.create_index("ix_comic_release_sync_events_run_id", "comic_release_sync_events", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_comic_release_sync_events_run_id", table_name="comic_release_sync_events")
    op.drop_index("ix_comic_release_sync_events_ebook_item_id", table_name="comic_release_sync_events")
    op.drop_table("comic_release_sync_events")
    op.drop_index("ix_comic_release_metadata_source_identity", table_name="comic_release_metadata")
    op.drop_table("comic_release_metadata")
    op.drop_table("comic_release_sync_runs")
