"""Add supplement registration cancellation history.

Revision ID: b6f1d8e3c2a7
Revises: c4e8b2f7a1d6
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b6f1d8e3c2a7"
down_revision = "c4e8b2f7a1d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "supplement_registration_cancellation_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("ebook_item_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("operator", sa.String(length=128), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=False),
        sa.Column("previous_workflow_status", sa.String(length=32), nullable=False),
        sa.Column("previous_review_status", sa.String(length=32), nullable=False),
        sa.Column("previous_wordpress_status", sa.String(length=32), nullable=False),
        sa.Column("dependency_checks_json", sa.Text(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["supplement_import_candidates.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["supplement_import_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "operation",
        "import_run_id",
        "candidate_id",
        "ebook_item_id",
        "cancelled_at",
    ):
        op.create_index(
            f"ix_supplement_registration_cancellation_history_{column}",
            "supplement_registration_cancellation_history",
            [column],
        )


def downgrade() -> None:
    op.drop_table("supplement_registration_cancellation_history")