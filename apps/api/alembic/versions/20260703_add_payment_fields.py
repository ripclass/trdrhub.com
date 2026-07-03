"""Add concierge payment fields to validation_sessions — Phase 5 launch.

Stripe Checkout (hosted) fires at intake submission; the job holds at
review_state=submitted (invisible to the operator queue, which lists
engine_complete/under_review/needs_info) until the checkout.session.completed
webhook stamps payment_status='paid' and advances it. Refunds performed in
the Stripe dashboard land back here as payment_status='refunded' via the
charge.refunded webhook.

payment_status semantics:
    NULL       — payment not required (legacy self-serve / flag off)
    'pending'  — checkout created or required, not yet paid
    'paid'     — checkout.session.completed received
    'refunded' — charge.refunded received

Revision ID: 20260703_add_payment_fields
Revises: 20260703_add_report_review
Create Date: 2026-07-03
"""

from alembic import op
import sqlalchemy as sa

revision = "20260703_add_payment_fields"
down_revision = "20260703_add_report_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("validation_sessions", sa.Column("payment_status", sa.String(20), nullable=True))
    op.add_column("validation_sessions", sa.Column("payment_product_id", sa.String(50), nullable=True))
    op.add_column("validation_sessions", sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True))
    op.add_column("validation_sessions", sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True))
    op.add_column("validation_sessions", sa.Column("amount_paid_cents", sa.Integer(), nullable=True))
    op.add_column("validation_sessions", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("validation_sessions", sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_validation_sessions_payment_status", "validation_sessions", ["payment_status"])
    op.create_index(
        "ix_validation_sessions_stripe_checkout_session_id",
        "validation_sessions", ["stripe_checkout_session_id"],
    )
    op.create_index(
        "ix_validation_sessions_stripe_payment_intent_id",
        "validation_sessions", ["stripe_payment_intent_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_sessions_stripe_payment_intent_id", table_name="validation_sessions")
    op.drop_index("ix_validation_sessions_stripe_checkout_session_id", table_name="validation_sessions")
    op.drop_index("ix_validation_sessions_payment_status", table_name="validation_sessions")
    op.drop_column("validation_sessions", "refunded_at")
    op.drop_column("validation_sessions", "paid_at")
    op.drop_column("validation_sessions", "amount_paid_cents")
    op.drop_column("validation_sessions", "stripe_payment_intent_id")
    op.drop_column("validation_sessions", "stripe_checkout_session_id")
    op.drop_column("validation_sessions", "payment_product_id")
    op.drop_column("validation_sessions", "payment_status")
