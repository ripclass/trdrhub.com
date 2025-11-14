"""Add contact_email column to companies table if missing."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20251114_add_contact_email_to_companies"
down_revision = "20251031_add_user_roles_bank_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "companies", "contact_email"):
        op.add_column(
            "companies",
            sa.Column("contact_email", sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "companies", "contact_email"):
        op.drop_column("companies", "contact_email")

