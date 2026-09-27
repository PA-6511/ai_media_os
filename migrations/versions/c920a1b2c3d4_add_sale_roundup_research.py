"""Add sale roundup, copy experiments and cumulative metrics (additive)."""
from alembic import op
import sqlalchemy as sa
revision = "c920a1b2c3d4"
down_revision = "f4a7c1d9e2b5"
branch_labels = None
depends_on = None

def upgrade():
    # Additive tables only; no existing table alterations.
    op.create_table('sale_roundup_campaigns',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
    sa.Column('starts_at', sa.String(length=40), nullable=False),
    sa.Column('ends_at', sa.String(length=40), nullable=False),
    sa.Column('imported_at', sa.String(length=40), nullable=False),
    sa.Column('source_generated_at', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_roundup_campaigns'))
    )
    op.create_table('sale_roundup_offers',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('campaign_id', sa.String(length=128), nullable=False),
    sa.Column('ebook_item_id', sa.String(length=128), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.Column('block_reasons', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['campaign_id'], ['sale_roundup_campaigns.id'], name=op.f('fk_sale_roundup_offers_campaign_id_sale_roundup_campaigns')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_roundup_offers'))
    )
    op.create_index(op.f('ix_sale_roundup_offers_campaign_id'), 'sale_roundup_offers', ['campaign_id'], unique=False)
    op.create_table('sale_copy_experiments',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('campaign_id', sa.String(length=128), nullable=False),
    sa.Column('snapshot_hash', sa.String(length=64), nullable=False),
    sa.Column('snapshot', sa.JSON(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=False),
    sa.Column('wordpress_state', sa.String(length=32), nullable=False),
    sa.Column('wordpress_post_id', sa.Integer(), nullable=True),
    sa.Column('article_url', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['campaign_id'], ['sale_roundup_campaigns.id'], name=op.f('fk_sale_copy_experiments_campaign_id_sale_roundup_campaigns')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_copy_experiments'))
    )
    op.create_index(op.f('ix_sale_copy_experiments_campaign_id'), 'sale_copy_experiments', ['campaign_id'], unique=False)
    op.create_table('sale_copy_variants',
    sa.Column('id', sa.String(length=64), nullable=False),
    sa.Column('experiment_id', sa.String(length=64), nullable=False),
    sa.Column('components', sa.JSON(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('draft_request', sa.JSON(), nullable=False),
    sa.Column('review_status', sa.String(length=16), nullable=False),
    sa.Column('reviewed_by', sa.String(length=128), nullable=True),
    sa.Column('reviewed_at', sa.String(length=40), nullable=True),
    sa.ForeignKeyConstraint(['experiment_id'], ['sale_copy_experiments.id'], name=op.f('fk_sale_copy_variants_experiment_id_sale_copy_experiments')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_copy_variants'))
    )
    op.create_index(op.f('ix_sale_copy_variants_experiment_id'), 'sale_copy_variants', ['experiment_id'], unique=False)
    op.create_table('sale_copy_metric_snapshots',
    sa.Column('post_id', sa.String(length=128), nullable=False),
    sa.Column('variant_id', sa.String(length=64), nullable=False),
    sa.Column('posted_at', sa.String(length=40), nullable=False),
    sa.Column('observed_at', sa.String(length=40), nullable=False),
    sa.Column('source', sa.String(length=128), nullable=False),
    sa.Column('attribution_basis', sa.String(length=32), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('impressions', sa.Integer(), nullable=True),
    sa.Column('clicks', sa.Integer(), nullable=True),
    sa.Column('orders', sa.Integer(), nullable=True),
    sa.Column('order_revenue', sa.Float(), nullable=True),
    sa.Column('referral_fee', sa.Float(), nullable=True),
    sa.CheckConstraint('clicks IS NULL OR clicks >= 0', name=op.f('ck_sale_copy_metric_snapshots_sale_clicks_nonnegative')),
    sa.CheckConstraint('impressions IS NULL OR impressions >= 0', name=op.f('ck_sale_copy_metric_snapshots_sale_impressions_nonnegative')),
    sa.CheckConstraint('order_revenue IS NULL OR order_revenue >= 0', name=op.f('ck_sale_copy_metric_snapshots_sale_order_revenue_nonnegative')),
    sa.CheckConstraint('orders IS NULL OR orders >= 0', name=op.f('ck_sale_copy_metric_snapshots_sale_orders_nonnegative')),
    sa.CheckConstraint('referral_fee IS NULL OR referral_fee >= 0', name=op.f('ck_sale_copy_metric_snapshots_sale_referral_fee_nonnegative')),
    sa.ForeignKeyConstraint(['variant_id'], ['sale_copy_variants.id'], name=op.f('fk_sale_copy_metric_snapshots_variant_id_sale_copy_variants')),
    sa.PrimaryKeyConstraint('post_id', name=op.f('pk_sale_copy_metric_snapshots'))
    )
    op.create_index(op.f('ix_sale_copy_metric_snapshots_variant_id'), 'sale_copy_metric_snapshots', ['variant_id'], unique=False)
    op.create_table('sale_roundup_settings',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('mode', sa.String(length=16), nullable=False),
    sa.Column('last_run', sa.JSON(), nullable=True),
    sa.CheckConstraint("mode IN ('STOP','MANUAL','SEMI_AUTO')", name=op.f('ck_sale_roundup_settings_sale_valid_mode')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sale_roundup_settings'))
    )


def downgrade():
    op.drop_table('sale_roundup_settings')
    op.drop_table('sale_copy_metric_snapshots')
    op.drop_table('sale_copy_variants')
    op.drop_table('sale_copy_experiments')
    op.drop_table('sale_roundup_offers')
    op.drop_table('sale_roundup_campaigns')
