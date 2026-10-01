"""add ebook tag schema

Revision ID: d9a4c7e2f1b6
Revises: b6f1d8e3c2a7
Create Date: 2026-08-06

Creates the normalized tag infrastructure only.

This migration intentionally:
- does not insert tag master rows;
- does not classify existing ebook items;
- does not modify public JSON;
- does not enable automatic tag rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a4c7e2f1b6"
down_revision: Union[str, Sequence[str], None] = "b6f1d8e3c2a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ebook_tags",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "tag_key",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "slug",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "display_name",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "tag_group",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "is_filterable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "tag_key",
            name="uq_ebook_tags_tag_key",
        ),
        sa.UniqueConstraint(
            "slug",
            name="uq_ebook_tags_slug",
        ),
    )

    op.create_index(
        "ix_ebook_tags_group_active_order",
        "ebook_tags",
        [
            "tag_group",
            "is_active",
            "display_order",
        ],
        unique=False,
    )

    op.create_table(
        "ebook_item_tags",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "ebook_item_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "assignment_source",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'MANUAL'"),
        ),
        sa.Column(
            "confidence",
            sa.Numeric(
                precision=5,
                scale=4,
            ),
            nullable=True,
        ),
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "assigned_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "approved_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "note",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            """
            confidence IS NULL
            OR (
                confidence >= 0
                AND confidence <= 1
            )
            """,
            name="ck_ebook_item_tags_confidence",
        ),
        sa.CheckConstraint(
            """
            assignment_source IN (
                'MANUAL',
                'IMPORT',
                'RULE',
                'AI',
                'PUBLISHER'
            )
            """,
            name="ck_ebook_item_tags_assignment_source",
        ),
        sa.CheckConstraint(
            """
            review_status IN (
                'UNREVIEWED',
                'PENDING',
                'APPROVED',
                'REJECTED'
            )
            """,
            name="ck_ebook_item_tags_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["ebook_item_id"],
            ["ebook_items.id"],
            name="fk_ebook_item_tags_ebook_item_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["ebook_tags.id"],
            name="fk_ebook_item_tags_tag_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "ebook_item_id",
            "tag_id",
            name="uq_ebook_item_tags_item_tag",
        ),
    )

    op.create_index(
        "ix_ebook_item_tags_item_review",
        "ebook_item_tags",
        [
            "ebook_item_id",
            "review_status",
        ],
        unique=False,
    )

    op.create_index(
        "ix_ebook_item_tags_tag_review",
        "ebook_item_tags",
        [
            "tag_id",
            "review_status",
        ],
        unique=False,
    )

    op.create_table(
        "ebook_tag_aliases",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "alias_text",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "normalized_alias",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'MANUAL'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["ebook_tags.id"],
            name="fk_ebook_tag_aliases_tag_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "normalized_alias",
            name="uq_ebook_tag_aliases_normalized_alias",
        ),
    )

    op.create_index(
        "ix_ebook_tag_aliases_tag_active",
        "ebook_tag_aliases",
        [
            "tag_id",
            "is_active",
        ],
        unique=False,
    )

    op.create_table(
        "ebook_tag_rules",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "tag_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "rule_name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "rule_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "field_name",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "operator",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "match_value",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "confidence",
            sa.Numeric(
                precision=5,
                scale=4,
            ),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'PENDING'"),
        ),
        sa.Column(
            "created_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            """
            confidence IS NULL
            OR (
                confidence >= 0
                AND confidence <= 1
            )
            """,
            name="ck_ebook_tag_rules_confidence",
        ),
        sa.CheckConstraint(
            """
            review_status IN (
                'UNREVIEWED',
                'PENDING',
                'APPROVED',
                'REJECTED'
            )
            """,
            name="ck_ebook_tag_rules_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["ebook_tags.id"],
            name="fk_ebook_tag_rules_tag_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tag_id",
            "rule_name",
            name="uq_ebook_tag_rules_tag_rule_name",
        ),
    )

    op.create_index(
        "ix_ebook_tag_rules_tag_active_priority",
        "ebook_tag_rules",
        [
            "tag_id",
            "is_active",
            "priority",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ebook_tag_rules_tag_active_priority",
        table_name="ebook_tag_rules",
    )
    op.drop_table("ebook_tag_rules")

    op.drop_index(
        "ix_ebook_tag_aliases_tag_active",
        table_name="ebook_tag_aliases",
    )
    op.drop_table("ebook_tag_aliases")

    op.drop_index(
        "ix_ebook_item_tags_tag_review",
        table_name="ebook_item_tags",
    )
    op.drop_index(
        "ix_ebook_item_tags_item_review",
        table_name="ebook_item_tags",
    )
    op.drop_table("ebook_item_tags")

    op.drop_index(
        "ix_ebook_tags_group_active_order",
        table_name="ebook_tags",
    )
    op.drop_table("ebook_tags")
