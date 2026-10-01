"""add controlled batch reservation release

Revision ID: e2f6b8c4d1a7
Revises: c1e5a7b9d3f2
Create Date: 2026-08-10

Adds a historical RELEASED batch-item state, immutable release evidence, and
active-only operation/item uniqueness.  This migration performs no release.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f6b8c4d1a7"
down_revision: Union[str, Sequence[str], None] = "c1e5a7b9d3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ITEM_STATES_WITH_RELEASED = (
    "'QUEUED','RESERVED','PREFLIGHT','EXECUTING','WP_DRAFTED',"
    "'X_DRAFTED','VERIFYING','COMPLETED','HOLD','FAILED',"
    "'RECONCILIATION_REQUIRED','RELEASED'"
)

ITEM_STATES_BEFORE_RELEASED = (
    "'QUEUED','RESERVED','PREFLIGHT','EXECUTING','WP_DRAFTED',"
    "'X_DRAFTED','VERIFYING','COMPLETED','HOLD','FAILED',"
    "'RECONCILIATION_REQUIRED'"
)


def _status_constraint_name() -> str:
    constraints = sa.inspect(op.get_bind()).get_check_constraints(
        "ebook_batch_items"
    )
    for constraint in constraints:
        sqltext = str(constraint.get("sqltext") or "")
        if "status" in sqltext and "RESERVED" in sqltext:
            name = constraint.get("name")
            if name:
                return str(name)
    raise RuntimeError("ebook batch item status constraint not found")


def _replace_item_status_constraint(states: str) -> None:
    old_name = _status_constraint_name()
    with op.batch_alter_table(
        "ebook_batch_items",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(op.f(old_name), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_ebook_batch_items_status_with_release"),
            f"status IN ({states})",
        )


def upgrade() -> None:
    op.drop_index(
        "ux_ebook_batch_items_operation_item",
        table_name="ebook_batch_items",
    )
    _replace_item_status_constraint(ITEM_STATES_WITH_RELEASED)
    op.create_index(
        "ux_ebook_batch_items_active_operation_item",
        "ebook_batch_items",
        ["operation", "ebook_item_id"],
        unique=True,
        sqlite_where=sa.text("status <> 'RELEASED'"),
        postgresql_where=sa.text("status <> 'RELEASED'"),
    )

    op.create_table(
        "ebook_batch_reservation_release_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column(
            "batch_item_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_batch_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_batch_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "candidate_item_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approval_remediation_event_id",
            sa.String(length=36),
            sa.ForeignKey(
                "workflow_approval_remediation_events.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("release_actor", sa.String(length=128), nullable=False),
        sa.Column("before_state", sa.String(length=32), nullable=False),
        sa.Column("after_state", sa.String(length=32), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("source_batch_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "candidate_workflow_state",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "candidate_review_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "approval_execution_eligibility",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "execution_evidence_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column("snapshot_digest", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "before_state = 'RESERVED' AND after_state = 'RELEASED'",
            name="valid_batch_reservation_release_transition",
        ),
        sa.CheckConstraint(
            "slot_index >= 1 AND slot_index <= 5",
            name="valid_batch_reservation_release_slot",
        ),
        sa.CheckConstraint(
            "candidate_workflow_state = 'REVIEW' "
            "AND candidate_review_status = 'NOT_REVIEWED'",
            name="valid_batch_reservation_release_candidate_state",
        ),
        sa.CheckConstraint(
            "approval_execution_eligibility = 'INELIGIBLE'",
            name="valid_batch_reservation_release_approval_state",
        ),
        sa.CheckConstraint(
            "execution_evidence_status = 'ABSENT'",
            name="valid_batch_reservation_release_execution_evidence",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) > 0",
            name="batch_reservation_release_reason_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(release_actor)) > 0",
            name="batch_reservation_release_actor_not_blank",
        ),
        sa.CheckConstraint(
            "length(snapshot_digest) = 64",
            name="valid_batch_reservation_release_snapshot_digest",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_batch_reservation_release_idempotency",
        ),
        sa.UniqueConstraint(
            "batch_item_id",
            name="uq_batch_reservation_release_batch_item",
        ),
    )
    op.create_index(
        "ix_batch_reservation_release_candidate",
        "ebook_batch_reservation_release_events",
        ["candidate_item_id"],
    )
    op.create_index(
        "ix_batch_reservation_release_remediation",
        "ebook_batch_reservation_release_events",
        ["approval_remediation_event_id"],
    )
    op.create_index(
        "ix_batch_reservation_release_created_at",
        "ebook_batch_reservation_release_events",
        ["created_at"],
    )

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER ebook_batch_reservation_release_no_update
            BEFORE UPDATE ON ebook_batch_reservation_release_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'ebook batch reservation release events are immutable'
                );
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER ebook_batch_reservation_release_no_delete
            BEFORE DELETE ON ebook_batch_reservation_release_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'ebook batch reservation release events are immutable'
                );
            END
            """
        )
    elif dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_ebook_batch_reservation_release_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION
                    'ebook batch reservation release events are immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER ebook_batch_reservation_release_no_mutation
            BEFORE UPDATE OR DELETE
            ON ebook_batch_reservation_release_events
            FOR EACH ROW EXECUTE FUNCTION
                reject_ebook_batch_reservation_release_mutation()
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    released_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ebook_batch_items "
            "WHERE status = 'RELEASED'"
        )
    ).scalar_one()
    release_event_count = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM ebook_batch_reservation_release_events"
        )
    ).scalar_one()
    if int(released_count) > 0:
        raise RuntimeError(
            "cannot downgrade controlled release migration: RELEASED batch "
            "item history exists"
        )
    if int(release_event_count) > 0:
        raise RuntimeError(
            "cannot downgrade controlled release migration: release event "
            "history exists"
        )

    dialect = bind.dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER ebook_batch_reservation_release_no_delete")
        op.execute("DROP TRIGGER ebook_batch_reservation_release_no_update")
    elif dialect == "postgresql":
        op.execute(
            "DROP TRIGGER ebook_batch_reservation_release_no_mutation "
            "ON ebook_batch_reservation_release_events"
        )
        op.execute(
            "DROP FUNCTION reject_ebook_batch_reservation_release_mutation()"
        )

    op.drop_index(
        "ix_batch_reservation_release_created_at",
        table_name="ebook_batch_reservation_release_events",
    )
    op.drop_index(
        "ix_batch_reservation_release_remediation",
        table_name="ebook_batch_reservation_release_events",
    )
    op.drop_index(
        "ix_batch_reservation_release_candidate",
        table_name="ebook_batch_reservation_release_events",
    )
    op.drop_table("ebook_batch_reservation_release_events")
    op.drop_index(
        "ux_ebook_batch_items_active_operation_item",
        table_name="ebook_batch_items",
    )
    _replace_item_status_constraint(ITEM_STATES_BEFORE_RELEASED)
    op.create_index(
        "ux_ebook_batch_items_operation_item",
        "ebook_batch_items",
        ["operation", "ebook_item_id"],
        unique=True,
    )
