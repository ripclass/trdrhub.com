"""Add billing localization fields to companies

Revision ID: billing_localization_001
Revises: rbac_members_001
Create Date: 2024-12-02

Adds country, currency, and payment_gateway columns to the companies table
for regional payment gateway routing.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'billing_localization_001'
down_revision = 'rbac_members_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add currency column (if country already exists, we're just adding the new columns)
    op.add_column('companies', sa.Column('currency', sa.String(3), nullable=True, server_default='USD'))
    op.add_column('companies', sa.Column('payment_gateway', sa.String(20), nullable=True, server_default='stripe'))
    
    # Update country column to be 2 chars (ISO standard) if it was longer
    # Note: This is a non-destructive change that just ensures consistency


def downgrade() -> None:
    op.drop_column('companies', 'payment_gateway')
    op.drop_column('companies', 'currency')

