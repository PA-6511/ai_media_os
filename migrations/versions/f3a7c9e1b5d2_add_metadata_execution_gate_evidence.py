"""add immutable metadata execution gate evidence

Revision ID: f3a7c9e1b5d2
Revises: e2f6b8c4d1a7
Create Date: 2026-08-11

Schema only.  This migration does not bind rights evidence, evaluate a live
candidate, create an approval or reservation, or call an external transport.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a7c9e1b5d2"
down_revision: Union[str, Sequence[str], None] = "e2f6b8c4d1a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_immutable_triggers(table: str, label: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"""
                CREATE TRIGGER {table}_no_{operation.lower()}
                BEFORE {operation} ON {table}
                BEGIN
                    SELECT RAISE(ABORT, '{label} are immutable');
                END
                """
            )
    elif dialect == "postgresql":
        function_name = f"reject_{table}_mutation"
        op.execute(
            f"""
            CREATE FUNCTION {function_name}()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{label} are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_no_mutation
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {function_name}()
            """
        )


def _drop_immutable_triggers(table: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(f"DROP TRIGGER {table}_no_delete")
        op.execute(f"DROP TRIGGER {table}_no_update")
    elif dialect == "postgresql":
        op.execute(f"DROP TRIGGER {table}_no_mutation ON {table}")
        op.execute(f"DROP FUNCTION reject_{table}_mutation()")


def upgrade() -> None:
    op.create_table(
        "image_rights_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("rights_status", sa.String(length=32), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("verified_by", sa.String(length=128), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "rights_status IN "
            "('VERIFIED_ALLOWED', 'VERIFIED_NOT_ALLOWED', 'UNRESOLVED')",
            name="valid_image_rights_status",
        ),
        sa.CheckConstraint(
            "length(trim(source_type)) > 0",
            name="image_rights_source_type_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(source_reference)) > 0",
            name="image_rights_source_reference_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_type)) > 0",
            name="image_rights_evidence_type_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="image_rights_evidence_reference_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(verified_by)) > 0",
            name="image_rights_verified_by_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_image_rights_evidence_candidate_id",
        "image_rights_evidence",
        ["candidate_id"],
    )
    op.create_index(
        "ix_image_rights_evidence_verified_at",
        "image_rights_evidence",
        ["verified_at"],
    )
    op.create_index(
        "ix_image_rights_candidate_verified",
        "image_rights_evidence",
        ["candidate_id", "verified_at"],
    )

    op.create_table(
        "metadata_gate_evaluation_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("execution_context", sa.String(length=64), nullable=False),
        sa.Column("overall_ready", sa.Boolean(), nullable=False),
        sa.Column("blocking_reasons_json", sa.Text(), nullable=False),
        sa.Column("requirement_profile_json", sa.Text(), nullable=False),
        sa.Column("per_field_result_json", sa.Text(), nullable=False),
        sa.Column("metadata_snapshot_digest", sa.String(length=64), nullable=False),
        sa.Column("evidence_references_json", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gate_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "length(metadata_snapshot_digest) = 64",
            name="valid_metadata_gate_snapshot_digest",
        ),
        sa.CheckConstraint(
            "length(trim(execution_context)) > 0",
            name="metadata_gate_execution_context_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(gate_version)) > 0",
            name="metadata_gate_version_not_blank",
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_metadata_gate_evaluation_events_candidate_id",
        "metadata_gate_evaluation_events",
        ["candidate_id"],
    )
    op.create_index(
        "ix_metadata_gate_evaluation_events_metadata_snapshot_digest",
        "metadata_gate_evaluation_events",
        ["metadata_snapshot_digest"],
    )
    op.create_index(
        "ix_metadata_gate_evaluation_events_evaluated_at",
        "metadata_gate_evaluation_events",
        ["evaluated_at"],
    )
    op.create_index(
        "ix_metadata_gate_candidate_evaluated",
        "metadata_gate_evaluation_events",
        ["candidate_id", "evaluated_at"],
    )
    _create_immutable_triggers("image_rights_evidence", "image rights evidence")
    _create_immutable_triggers(
        "metadata_gate_evaluation_events",
        "metadata gate evaluation events",
    )


def downgrade() -> None:
    bind = op.get_bind()
    rights_count = int(
        bind.execute(sa.text("SELECT COUNT(*) FROM image_rights_evidence")).scalar_one()
    )
    event_count = int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM metadata_gate_evaluation_events")
        ).scalar_one()
    )
    if rights_count or event_count:
        raise RuntimeError(
            "cannot downgrade metadata gate migration: immutable evidence exists"
        )

    _drop_immutable_triggers("metadata_gate_evaluation_events")
    _drop_immutable_triggers("image_rights_evidence")
    op.drop_index(
        "ix_metadata_gate_candidate_evaluated",
        table_name="metadata_gate_evaluation_events",
    )
    op.drop_index(
        "ix_metadata_gate_evaluation_events_evaluated_at",
        table_name="metadata_gate_evaluation_events",
    )
    op.drop_index(
        "ix_metadata_gate_evaluation_events_metadata_snapshot_digest",
        table_name="metadata_gate_evaluation_events",
    )
    op.drop_index(
        "ix_metadata_gate_evaluation_events_candidate_id",
        table_name="metadata_gate_evaluation_events",
    )
    op.drop_table("metadata_gate_evaluation_events")
    op.drop_index(
        "ix_image_rights_candidate_verified",
        table_name="image_rights_evidence",
    )
    op.drop_index(
        "ix_image_rights_evidence_verified_at",
        table_name="image_rights_evidence",
    )
    op.drop_index(
        "ix_image_rights_evidence_candidate_id",
        table_name="image_rights_evidence",
    )
    op.drop_table("image_rights_evidence")
