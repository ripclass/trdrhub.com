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
    # Create ruleset status enum (only if it doesn't exist)
    bind = op.get_bind()
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ruleset_status')"
    )).scalar()
    if not result:
        ruleset_status_enum = postgresql.ENUM(
            'draft', 'active', 'archived', 'scheduled',
            name='ruleset_status',
            create_type=True
        )
        ruleset_status_enum.create(bind, checkfirst=False)
    else:
        # Enum exists, create a reference for use in table definition
        ruleset_status_enum = postgresql.ENUM(
            'draft', 'active', 'archived', 'scheduled',
            name='ruleset_status',
            create_type=False
        )

    # Create audit action enum (only if it doesn't exist)
    result = bind.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ruleset_audit_action')"
    )).scalar()
    if not result:
        audit_action_enum = postgresql.ENUM(
            'upload', 'validate', 'publish', 'rollback', 'archive',
            name='ruleset_audit_action',
            create_type=True
        )
        audit_action_enum.create(bind, checkfirst=False)
    else:
        # Enum exists, create a reference for use in table definition
        audit_action_enum = postgresql.ENUM(
            'upload', 'validate', 'publish', 'rollback', 'archive',
            name='ruleset_audit_action',
            create_type=False
        )

    # Check if tables already exist
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Create rulesets table (only if it doesn't exist)
    if 'rulesets' not in existing_tables:
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

        # Create indexes (table was just created, but indexes might exist from partial migration)
        try:
            op.create_index(
                'ix_rulesets_domain_jurisdiction',
                'rulesets',
                ['domain', 'jurisdiction']
            )
        except Exception:
            pass  # Index already exists
        try:
            op.create_index(
                'ix_rulesets_status',
                'rulesets',
                ['status']
            )
        except Exception:
            pass  # Index already exists
        try:
            op.create_index(
                'ix_rulesets_created_at',
                'rulesets',
                ['created_at']
            )
        except Exception:
            pass  # Index already exists

        # Create partial unique index: one active per (domain, jurisdiction)
        op.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_rulesets_active_unique 
            ON rulesets (domain, jurisdiction) 
            WHERE status = 'active'
        """)

    # Create ruleset_audit table (only if it doesn't exist)
    if 'ruleset_audit' not in existing_tables:
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

        # Create indexes for audit table (table was just created, but indexes might exist from partial migration)
        try:
            op.create_index(
                'ix_ruleset_audit_ruleset_id',
                'ruleset_audit',
                ['ruleset_id']
            )
        except Exception:
            pass  # Index already exists
        try:
            op.create_index(
                'ix_ruleset_audit_created_at',
                'ruleset_audit',
                ['created_at']
            )
        except Exception:
            pass  # Index already exists
        try:
            op.create_index(
                'ix_ruleset_audit_action',
                'ruleset_audit',
                ['action']
            )
        except Exception:
            pass  # Index already exists


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

