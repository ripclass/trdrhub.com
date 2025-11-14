"""Ensure companies table has billing + metadata columns used by ORM."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision = "20251114_add_contact_email_to_companies"
down_revision = "20251031_add_user_roles_bank_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table_name: str, column_name: str) -> bool:
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


PLAN_ENUM_NAME = "plan_type"
PLAN_VALUES = (
    "free",
    "pay_per_check",
    "monthly_basic",
    "monthly_pro",
    "enterprise",
)

STATUS_ENUM_NAME = "company_status"
STATUS_VALUES = (
    "active",
    "delinquent",
    "suspended",
    "trial",
)

LANG_ENUM_NAME = "language_type"
LANG_VALUES = (
    "en",
    "bn",
    "ar",
    "hi",
    "ur",
    "zh",
    "fr",
    "de",
    "ms",
)


def _ensure_enum(bind, name: str, values: tuple[str, ...]) -> None:
    enum_type = sa.Enum(*values, name=name)
    enum_type.create(bind, checkfirst=True)


def _drop_enum(bind, name: str) -> None:
    bind.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = :enum_name) THEN
                    DROP TYPE IF EXISTS """ + name + """ CASCADE;
                END IF;
            END $$;
            """
        ),
        {"enum_name": name},
    )


def upgrade() -> None:
    bind = op.get_bind()
    # Ensure enums exist before columns referencing them
    _ensure_enum(bind, PLAN_ENUM_NAME, PLAN_VALUES)
    _ensure_enum(bind, STATUS_ENUM_NAME, STATUS_VALUES)
    _ensure_enum(bind, LANG_ENUM_NAME, LANG_VALUES)

    columns_to_add = [
        (
            "contact_email",
            sa.String(length=255),
            True,
            None,
        ),
        (
            "plan",
            sa.Enum(*PLAN_VALUES, name=PLAN_ENUM_NAME, create_type=False),
            False,
            "free",
        ),
        ("quota_limit", sa.Integer(), True, None),
        ("billing_cycle_start", sa.Date(), True, None),
        ("payment_provider_id", sa.String(length=255), True, None),
        (
            "status",
            sa.Enum(*STATUS_VALUES, name=STATUS_ENUM_NAME, create_type=False),
            False,
            "active",
        ),
        (
            "preferred_language",
            sa.Enum(*LANG_VALUES, name=LANG_ENUM_NAME, create_type=False),
            False,
            "en",
        ),
        ("event_metadata", postgresql.JSONB(), True, None),
        ("business_address", sa.Text(), True, None),
        ("tax_id", sa.String(length=100), True, None),
    ]

    for name, column_type, nullable, default in columns_to_add:
        if _has_column(bind, "companies", name):
            continue

        column = sa.Column(
            name,
            column_type,
            nullable=nullable,
            server_default=sa.text(f"'{default}'") if default is not None else None,
        )
        op.add_column("companies", column)

        if default is not None:
            op.execute(
                sa.text(
                    f"ALTER TABLE companies ALTER COLUMN {name} DROP DEFAULT"
                )
            )

    if not bool(
        bind.execute(
            sa.text(
                """
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'companies'
                  AND indexname = 'idx_companies_payment_provider_id'
                """
            )
        ).scalar()
    ):
        op.create_index(
            "idx_companies_payment_provider_id",
            "companies",
            ["payment_provider_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = [
        "tax_id",
        "business_address",
        "event_metadata",
        "preferred_language",
        "status",
        "payment_provider_id",
        "billing_cycle_start",
        "quota_limit",
        "plan",
        "contact_email",
    ]
    for column_name in columns:
        if _has_column(bind, "companies", column_name):
            op.drop_column("companies", column_name)

    _drop_enum(bind, PLAN_ENUM_NAME)
    _drop_enum(bind, STATUS_ENUM_NAME)
    _drop_enum(bind, LANG_ENUM_NAME)


