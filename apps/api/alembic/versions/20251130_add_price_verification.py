"""Add price verification tables

Revision ID: 20251130_price_verify
Revises: 20251223_create_rules_audit_table
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

# revision identifiers, used by Alembic.
revision = '20251130_price_verify'
down_revision = '20251223_create_rules_audit_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create commodities table
    op.create_table(
        'commodities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('default_unit', sa.String(50), nullable=False),
        sa.Column('alternate_units', JSON),
        sa.Column('data_sources', JSON),
        sa.Column('source_codes', JSON),
        sa.Column('typical_min_price', sa.Float),
        sa.Column('typical_max_price', sa.Float),
        sa.Column('description', sa.Text),
        sa.Column('hs_codes', JSON),
        sa.Column('aliases', JSON),
        sa.Column('regions', JSON),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.func.now()),
    )
    
    # Create commodity prices table
    op.create_table(
        'commodity_prices',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('commodity_code', sa.String(50), nullable=False, index=True),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), default='USD'),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('source_reference', sa.String(200)),
        sa.Column('price_date', sa.TIMESTAMP, nullable=False, index=True),
        sa.Column('fetched_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('is_spot', sa.Boolean, default=True),
        sa.Column('contract_month', sa.String(10)),
        sa.Column('quality_grade', sa.String(50)),
        sa.Column('metadata', JSON),
    )
    
    # Create price verifications table
    op.create_table(
        'price_verifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('commodity_code', sa.String(50), nullable=False),
        sa.Column('commodity_name', sa.String(200)),
        sa.Column('document_price', sa.Float, nullable=False),
        sa.Column('document_currency', sa.String(3), default='USD'),
        sa.Column('document_unit', sa.String(50), nullable=False),
        sa.Column('document_quantity', sa.Float),
        sa.Column('total_value', sa.Float),
        sa.Column('normalized_price', sa.Float),
        sa.Column('normalized_unit', sa.String(50)),
        sa.Column('market_price', sa.Float),
        sa.Column('market_price_low', sa.Float),
        sa.Column('market_price_high', sa.Float),
        sa.Column('market_source', sa.String(100)),
        sa.Column('market_date', sa.TIMESTAMP),
        sa.Column('variance_percent', sa.Float),
        sa.Column('variance_absolute', sa.Float),
        sa.Column('risk_level', sa.String(20)),
        sa.Column('risk_flags', JSON),
        sa.Column('verdict', sa.String(20)),
        sa.Column('verdict_reason', sa.Text),
        sa.Column('document_type', sa.String(50)),
        sa.Column('document_reference', sa.String(200)),
        sa.Column('origin_country', sa.String(3)),
        sa.Column('destination_country', sa.String(3)),
        sa.Column('source_type', sa.String(20), default='manual'),
        sa.Column('extracted_data', JSON),
        sa.Column('session_id', sa.String(100)),
        sa.Column('user_id', UUID(as_uuid=True)),
        sa.Column('company_id', UUID(as_uuid=True)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.func.now()),
        sa.Column('exported_pdf', sa.Boolean, default=False),
        sa.Column('exported_at', sa.TIMESTAMP),
    )
    
    # Create indexes
    op.create_index('ix_commodity_prices_code_date', 'commodity_prices', ['commodity_code', 'price_date'])
    op.create_index('ix_price_verifications_created', 'price_verifications', ['created_at'])
    op.create_index('ix_price_verifications_commodity', 'price_verifications', ['commodity_code'])


def downgrade():
    op.drop_index('ix_price_verifications_commodity')
    op.drop_index('ix_price_verifications_created')
    op.drop_index('ix_commodity_prices_code_date')
    op.drop_table('price_verifications')
    op.drop_table('commodity_prices')
    op.drop_table('commodities')

