"""
Merge active Day3 validation heads and reconcile required schema columns.

This migration is intentionally non-destructive:
- adds users.auth_user_id when absent
- adds companies.type when absent
- creates supporting non-unique/partial-index artifacts only if needed
- does not drop existing data
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "20260302_merge_day3_validate_schema"
down_revision = ("sanctions_001", "20260227_day1_p0_failclosed")
branch_labels = None
depends_on = None



def upgrade() -> None:
    bind = op.get_bind()

    # Add missing columns defensively for non-destructive / partially-migrated environments.
    bind.execute(sa.text("ALTER TABLE IF EXISTS public.users ADD COLUMN IF NOT EXISTS auth_user_id UUID;"))
    bind.execute(sa.text("ALTER TABLE IF EXISTS public.companies ADD COLUMN IF NOT EXISTS type TEXT;"))
    bind.execute(
        sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_auth_user_id "
            "ON public.users(auth_user_id) WHERE auth_user_id IS NOT NULL;"
        )
    )
    bind.execute(sa.text("UPDATE public.companies SET type = COALESCE(type, 'sme') WHERE type IS NULL;"))

    # Optional auth users FK bridge when Supabase auth schema is present.
    bind.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='auth' AND table_name='users'
              ) THEN
                IF NOT EXISTS (
                  SELECT 1
                  FROM pg_constraint
                  WHERE conname = 'fk_users_auth_user_id'
                ) THEN
                  ALTER TABLE public.users
                    ADD CONSTRAINT fk_users_auth_user_id
                    FOREIGN KEY (auth_user_id)
                    REFERENCES auth.users(id)
                    ON DELETE SET NULL;
                END IF;
              END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    bind.execute(sa.text("ALTER TABLE IF EXISTS public.users DROP CONSTRAINT IF EXISTS fk_users_auth_user_id;"))
    bind.execute(sa.text("DROP INDEX IF EXISTS public.ux_users_auth_user_id;"))
    bind.execute(sa.text("ALTER TABLE IF EXISTS public.companies DROP COLUMN IF EXISTS type;"))
    bind.execute(sa.text("ALTER TABLE IF EXISTS public.users DROP COLUMN IF EXISTS auth_user_id;"))
