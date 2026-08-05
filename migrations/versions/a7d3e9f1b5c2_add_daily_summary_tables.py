"""Add daily summary selections, audit history, and run state.

Revision ID: a7d3e9f1b5c2
Revises: f6c8d2a4b1e9
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a7d3e9f1b5c2"
down_revision = "f6c8d2a4b1e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_summary_selections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ebook_item_id", sa.String(length=36), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("inclusion_state", sa.String(length=32), nullable=False),
        sa.Column("selection_source", sa.String(length=16), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selected_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "inclusion_state IN ('AUTO_INCLUDED', 'HUMAN_INCLUDED', 'HUMAN_EXCLUDED')",
            name="valid_daily_summary_inclusion_state",
        ),
        sa.CheckConstraint(
            "selection_source IN ('AUTO', 'HUMAN')",
            name="valid_daily_summary_selection_source",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"], ["ebook_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ebook_item_id",
            "summary_date",
            name="daily_summary_selection_identity",
        ),
    )
    op.create_index(
        "ix_daily_summary_selections_ebook_item_id",
        "daily_summary_selections",
        ["ebook_item_id"],
    )
    op.create_index(
        "ix_daily_summary_selections_summary_date",
        "daily_summary_selections",
        ["summary_date"],
    )

    op.create_table(
        "daily_summary_selection_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("ebook_item_id", sa.String(length=36), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("before_state", sa.String(length=32), nullable=True),
        sa.Column("after_state", sa.String(length=32), nullable=True),
        sa.Column("changed_by", sa.String(length=128), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"], ["ebook_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("operation", "ebook_item_id", "summary_date", "changed_at"):
        op.create_index(
            f"ix_daily_summary_selection_history_{column}",
            "daily_summary_selection_history",
            [column],
        )

    op.create_table(
        "daily_summary_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("summary_key", sa.String(length=128), nullable=False),
        sa.Column("wordpress_post_id", sa.String(length=64), nullable=True),
        sa.Column("wordpress_status", sa.String(length=16), nullable=True),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("generated_count", sa.Integer(), nullable=False),
        sa.Column("selected_item_ids_json", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("remote_response_id", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "wordpress_status IS NULL OR wordpress_status IN ('draft', 'future', 'publish', 'trash')",
            name="valid_daily_summary_wordpress_status",
        ),
        sa.CheckConstraint(
            "execution_status IN ('PREVIEWED', 'CREATING', 'UPDATING', 'SUCCEEDED', 'FAILED')",
            name="valid_daily_summary_execution_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("summary_date", name="daily_summary_run_date_identity"),
        sa.UniqueConstraint("summary_key", name="daily_summary_run_key_identity"),
    )
    for column in ("summary_date", "summary_key", "wordpress_post_id", "input_hash"):
        op.create_index(
            f"ix_daily_summary_runs_{column}",
            "daily_summary_runs",
            [column],
        )

    op.create_table(
        "daily_summary_run_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("summary_key", sa.String(length=128), nullable=False),
        sa.Column("selected_item_ids_json", sa.Text(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("wordpress_post_id", sa.String(length=64), nullable=True),
        sa.Column("wordpress_status", sa.String(length=16), nullable=True),
        sa.Column("remote_response_id", sa.String(length=64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("operation", "summary_date", "summary_key", "input_hash", "created_at"):
        op.create_index(
            f"ix_daily_summary_run_history_{column}",
            "daily_summary_run_history",
            [column],
        )


def downgrade() -> None:
    op.drop_table("daily_summary_run_history")
    op.drop_table("daily_summary_runs")
    op.drop_table("daily_summary_selection_history")
    op.drop_table("daily_summary_selections")