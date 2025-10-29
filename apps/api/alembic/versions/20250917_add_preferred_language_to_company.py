"""Add preferred_language field to Company table

Revision ID: 20250917_001
Revises: 20250916_170100_seed_default_companies
Create Date: 2025-09-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250917_001'
down_revision = '20250916_170100_seed_default_companies'
branch_labels = None
depends_on = None


def upgrade():
    # Create Language enum
    language_enum = postgresql.ENUM(
        'en', 'bn', 'ar', 'hi', 'ur', 'zh', 'fr', 'de', 'ms',
        name='languagetype'
    )
    language_enum.create(op.get_bind())

    # Add preferred_language column to companies table
    op.add_column(
        'companies',
        sa.Column(
            'preferred_language',
            language_enum,
            nullable=False,
            server_default='en'
        )
    )

    # Create index for faster lookups
    op.create_index(
        'ix_companies_preferred_language',
        'companies',
        ['preferred_language']
    )


def downgrade():
    # Drop index
    op.drop_index('ix_companies_preferred_language', table_name='companies')

    # Drop column
    op.drop_column('companies', 'preferred_language')

    # Drop enum
    language_enum = postgresql.ENUM(name='languagetype')
    language_enum.drop(op.get_bind())