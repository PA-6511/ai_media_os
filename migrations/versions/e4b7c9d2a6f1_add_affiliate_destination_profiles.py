"""Add destination-scoped affiliate profiles and offer links.

Revision ID: e4b7c9d2a6f1
Revises: c8a1e7f9b2d4

The legacy ``store_offers.affiliate_url`` column is intentionally retained.
A clear legacy DMM account setting is copied only to ``blog_main``.  It is
never copied to ``x_main``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
import uuid

from alembic import op
import sqlalchemy as sa


revision = "e4b7c9d2a6f1"
down_revision = "c8a1e7f9b2d4"
branch_labels = None
depends_on = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _legacy_dmm_profile(connection: sa.Connection) -> tuple[str, str] | None:
    inspector = sa.inspect(connection)
    if "affiliate_account_settings" not in inspector.get_table_names():
        return None
    row = connection.execute(
        sa.text(
            "SELECT affiliate_id, enabled "
            "FROM affiliate_account_settings WHERE service_name = 'dmm'"
        )
    ).one_or_none()
    if row is None:
        return None
    affiliate_id = str(row.affiliate_id or "").strip()
    if not affiliate_id:
        return None
    profile_id = str(uuid.uuid4())
    now = _utc_now()
    connection.execute(
        sa.text(
            "INSERT INTO affiliate_destination_profiles "
            "(id, provider, destination_type, destination_key, display_name, "
            "affiliate_id, channel, channel_id, is_active, created_at, updated_at) "
            "VALUES (:id, 'dmm', 'wordpress', 'blog_main', :display_name, "
            ":affiliate_id, 'toolbar', 'text', :is_active, :now, :now)"
        ),
        {
            "id": profile_id,
            "display_name": "メインブログ",
            "affiliate_id": affiliate_id,
            "is_active": bool(row.enabled),
            "now": now,
        },
    )
    return profile_id, affiliate_id


def _affiliate_id_from_legacy_url(value: str | None) -> str | None:
    parsed = urlsplit(str(value or "").strip())
    if parsed.scheme != "https" or parsed.hostname != "al.dmm.com":
        return None
    values = parse_qs(parsed.query, keep_blank_values=True).get("af_id", [])
    if len(values) != 1 or not values[0].strip():
        return None
    return values[0].strip()


def _migrate_matching_legacy_links(
    connection: sa.Connection,
    *,
    profile_id: str,
    affiliate_id: str,
) -> None:
    rows = connection.execute(
        sa.text(
            "SELECT id, affiliate_url FROM store_offers "
            "WHERE store_name = 'dmm' AND affiliate_url IS NOT NULL"
        )
    ).all()
    now = _utc_now()
    for row in rows:
        if _affiliate_id_from_legacy_url(row.affiliate_url) != affiliate_id:
            continue
        connection.execute(
            sa.text(
                "INSERT INTO store_offer_affiliate_links "
                "(id, store_offer_id, profile_id, affiliate_url, "
                "generation_method, source_affiliate_id, generated_at, updated_at) "
                "VALUES (:id, :store_offer_id, :profile_id, :affiliate_url, "
                ":generation_method, :source_affiliate_id, :now, :now)"
            ),
            {
                "id": str(uuid.uuid4()),
                "store_offer_id": row.id,
                "profile_id": profile_id,
                "affiliate_url": row.affiliate_url,
                "generation_method": "LEGACY_DMM_AFFILIATE_URL_MATCH",
                "source_affiliate_id": affiliate_id,
                "now": now,
            },
        )


def upgrade() -> None:
    op.create_table(
        "affiliate_destination_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("destination_type", sa.String(length=64), nullable=False),
        sa.Column("destination_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("affiliate_id", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("channel_id", sa.String(length=64), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(provider)) > 0",
            name="affiliate_destination_provider_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(destination_type)) > 0",
            name="affiliate_destination_type_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(destination_key)) > 0",
            name="affiliate_destination_key_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(affiliate_id)) > 0",
            name="affiliate_destination_id_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "destination_key",
            name="affiliate_destination_profile_identity",
        ),
    )
    op.create_index(
        "ix_affiliate_destination_profiles_provider",
        "affiliate_destination_profiles",
        ["provider"],
    )
    op.create_index(
        "ix_affiliate_destination_profiles_destination_type",
        "affiliate_destination_profiles",
        ["destination_type"],
    )
    op.create_index(
        "ix_affiliate_destination_profiles_is_active",
        "affiliate_destination_profiles",
        ["is_active"],
    )

    op.create_table(
        "store_offer_affiliate_links",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("store_offer_id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("affiliate_url", sa.Text(), nullable=False),
        sa.Column("generation_method", sa.String(length=64), nullable=False),
        sa.Column("source_affiliate_id", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(trim(affiliate_url)) > 0",
            name="store_offer_affiliate_url_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(source_affiliate_id)) > 0",
            name="store_offer_source_affiliate_id_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["store_offer_id"], ["store_offers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["affiliate_destination_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "store_offer_id",
            "profile_id",
            name="store_offer_affiliate_profile_identity",
        ),
    )
    op.create_index(
        "ix_store_offer_affiliate_links_store_offer_id",
        "store_offer_affiliate_links",
        ["store_offer_id"],
    )
    op.create_index(
        "ix_store_offer_affiliate_links_profile_id",
        "store_offer_affiliate_links",
        ["profile_id"],
    )

    connection = op.get_bind()
    legacy_profile = _legacy_dmm_profile(connection)
    if legacy_profile is not None:
        profile_id, affiliate_id = legacy_profile
        _migrate_matching_legacy_links(
            connection,
            profile_id=profile_id,
            affiliate_id=affiliate_id,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_store_offer_affiliate_links_profile_id",
        table_name="store_offer_affiliate_links",
    )
    op.drop_index(
        "ix_store_offer_affiliate_links_store_offer_id",
        table_name="store_offer_affiliate_links",
    )
    op.drop_table("store_offer_affiliate_links")
    op.drop_index(
        "ix_affiliate_destination_profiles_is_active",
        table_name="affiliate_destination_profiles",
    )
    op.drop_index(
        "ix_affiliate_destination_profiles_destination_type",
        table_name="affiliate_destination_profiles",
    )
    op.drop_index(
        "ix_affiliate_destination_profiles_provider",
        table_name="affiliate_destination_profiles",
    )
    op.drop_table("affiliate_destination_profiles")
