"""add ebook batch runtime control

Revision ID: b8d6f0e2a4c1
Revises: a7c5e9d1f3b2
Create Date: 2026-08-08

Persistent runtime mode for the five-item draft loop.

Supported modes:
- STOP
- SEMI_AUTO
- AUTO_DRAFT

No publication or X-posting mode exists here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d6f0e2a4c1"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "a7c5e9d1f3b2"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "ebook_batch_runtime_control",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "mode",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text(
                "'STOP'"
            ),
        ),
        sa.Column(
            "emergency_stop",
            sa.Integer(),
            nullable=False,
            server_default=sa.text(
                "0"
            ),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP"
            ),
        ),
        sa.CheckConstraint(
            "id = 1",
            name=(
                "ck_ebook_batch_runtime_"
                "control_singleton"
            ),
        ),
        sa.CheckConstraint(
            """
            mode IN (
                'STOP',
                'SEMI_AUTO',
                'AUTO_DRAFT'
            )
            """,
            name=(
                "ck_ebook_batch_runtime_"
                "control_mode"
            ),
        ),
        sa.CheckConstraint(
            "emergency_stop IN (0, 1)",
            name=(
                "ck_ebook_batch_runtime_"
                "control_emergency_stop"
            ),
        ),
    )

    op.execute(
        """
        INSERT INTO ebook_batch_runtime_control (
            id,
            mode,
            emergency_stop
        )
        VALUES (
            1,
            'STOP',
            0
        )
        """
    )


def downgrade() -> None:
    op.drop_table(
        "ebook_batch_runtime_control"
    )
