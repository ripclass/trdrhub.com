"""Commodity resolution system - database-driven commodities with HS codes

Revision ID: 20251201_commodity_resolution
Revises: 
Create Date: 2025-12-01

This migration creates:
1. commodities table - database-driven commodity management
2. hs_codes table - HS code lookup for global commodity classification
3. commodity_requests table - user-submitted commodity requests
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid


# revision identifiers
revision = '20251201_commodity_resolution'
down_revision = '20251201_audit'  # Fixed: chain after audit_logs
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Commodities table - replaces hardcoded COMMODITIES_DATABASE
    op.create_table(
        'commodities',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('unit', sa.String(20), nullable=False),
        sa.Column('aliases', JSONB, default=list),  # ["dried fish", "stockfish"]
        sa.Column('hs_codes', JSONB, default=list),  # ["0305.59", "0305.69"]
        sa.Column('price_low', sa.Numeric(12, 4), nullable=True),
        sa.Column('price_high', sa.Numeric(12, 4), nullable=True),
        sa.Column('current_estimate', sa.Numeric(12, 4), nullable=True),
        sa.Column('data_sources', JSONB, default=dict),  # {"world_bank": "CODE", "fred": "CODE"}
        sa.Column('source_codes', JSONB, default=dict),
        sa.Column('verified', sa.Boolean, default=False),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_by', sa.String(100), nullable=True),  # user_id, "system", "ai"
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Index for full-text search on name and aliases
    op.create_index('ix_commodities_name_lower', 'commodities', [sa.text('lower(name)')])
    
    # 2. HS Codes table - Harmonized System codes for global classification
    op.create_table(
        'hs_codes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('code', sa.String(12), unique=True, nullable=False, index=True),  # e.g., "0305.59"
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('chapter', sa.String(2), nullable=False, index=True),  # e.g., "03"
        sa.Column('heading', sa.String(4), nullable=True),  # e.g., "0305"
        sa.Column('category', sa.String(50), nullable=True),  # mapped category
        sa.Column('typical_unit', sa.String(20), nullable=True),  # kg, mt, etc.
        sa.Column('price_range_low', sa.Numeric(12, 4), nullable=True),
        sa.Column('price_range_high', sa.Numeric(12, 4), nullable=True),
        sa.Column('keywords', JSONB, default=list),  # for fuzzy matching
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # 3. Commodity requests table - user submissions for new commodities
    op.create_table(
        'commodity_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('requested_name', sa.String(200), nullable=False),
        sa.Column('requested_by', sa.String(100), nullable=True),  # user_id
        sa.Column('company_id', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('suggested_category', sa.String(50), nullable=True),
        sa.Column('suggested_unit', sa.String(20), nullable=True),
        sa.Column('suggested_hs_code', sa.String(12), nullable=True),
        sa.Column('suggested_price_low', sa.Numeric(12, 4), nullable=True),
        sa.Column('suggested_price_high', sa.Numeric(12, 4), nullable=True),
        sa.Column('document_reference', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), default='pending', index=True),  # pending, approved, rejected
        sa.Column('resolved_commodity_id', UUID(as_uuid=True), sa.ForeignKey('commodities.id'), nullable=True),
        sa.Column('admin_notes', sa.Text, nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # 4. Seed initial HS codes for common trade categories
    op.execute("""
        INSERT INTO hs_codes (id, code, description, chapter, heading, category, typical_unit, price_range_low, price_range_high, keywords) VALUES
        -- Chapter 03: Fish
        (gen_random_uuid(), '0301', 'Live fish', '03', '0301', 'seafood', 'kg', 2, 50, '["fish", "live fish", "aquarium fish"]'),
        (gen_random_uuid(), '0302', 'Fish, fresh or chilled', '03', '0302', 'seafood', 'kg', 3, 30, '["fish", "fresh fish", "chilled fish"]'),
        (gen_random_uuid(), '0303', 'Fish, frozen', '03', '0303', 'seafood', 'kg', 2, 25, '["fish", "frozen fish"]'),
        (gen_random_uuid(), '0304', 'Fish fillets and other fish meat', '03', '0304', 'seafood', 'kg', 5, 40, '["fish fillet", "fish meat"]'),
        (gen_random_uuid(), '0305', 'Fish, dried, salted or smoked', '03', '0305', 'seafood', 'kg', 5, 30, '["dried fish", "dry fish", "salted fish", "smoked fish", "stockfish"]'),
        (gen_random_uuid(), '0306', 'Crustaceans', '03', '0306', 'seafood', 'kg', 8, 60, '["shrimp", "crab", "lobster", "prawns"]'),
        (gen_random_uuid(), '0307', 'Molluscs', '03', '0307', 'seafood', 'kg', 5, 40, '["squid", "octopus", "clam", "mussel", "oyster"]'),
        
        -- Chapter 07: Vegetables
        (gen_random_uuid(), '0701', 'Potatoes, fresh or chilled', '07', '0701', 'vegetables', 'kg', 0.2, 2, '["potato", "potatoes"]'),
        (gen_random_uuid(), '0702', 'Tomatoes, fresh or chilled', '07', '0702', 'vegetables', 'kg', 0.5, 4, '["tomato", "tomatoes"]'),
        (gen_random_uuid(), '0703', 'Onions, shallots, garlic, leeks', '07', '0703', 'vegetables', 'kg', 0.3, 5, '["onion", "garlic", "shallot", "leek"]'),
        (gen_random_uuid(), '0713', 'Dried leguminous vegetables', '07', '0713', 'vegetables', 'kg', 0.5, 3, '["lentils", "chickpeas", "beans", "peas"]'),
        
        -- Chapter 09: Coffee, tea, spices
        (gen_random_uuid(), '0901', 'Coffee', '09', '0901', 'beverages', 'kg', 2, 30, '["coffee", "coffee beans"]'),
        (gen_random_uuid(), '0902', 'Tea', '09', '0902', 'beverages', 'kg', 2, 50, '["tea", "green tea", "black tea"]'),
        (gen_random_uuid(), '0904', 'Pepper', '09', '0904', 'spices', 'kg', 3, 15, '["pepper", "black pepper", "white pepper"]'),
        (gen_random_uuid(), '0910', 'Ginger, saffron, turmeric, other spices', '09', '0910', 'spices', 'kg', 2, 100, '["ginger", "turmeric", "saffron", "spices"]'),
        
        -- Chapter 10: Cereals
        (gen_random_uuid(), '1001', 'Wheat and meslin', '10', '1001', 'agriculture', 'mt', 200, 400, '["wheat"]'),
        (gen_random_uuid(), '1005', 'Maize (corn)', '10', '1005', 'agriculture', 'mt', 150, 350, '["maize", "corn"]'),
        (gen_random_uuid(), '1006', 'Rice', '10', '1006', 'agriculture', 'mt', 300, 900, '["rice", "paddy", "white rice", "brown rice"]'),
        
        -- Chapter 12: Oil seeds
        (gen_random_uuid(), '1201', 'Soya beans', '12', '1201', 'agriculture', 'mt', 300, 600, '["soybean", "soya", "soy"]'),
        (gen_random_uuid(), '1207', 'Other oil seeds (sesame, mustard, etc)', '12', '1207', 'agriculture', 'mt', 500, 2000, '["sesame", "mustard seeds", "sunflower seeds"]'),
        
        -- Chapter 27: Mineral fuels, oils
        (gen_random_uuid(), '2709', 'Petroleum oils, crude', '27', '2709', 'energy', 'barrel', 40, 150, '["crude oil", "petroleum", "oil"]'),
        (gen_random_uuid(), '2710', 'Petroleum oils, refined', '27', '2710', 'energy', 'barrel', 50, 180, '["diesel", "gasoline", "petrol", "fuel oil"]'),
        (gen_random_uuid(), '2711', 'Petroleum gases (LPG, LNG)', '27', '2711', 'energy', 'mt', 300, 800, '["lpg", "lng", "natural gas", "propane", "butane"]'),
        
        -- Chapter 52: Cotton
        (gen_random_uuid(), '5201', 'Cotton, not carded or combed', '52', '5201', 'textiles', 'kg', 1.5, 5, '["cotton", "raw cotton", "cotton lint"]'),
        (gen_random_uuid(), '5205', 'Cotton yarn', '52', '5205', 'textiles', 'kg', 2, 8, '["cotton yarn", "cotton thread"]'),
        
        -- Chapter 71: Precious metals
        (gen_random_uuid(), '7108', 'Gold', '71', '7108', 'precious_metals', 'oz', 1500, 2500, '["gold", "gold bullion"]'),
        (gen_random_uuid(), '7106', 'Silver', '71', '7106', 'precious_metals', 'oz', 15, 35, '["silver", "silver bullion"]'),
        
        -- Chapter 72: Iron and steel
        (gen_random_uuid(), '7207', 'Semi-finished iron/steel products', '72', '7207', 'metals', 'mt', 400, 800, '["steel", "iron", "billet", "slab"]'),
        (gen_random_uuid(), '7208', 'Flat-rolled iron/steel, hot-rolled', '72', '7208', 'metals', 'mt', 500, 1000, '["steel sheet", "steel plate", "hot rolled"]'),
        
        -- Chapter 74: Copper
        (gen_random_uuid(), '7403', 'Refined copper', '74', '7403', 'metals', 'mt', 6000, 12000, '["copper", "refined copper"]'),
        
        -- Chapter 76: Aluminium
        (gen_random_uuid(), '7601', 'Unwrought aluminium', '76', '7601', 'metals', 'mt', 1800, 3500, '["aluminium", "aluminum", "aluminium ingot"]'),
        
        -- Chapter 84: Machinery
        (gen_random_uuid(), '8471', 'Computers and data processing equipment', '84', '8471', 'electronics', 'unit', 100, 5000, '["computer", "laptop", "server"]'),
        
        -- Chapter 85: Electrical equipment
        (gen_random_uuid(), '8517', 'Telephones, smartphones', '85', '8517', 'electronics', 'unit', 50, 1500, '["phone", "smartphone", "mobile", "telephone"]'),
        
        -- Textiles
        (gen_random_uuid(), '6109', 'T-shirts, singlets', '61', '6109', 'textiles', 'dozen', 20, 200, '["tshirt", "t-shirt", "singlet"]'),
        (gen_random_uuid(), '6203', 'Mens suits, trousers', '62', '6203', 'textiles', 'dozen', 50, 500, '["suit", "trousers", "pants", "jacket"]'),
        (gen_random_uuid(), '6204', 'Womens suits, dresses', '62', '6204', 'textiles', 'dozen', 50, 500, '["dress", "skirt", "womens suit"]')
    """)


def downgrade() -> None:
    op.drop_table('commodity_requests')
    op.drop_table('hs_codes')
    op.drop_index('ix_commodities_name_lower', 'commodities')
    op.drop_table('commodities')

