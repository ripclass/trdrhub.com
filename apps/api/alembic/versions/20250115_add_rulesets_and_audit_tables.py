"""Add rulesets and ruleset_audit tables

Revision ID: 20250115_add_rulesets_and_audit_tables
Revises: 20251031_add_user_roles_bank_tables
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250115_add_rulesets_and_audit_tables'
down_revision = '20251031_add_user_roles_bank_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ruleset status enum
    ruleset_status_enum = postgresql.ENUM(
        'draft', 'active', 'archived', 'scheduled',
        name='ruleset_status',
        create_type=True
    )
    ruleset_status_enum.create(op.get_bind(), checkfirst=True)

    # Create audit action enum
    audit_action_enum = postgresql.ENUM(
        'upload', 'validate', 'publish', 'rollback', 'archive',
        name='ruleset_audit_action',
        create_type=True
    )
    audit_action_enum.create(op.get_bind(), checkfirst=True)

    # Create rulesets table
    op.create_table(
        'rulesets',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column('domain', sa.String(length=50), nullable=False),
        sa.Column('jurisdiction', sa.String(length=50), nullable=False, server_default='global'),
        sa.Column('ruleset_version', sa.String(length=50), nullable=False),
        sa.Column('rulebook_version', sa.String(length=50), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column(
            'status',
            ruleset_status_enum,
            nullable=False,
            server_default='draft'
        ),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checksum_md5', sa.String(length=32), nullable=False),
        sa.Column('rule_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'created_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
        sa.Column(
            'published_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )

    # Create indexes
    op.create_index(
        'ix_rulesets_domain_jurisdiction',
        'rulesets',
        ['domain', 'jurisdiction']
    )
    op.create_index(
        'ix_rulesets_status',
        'rulesets',
        ['status']
    )
    op.create_index(
        'ix_rulesets_created_at',
        'rulesets',
        ['created_at']
    )

    # Create partial unique index: one active per (domain, jurisdiction)
    op.execute("""
        CREATE UNIQUE INDEX ix_rulesets_active_unique 
        ON rulesets (domain, jurisdiction) 
        WHERE status = 'active'
    """)

    # Create ruleset_audit table
    op.create_table(
        'ruleset_audit',
        sa.Column(
            'id',
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text('gen_random_uuid()'),
        ),
        sa.Column(
            'ruleset_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('rulesets.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column(
            'action',
            audit_action_enum,
            nullable=False
        ),
        sa.Column(
            'actor_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column('detail', postgresql.JSONB, nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False
        ),
    )

    # Create indexes for audit table
    op.create_index(
        'ix_ruleset_audit_ruleset_id',
        'ruleset_audit',
        ['ruleset_id']
    )
    op.create_index(
        'ix_ruleset_audit_created_at',
        'ruleset_audit',
        ['created_at']
    )
    op.create_index(
        'ix_ruleset_audit_action',
        'ruleset_audit',
        ['action']
    )


def downgrade() -> None:
    op.drop_index('ix_ruleset_audit_action', table_name='ruleset_audit')
    op.drop_index('ix_ruleset_audit_created_at', table_name='ruleset_audit')
    op.drop_index('ix_ruleset_audit_ruleset_id', table_name='ruleset_audit')
    op.drop_table('ruleset_audit')

    op.drop_index('ix_rulesets_active_unique', table_name='rulesets')
    op.drop_index('ix_rulesets_created_at', table_name='rulesets')
    op.drop_index('ix_rulesets_status', table_name='rulesets')
    op.drop_index('ix_rulesets_domain_jurisdiction', table_name='rulesets')
    op.drop_table('rulesets')

    op.execute("DROP TYPE IF EXISTS ruleset_audit_action")
    op.execute("DROP TYPE IF EXISTS ruleset_status")

