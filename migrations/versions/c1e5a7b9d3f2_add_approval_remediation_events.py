"""add immutable workflow approval remediation events

Revision ID: c1e5a7b9d3f2
Revises: b8d6f0e2a4c1
Create Date: 2026-08-09

This migration only adds the dedicated approval-remediation evidence and
supersession relation. It does not remediate any candidate or release a batch.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1e5a7b9d3f2"
down_revision: Union[str, Sequence[str], None] = "b8d6f0e2a4c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_approval_remediation_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "event_type",
            sa.String(length=64),
            nullable=False,
            server_default="AUTOMATED_APPROVAL_REMEDIATION",
        ),
        sa.Column(
            "candidate_item_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "superseded_approval_request_id",
            sa.String(length=36),
            sa.ForeignKey(
                "workflow_approval_requests.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "related_batch_item_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_batch_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "remediation_actor",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "before_workflow_state",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "before_review_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "after_workflow_state",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "after_review_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "metadata_snapshot_digest",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "human_decision_evidence_status",
            sa.String(length=32),
            nullable=False,
            server_default="NOT_PROVEN",
        ),
        sa.Column(
            "expected_execution_eligibility",
            sa.String(length=32),
            nullable=False,
            server_default="INELIGIBLE",
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=64),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type = 'AUTOMATED_APPROVAL_REMEDIATION'",
            name="valid_approval_remediation_event_type",
        ),
        sa.CheckConstraint(
            "before_workflow_state = 'READY' "
            "AND before_review_status = 'APPROVED' "
            "AND after_workflow_state = 'REVIEW' "
            "AND after_review_status = 'NOT_REVIEWED'",
            name="valid_approval_remediation_transition",
        ),
        sa.CheckConstraint(
            "human_decision_evidence_status = 'NOT_PROVEN'",
            name="valid_approval_remediation_human_evidence",
        ),
        sa.CheckConstraint(
            "expected_execution_eligibility = 'INELIGIBLE'",
            name="valid_approval_remediation_execution_eligibility",
        ),
        sa.CheckConstraint(
            "length(metadata_snapshot_digest) = 64",
            name="valid_approval_remediation_metadata_digest",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="approval_remediation_reason_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(remediation_actor)) > 0",
            name="approval_remediation_actor_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "superseded_approval_request_id",
            name="uq_approval_remediation_superseded_request",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_approval_remediation_idempotency_key",
        ),
    )
    op.create_index(
        "ix_approval_remediation_candidate",
        "workflow_approval_remediation_events",
        ["candidate_item_id"],
    )
    op.create_index(
        "ix_approval_remediation_batch_item",
        "workflow_approval_remediation_events",
        ["related_batch_item_id"],
    )
    op.create_index(
        "ix_approval_remediation_actor",
        "workflow_approval_remediation_events",
        ["remediation_actor"],
    )
    op.create_index(
        "ix_approval_remediation_created_at",
        "workflow_approval_remediation_events",
        ["created_at"],
    )

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER workflow_approval_remediation_no_update
            BEFORE UPDATE ON workflow_approval_remediation_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'workflow approval remediation events are immutable'
                );
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER workflow_approval_remediation_no_delete
            BEFORE DELETE ON workflow_approval_remediation_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'workflow approval remediation events are immutable'
                );
            END
            """
        )
    elif dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_workflow_approval_remediation_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION
                    'workflow approval remediation events are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER workflow_approval_remediation_no_mutation
            BEFORE UPDATE OR DELETE
            ON workflow_approval_remediation_events
            FOR EACH ROW EXECUTE FUNCTION
                reject_workflow_approval_remediation_mutation()
            """
        )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            "DROP TRIGGER workflow_approval_remediation_no_delete"
        )
        op.execute(
            "DROP TRIGGER workflow_approval_remediation_no_update"
        )
    elif dialect == "postgresql":
        op.execute(
            """
            DROP TRIGGER workflow_approval_remediation_no_mutation
            ON workflow_approval_remediation_events
            """
        )
        op.execute(
            """
            DROP FUNCTION
                reject_workflow_approval_remediation_mutation()
            """
        )

    op.drop_index(
        "ix_approval_remediation_created_at",
        table_name="workflow_approval_remediation_events",
    )
    op.drop_index(
        "ix_approval_remediation_actor",
        table_name="workflow_approval_remediation_events",
    )
    op.drop_index(
        "ix_approval_remediation_batch_item",
        table_name="workflow_approval_remediation_events",
    )
    op.drop_index(
        "ix_approval_remediation_candidate",
        table_name="workflow_approval_remediation_events",
    )
    op.drop_table("workflow_approval_remediation_events")
