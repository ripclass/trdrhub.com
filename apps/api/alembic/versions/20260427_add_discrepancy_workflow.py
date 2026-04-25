"""Discrepancy resolution workflow + re-papering loop — Phase A2.

Extends the legacy ``discrepancies`` table with state-machine columns
+ ownership + resolution metadata, and adds two new tables:

  * ``discrepancy_comments``  — append-only thread per discrepancy.
  * ``repapering_requests``   — token-authed loop for asking a counterparty
                                  (supplier, agent, internal team) to fix
                                  a flagged document and re-upload.

All new columns on ``discrepancies`` are nullable except ``state``,
which has a server_default of ``'raised'`` so existing rows backfill
atomically.

Revision ID: 20260427_add_discrepancy_workflow
Revises: 20260426_add_validation_session_bulk_link
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260427_add_discrepancy_workflow"
down_revision = "20260426_add_validation_session_bulk_link"
branch_labels = None
depends_on = None


# Allowed discrepancy states. Mirrored in
# ``app/models/discrepancy_workflow.py::DiscrepancyState``.
_DISCREPANCY_STATES = (
    "raised",          # default — examiner flagged it, no action yet
    "acknowledged",    # user has seen it
    "responded",       # user posted a comment / explanation
    "accepted",        # user accepts the discrepancy as valid (must fix)
    "rejected",        # user disputes — bank/admin will decide
    "waived",          # admin/bank waived the rule
    "repaper",         # re-papering loop kicked off
    "resolved",        # corrected docs validated clean
)

_RESOLUTION_ACTIONS = ("accept", "reject", "waive", "repaper", "resolved")

_REPAPER_STATES = (
    "requested",       # email sent, awaiting recipient
    "in_progress",     # recipient opened the link
    "corrected",       # recipient uploaded files
    "resolved",        # re-validation cleared the original discrepancy
    "cancelled",       # requester cancelled before resolution
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extend discrepancies table.
    # ------------------------------------------------------------------
    op.add_column(
        "discrepancies",
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default="raised",
        ),
    )
    op.add_column(
        "discrepancies",
        sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discrepancies",
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "discrepancies",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discrepancies",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discrepancies",
        sa.Column("resolution_action", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "discrepancies",
        sa.Column(
            "resolution_evidence_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "discrepancies",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_discrepancies_state_valid",
        "discrepancies",
        "state IN (" + ", ".join(f"'{s}'" for s in _DISCREPANCY_STATES) + ")",
    )
    op.create_check_constraint(
        "ck_discrepancies_resolution_action_valid",
        "discrepancies",
        "resolution_action IS NULL OR resolution_action IN ("
        + ", ".join(f"'{s}'" for s in _RESOLUTION_ACTIONS)
        + ")",
    )
    op.create_index(
        "ix_discrepancies_state",
        "discrepancies",
        ["state"],
    )
    op.create_index(
        "ix_discrepancies_owner_user_id",
        "discrepancies",
        ["owner_user_id"],
    )

    # ------------------------------------------------------------------
    # 2. discrepancy_comments — append-only thread.
    # ------------------------------------------------------------------
    op.create_table(
        "discrepancy_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "discrepancy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discrepancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Author-side bookkeeping for comments from non-platform users
        # (re-papering recipients): we record their email + display name
        # in case they don't have an account.
        sa.Column("author_email", sa.String(length=320), nullable=True),
        sa.Column("author_display_name", sa.String(length=128), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        # Where the comment came from. UI renders these differently —
        # 'system' messages are deemphasized.
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default="user",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_discrepancy_comments_source_valid",
        "discrepancy_comments",
        "source IN ('user', 'recipient', 'system')",
    )
    op.create_index(
        "ix_discrepancy_comments_discrepancy_created",
        "discrepancy_comments",
        ["discrepancy_id", "created_at"],
    )

    # ------------------------------------------------------------------
    # 3. repapering_requests — token-authed correction loop.
    # ------------------------------------------------------------------
    op.create_table(
        "repapering_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "discrepancy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discrepancies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requester_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_email", sa.String(length=320), nullable=False),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recipient_display_name", sa.String(length=128), nullable=True),
        # Long-lived random token. Recipient hits /repaper/{token}/upload.
        # Indexed unique. ~256 bits of entropy.
        sa.Column(
            "access_token",
            sa.String(length=64),
            nullable=False,
            unique=True,
        ),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default="requested",
        ),
        sa.Column(
            "replacement_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("validation_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_repapering_requests_state_valid",
        "repapering_requests",
        "state IN (" + ", ".join(f"'{s}'" for s in _REPAPER_STATES) + ")",
    )
    op.create_index(
        "ix_repapering_requests_token",
        "repapering_requests",
        ["access_token"],
        unique=True,
    )
    op.create_index(
        "ix_repapering_requests_discrepancy",
        "repapering_requests",
        ["discrepancy_id"],
    )
    op.create_index(
        "ix_repapering_requests_state",
        "repapering_requests",
        ["state"],
    )


def downgrade() -> None:
    op.drop_index("ix_repapering_requests_state", table_name="repapering_requests")
    op.drop_index("ix_repapering_requests_discrepancy", table_name="repapering_requests")
    op.drop_index("ix_repapering_requests_token", table_name="repapering_requests")
    op.drop_table("repapering_requests")

    op.drop_index("ix_discrepancy_comments_discrepancy_created", table_name="discrepancy_comments")
    op.drop_table("discrepancy_comments")

    op.drop_index("ix_discrepancies_owner_user_id", table_name="discrepancies")
    op.drop_index("ix_discrepancies_state", table_name="discrepancies")
    op.drop_constraint(
        "ck_discrepancies_resolution_action_valid",
        "discrepancies",
        type_="check",
    )
    op.drop_constraint(
        "ck_discrepancies_state_valid",
        "discrepancies",
        type_="check",
    )
    op.drop_column("discrepancies", "updated_at")
    op.drop_column("discrepancies", "resolution_evidence_session_id")
    op.drop_column("discrepancies", "resolution_action")
    op.drop_column("discrepancies", "resolved_at")
    op.drop_column("discrepancies", "acknowledged_at")
    op.drop_column("discrepancies", "owner_user_id")
    op.drop_column("discrepancies", "state_changed_at")
    op.drop_column("discrepancies", "state")
