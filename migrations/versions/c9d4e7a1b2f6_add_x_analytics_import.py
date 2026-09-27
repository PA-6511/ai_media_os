"""add X Analytics CSV import and metric snapshots

Revision ID: c9d4e7a1b2f6
Revises: f7b2c8d9e1a3
Create Date: 2026-09-07
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d4e7a1b2f6"
down_revision: Union[str, Sequence[str], None] = "f7b2c8d9e1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COUNT_COLUMNS = (
    "impressions",
    "views",
    "engagements",
    "link_clicks",
    "profile_clicks",
    "likes",
    "reposts",
    "replies",
    "follows",
)


def upgrade() -> None:
    op.create_table(
        "x_analytics_import_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_key", sa.String(length=64), nullable=False),
        sa.Column("csv_sha256", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("metric_scope", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("csv_timezone", sa.String(length=64), nullable=True),
        sa.Column("reach_metric_name", sa.String(length=32), nullable=True),
        sa.Column("headers_json", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "metric_scope IN ('lifetime', 'interval', 'unknown')",
            name="valid_x_analytics_import_scope",
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'SUCCEEDED')",
            name="valid_x_analytics_import_status",
        ),
        sa.CheckConstraint(
            "metric_scope != 'interval' OR "
            "(interval_start_at IS NOT NULL AND interval_end_at IS NOT NULL "
            "AND interval_end_at > interval_start_at)",
            name="valid_x_analytics_import_interval",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("import_key", name="x_analytics_import_key"),
    )
    for column in ("csv_sha256", "source", "account_identifier", "observed_at"):
        op.create_index(
            f"ix_x_analytics_import_runs_{column}",
            "x_analytics_import_runs",
            [column],
        )

    snapshot_columns: list[sa.Column] = [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("observation_key", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("account_identifier", sa.String(length=255), nullable=False),
        sa.Column("post_id", sa.String(length=128), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("post_type", sa.String(length=64), nullable=True),
        sa.Column("post_type_source", sa.String(length=64), nullable=True),
        sa.Column("metric_scope", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_end_at", sa.DateTime(timezone=True), nullable=True),
        *(sa.Column(name, sa.Integer(), nullable=True) for name in COUNT_COLUMNS),
        sa.Column("engagement_rate", sa.Numeric(18, 8), nullable=True),
        sa.Column("engagement_rate_format", sa.String(length=32), nullable=True),
        sa.Column("reach_metric_name", sa.String(length=32), nullable=True),
        sa.Column("reach_metric_source_header", sa.String(length=255), nullable=True),
        sa.Column("ebook_item_id", sa.String(length=36), nullable=True),
        sa.Column("store_name", sa.String(length=64), nullable=True),
        sa.Column("has_cover", sa.Boolean(), nullable=True),
        sa.Column("link_status", sa.String(length=16), nullable=False),
        sa.Column("link_source", sa.String(length=128), nullable=True),
        sa.Column("post_evidence_path", sa.Text(), nullable=True),
        sa.Column("first_import_run_id", sa.String(length=36), nullable=False),
        sa.Column("last_import_run_id", sa.String(length=36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    ]
    op.create_table(
        "x_analytics_metric_snapshots",
        *snapshot_columns,
        sa.CheckConstraint(
            "metric_scope IN ('lifetime', 'interval', 'unknown')",
            name="valid_x_analytics_snapshot_scope",
        ),
        sa.CheckConstraint(
            "metric_scope != 'interval' OR "
            "(interval_start_at IS NOT NULL AND interval_end_at IS NOT NULL "
            "AND interval_end_at > interval_start_at)",
            name="valid_x_analytics_snapshot_interval",
        ),
        sa.CheckConstraint(
            "link_status IN ('MATCHED', 'UNMATCHED', 'AMBIGUOUS')",
            name="valid_x_analytics_link_status",
        ),
        *(
            sa.CheckConstraint(
                f"{name} IS NULL OR {name} >= 0",
                name=f"nonnegative_x_analytics_{name}",
            )
            for name in COUNT_COLUMNS
        ),
        sa.CheckConstraint(
            "engagement_rate IS NULL OR engagement_rate >= 0",
            name="nonnegative_x_analytics_engagement_rate",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"], ["ebook_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["first_import_run_id"],
            ["x_analytics_import_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["last_import_run_id"],
            ["x_analytics_import_runs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "observation_key", name="x_analytics_observation_identity"
        ),
    )
    for column in (
        "source",
        "account_identifier",
        "post_id",
        "observed_at",
        "ebook_item_id",
    ):
        op.create_index(
            f"ix_x_analytics_metric_snapshots_{column}",
            "x_analytics_metric_snapshots",
            [column],
        )

    op.create_table(
        "x_analytics_import_rows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("import_run_id", sa.String(length=36), nullable=False),
        sa.Column("snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=False),
        sa.Column("unknown_payload_json", sa.Text(), nullable=False),
        sa.Column("source_headers_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["import_run_id"], ["x_analytics_import_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["x_analytics_metric_snapshots.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_run_id", "row_number", name="x_analytics_import_row_identity"
        ),
    )
    op.create_index(
        "ix_x_analytics_import_rows_import_run_id",
        "x_analytics_import_rows",
        ["import_run_id"],
    )
    op.create_index(
        "ix_x_analytics_import_rows_snapshot_id",
        "x_analytics_import_rows",
        ["snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_x_analytics_import_rows_snapshot_id",
        table_name="x_analytics_import_rows",
    )
    op.drop_index(
        "ix_x_analytics_import_rows_import_run_id",
        table_name="x_analytics_import_rows",
    )
    op.drop_table("x_analytics_import_rows")
    for column in (
        "ebook_item_id",
        "observed_at",
        "post_id",
        "account_identifier",
        "source",
    ):
        op.drop_index(
            f"ix_x_analytics_metric_snapshots_{column}",
            table_name="x_analytics_metric_snapshots",
        )
    op.drop_table("x_analytics_metric_snapshots")
    for column in ("observed_at", "account_identifier", "source", "csv_sha256"):
        op.drop_index(
            f"ix_x_analytics_import_runs_{column}",
            table_name="x_analytics_import_runs",
        )
    op.drop_table("x_analytics_import_runs")