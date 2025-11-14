"""Add auth_user_id column to users and backfill from Supabase auth.users."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20251115_add_auth_user_id_to_users"
down_revision = "20251114_add_contact_email_to_companies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "users", "auth_user_id"):
        op.add_column(
            "users",
            sa.Column(
                "auth_user_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                unique=True,
            ),
        )

    # Backfill auth_user_id by matching emails between auth.users and public.users
    op.execute(
        """
        UPDATE users
        SET auth_user_id = auth_u.id
        FROM auth.users AS auth_u
        WHERE auth_u.email = users.email
          AND users.auth_user_id IS NULL;
        """
    )

    # Ensure FK for future writes
    op.create_foreign_key(
        "fk_users_auth_user_id",
        "users",
        "auth.users",
        ["auth_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_auth_user_id", type_="foreignkey")

    if _has_column(bind, "users", "auth_user_id"):
        op.drop_column("users", "auth_user_id")

