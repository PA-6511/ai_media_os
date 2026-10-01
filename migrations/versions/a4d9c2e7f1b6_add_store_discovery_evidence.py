"""add immutable store discovery evidence

Revision ID: a4d9c2e7f1b6
Revises: f3a7c9e1b5d2
Create Date: 2026-08-13
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4d9c2e7f1b6"
down_revision: Union[str, Sequence[str], None] = "f3a7c9e1b5d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_immutable_triggers() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(
                f"""
                CREATE TRIGGER store_discovery_evidence_no_{operation.lower()}
                BEFORE {operation} ON store_discovery_evidence
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'store discovery evidence is immutable'
                    );
                END
                """
            )

    elif dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_store_discovery_evidence_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'store discovery evidence is immutable';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER store_discovery_evidence_no_mutation
            BEFORE UPDATE OR DELETE ON store_discovery_evidence
            FOR EACH ROW
            EXECUTE FUNCTION reject_store_discovery_evidence_mutation()
            """
        )


def _drop_immutable_triggers() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        op.execute("DROP TRIGGER store_discovery_evidence_no_delete")
        op.execute("DROP TRIGGER store_discovery_evidence_no_update")

    elif dialect == "postgresql":
        op.execute(
            "DROP TRIGGER store_discovery_evidence_no_mutation "
            "ON store_discovery_evidence"
        )
        op.execute(
            "DROP FUNCTION reject_store_discovery_evidence_mutation()"
        )


def upgrade() -> None:
    op.create_table(
        "store_discovery_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column(
            "candidate_id",
            sa.String(length=36),
            sa.ForeignKey("ebook_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("store_name", sa.String(length=32), nullable=False),
        sa.Column(
            "discovery_status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "verification_method",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("verified_by", sa.String(length=128), nullable=False),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "store_name IN ('amazon', 'rakuten_kobo', 'dmm')",
            name="valid_store_discovery_store_name",
        ),
        sa.CheckConstraint(
            "discovery_status = 'VERIFIED_NOT_FOUND'",
            name="valid_store_discovery_status",
        ),
        sa.CheckConstraint(
            "length(trim(verification_method)) > 0",
            name="store_discovery_verification_method_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_reference)) > 0",
            name="store_discovery_evidence_reference_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(verified_by)) > 0",
            name="store_discovery_verified_by_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_store_discovery_evidence_candidate_id",
        "store_discovery_evidence",
        ["candidate_id"],
    )
    op.create_index(
        "ix_store_discovery_evidence_store_name",
        "store_discovery_evidence",
        ["store_name"],
    )
    op.create_index(
        "ix_store_discovery_evidence_verified_at",
        "store_discovery_evidence",
        ["verified_at"],
    )
    op.create_index(
        "ix_store_discovery_candidate_store_verified",
        "store_discovery_evidence",
        ["candidate_id", "store_name", "verified_at"],
    )

    _create_immutable_triggers()


def downgrade() -> None:
    bind = op.get_bind()

    count = int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM store_discovery_evidence")
        ).scalar_one()
    )

    if count:
        raise RuntimeError(
            "cannot downgrade store discovery migration: "
            "immutable evidence exists"
        )

    _drop_immutable_triggers()

    op.drop_index(
        "ix_store_discovery_candidate_store_verified",
        table_name="store_discovery_evidence",
    )
    op.drop_index(
        "ix_store_discovery_evidence_verified_at",
        table_name="store_discovery_evidence",
    )
    op.drop_index(
        "ix_store_discovery_evidence_store_name",
        table_name="store_discovery_evidence",
    )
    op.drop_index(
        "ix_store_discovery_evidence_candidate_id",
        table_name="store_discovery_evidence",
    )

    op.drop_table("store_discovery_evidence")
