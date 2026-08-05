"""Add supplement import candidates and discovery metadata.

Revision ID: c4e8b2f7a1d6
Revises: a7d3e9f1b5c2
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c4e8b2f7a1d6"
down_revision = "a7d3e9f1b5c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ebook_items") as batch_op:
        batch_op.add_column(sa.Column("source_discovery", sa.String(length=64)))
        batch_op.add_column(sa.Column("source_url", sa.Text()))
        batch_op.create_index(
            "ix_ebook_items_source_discovery", ["source_discovery"]
        )

    op.create_table(
        "supplement_import_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("target_release_date", sa.Date(), nullable=False),
        sa.Column("raw_text_hash", sa.String(length=64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PARSED', 'IMPORTING', 'IMPORTED', 'FAILED')",
            name="valid_supplement_import_run_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "target_release_date",
            "raw_text_hash",
            name="supplement_import_run_input_identity",
        ),
    )
    op.create_index(
        "ix_supplement_import_runs_target_release_date",
        "supplement_import_runs",
        ["target_release_date"],
    )
    op.create_index(
        "ix_supplement_import_runs_raw_text_hash",
        "supplement_import_runs",
        ["raw_text_hash"],
    )

    op.create_table(
        "supplement_import_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_key", sa.String(length=64), nullable=False),
        sa.Column("normalized_title", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("volume_label", sa.String(length=100)),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("publisher_name", sa.String(length=255)),
        sa.Column("author_name", sa.String(length=255)),
        sa.Column("imprint_name", sa.String(length=255)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parser_confidence", sa.String(length=32), nullable=False),
        sa.Column("parser_warnings", sa.Text(), nullable=False),
        sa.Column("match_status", sa.String(length=32), nullable=False),
        sa.Column("matched_ebook_item_id", sa.String(length=36)),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("import_status", sa.String(length=32), nullable=False),
        sa.Column("imported_ebook_item_id", sa.String(length=36)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "parser_confidence IN ('HIGH', 'REVIEW_REQUIRED', 'UNPARSED')",
            name="valid_supplement_parser_confidence",
        ),
        sa.CheckConstraint(
            "match_status IN ('NEW_CANDIDATE', 'EXACT_DUPLICATE', "
            "'POSSIBLE_DUPLICATE', 'INVALID')",
            name="valid_supplement_match_status",
        ),
        sa.CheckConstraint(
            "import_status IN ('PENDING', 'IMPORTED', 'SKIPPED')",
            name="valid_supplement_import_status",
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["supplement_import_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["matched_ebook_item_id"], ["ebook_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["imported_ebook_item_id"], ["ebook_items.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_run_id",
            "candidate_key",
            name="supplement_import_candidate_identity",
        ),
    )
    for column in (
        "import_run_id",
        "normalized_title",
        "release_date",
        "match_status",
        "matched_ebook_item_id",
        "imported_ebook_item_id",
    ):
        op.create_index(
            f"ix_supplement_import_candidates_{column}",
            "supplement_import_candidates",
            [column],
        )

    op.create_table(
        "supplement_parse_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("import_run_id", sa.String(length=36)),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("target_release_date", sa.Date(), nullable=False),
        sa.Column("raw_text_hash", sa.String(length=64), nullable=False),
        sa.Column("parsed_count", sa.Integer(), nullable=False),
        sa.Column("unparsed_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["supplement_import_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("operation", "import_run_id", "raw_text_hash", "created_at"):
        op.create_index(
            f"ix_supplement_parse_history_{column}",
            "supplement_parse_history",
            [column],
        )

    op.create_table(
        "supplement_import_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=False),
        sa.Column("selected_candidate_ids", sa.Text(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("imported_ebook_item_ids", sa.Text(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_skipped_count", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.String(length=128), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["supplement_import_runs.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("operation", "import_run_id", "created_at"):
        op.create_index(
            f"ix_supplement_import_history_{column}",
            "supplement_import_history",
            [column],
        )


def downgrade() -> None:
    op.drop_table("supplement_import_history")
    op.drop_table("supplement_parse_history")
    op.drop_table("supplement_import_candidates")
    op.drop_table("supplement_import_runs")
    with op.batch_alter_table("ebook_items") as batch_op:
        batch_op.drop_index("ix_ebook_items_source_discovery")
        batch_op.drop_column("source_url")
        batch_op.drop_column("source_discovery")
