"""Bulk validation infra — Phase A1 part 2.

Creates the bulk-job table family (``bulk_jobs``, ``bulk_items``,
``bulk_failures``, ``job_events``, ``bulk_templates``) that previously
existed only as ORM definitions in ``app/models/bulk_jobs.py`` with no
backing migration. Without this migration the bank-side bulk processor
silently no-ops in production because the queue is a stub and the
tables don't exist.

Then adds nullable FKs ``bulk_job_id`` and ``bulk_item_id`` on
``validation_sessions`` so customer bulk children can be reverse-
looked-up — given a BulkJob, fetch every spawned ValidationSession;
given a ValidationSession, find which BulkItem produced it (NULL for
sessions created via the single-LC upload path).

Revision ID: 20260426_add_validation_session_bulk_link
Revises: 20260425_add_lc_lifecycle
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260426_add_validation_session_bulk_link"
down_revision = "20260425_add_lc_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Create bulk_jobs table.
    # ------------------------------------------------------------------
    op.create_table(
        "bulk_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("bank_alias", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("total_items", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("processed_items", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("succeeded_items", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("failed_items", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("skipped_items", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("progress_percent", sa.DECIMAL(5, 2), nullable=True, server_default=sa.text("0.00")),
        sa.Column("estimated_completion", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("resume_token", sa.String(length=128), nullable=True),
        sa.Column("checkpoint_data", postgresql.JSONB(), nullable=True),
        sa.Column("s3_manifest_bucket", sa.String(length=128), nullable=True),
        sa.Column("s3_manifest_key", sa.String(length=512), nullable=True),
        sa.Column("s3_results_bucket", sa.String(length=128), nullable=True),
        sa.Column("s3_results_key", sa.String(length=512), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("throughput_items_per_sec", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("peak_memory_mb", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bulk_jobs_tenant_id", "bulk_jobs", ["tenant_id"])
    op.create_index("ix_bulk_jobs_bank_alias", "bulk_jobs", ["bank_alias"])
    op.create_index("ix_bulk_jobs_tenant_status", "bulk_jobs", ["tenant_id", "status"])
    op.create_index("ix_bulk_jobs_created_at", "bulk_jobs", ["created_at"])
    op.create_index("ix_bulk_jobs_priority", "bulk_jobs", ["priority", "created_at"])

    # ------------------------------------------------------------------
    # 2. Create bulk_items table.
    # ------------------------------------------------------------------
    op.create_table(
        "bulk_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulk_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lc_identifier", sa.String(length=128), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=True),
        sa.Column("item_data", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=True, server_default=sa.text("3")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("result_data", postgresql.JSONB(), nullable=True),
        sa.Column("output_files", postgresql.JSONB(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_category", sa.String(length=32), nullable=True),
        sa.Column("retriable", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bulk_items_idempotency_key", "bulk_items", ["idempotency_key"])
    op.create_index("ix_bulk_items_job_status", "bulk_items", ["job_id", "status"])
    op.create_index("ix_bulk_items_identifier", "bulk_items", ["job_id", "lc_identifier"])
    op.create_index("ix_bulk_items_idempotency", "bulk_items", ["idempotency_key"])

    # ------------------------------------------------------------------
    # 3. Create bulk_failures table.
    # ------------------------------------------------------------------
    op.create_table(
        "bulk_failures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulk_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_details", postgresql.JSONB(), nullable=True),
        sa.Column("error_category", sa.String(length=32), nullable=False),
        sa.Column("error_severity", sa.String(length=16), nullable=False),
        sa.Column("retriable", sa.Boolean(), nullable=False),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("execution_context", postgresql.JSONB(), nullable=True),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index("ix_bulk_failures_item", "bulk_failures", ["item_id"])
    op.create_index("ix_bulk_failures_code", "bulk_failures", ["error_code"])
    op.create_index("ix_bulk_failures_category", "bulk_failures", ["error_category"])

    # ------------------------------------------------------------------
    # 4. Create job_events table.
    # ------------------------------------------------------------------
    op.create_table(
        "job_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulk_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index("ix_job_events_job_type", "job_events", ["job_id", "event_type"])
    op.create_index("ix_job_events_created", "job_events", ["created_at"])

    # ------------------------------------------------------------------
    # 5. Create bulk_templates table.
    # ------------------------------------------------------------------
    op.create_table(
        "bulk_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("config_template", postgresql.JSONB(), nullable=False),
        sa.Column("manifest_schema", postgresql.JSONB(), nullable=True),
        sa.Column("validation_rules", postgresql.JSONB(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("allowed_roles", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bulk_templates_tenant_id", "bulk_templates", ["tenant_id"])
    op.create_index("ix_bulk_templates_tenant_type", "bulk_templates", ["tenant_id", "job_type"])
    op.create_index("ix_bulk_templates_usage", "bulk_templates", ["usage_count", "last_used_at"])

    # ------------------------------------------------------------------
    # 6. Add validation_sessions back-references to bulk job/item.
    # ------------------------------------------------------------------
    op.add_column(
        "validation_sessions",
        sa.Column(
            "bulk_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulk_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "validation_sessions",
        sa.Column(
            "bulk_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bulk_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_validation_sessions_bulk_job_id",
        "validation_sessions",
        ["bulk_job_id"],
    )
    op.create_index(
        "ix_validation_sessions_bulk_item_id",
        "validation_sessions",
        ["bulk_item_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_sessions_bulk_item_id", table_name="validation_sessions")
    op.drop_index("ix_validation_sessions_bulk_job_id", table_name="validation_sessions")
    op.drop_column("validation_sessions", "bulk_item_id")
    op.drop_column("validation_sessions", "bulk_job_id")

    op.drop_index("ix_bulk_templates_usage", table_name="bulk_templates")
    op.drop_index("ix_bulk_templates_tenant_type", table_name="bulk_templates")
    op.drop_index("ix_bulk_templates_tenant_id", table_name="bulk_templates")
    op.drop_table("bulk_templates")

    op.drop_index("ix_job_events_created", table_name="job_events")
    op.drop_index("ix_job_events_job_type", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index("ix_bulk_failures_category", table_name="bulk_failures")
    op.drop_index("ix_bulk_failures_code", table_name="bulk_failures")
    op.drop_index("ix_bulk_failures_item", table_name="bulk_failures")
    op.drop_table("bulk_failures")

    op.drop_index("ix_bulk_items_idempotency", table_name="bulk_items")
    op.drop_index("ix_bulk_items_identifier", table_name="bulk_items")
    op.drop_index("ix_bulk_items_job_status", table_name="bulk_items")
    op.drop_index("ix_bulk_items_idempotency_key", table_name="bulk_items")
    op.drop_table("bulk_items")

    op.drop_index("ix_bulk_jobs_priority", table_name="bulk_jobs")
    op.drop_index("ix_bulk_jobs_created_at", table_name="bulk_jobs")
    op.drop_index("ix_bulk_jobs_tenant_status", table_name="bulk_jobs")
    op.drop_index("ix_bulk_jobs_bank_alias", table_name="bulk_jobs")
    op.drop_index("ix_bulk_jobs_tenant_id", table_name="bulk_jobs")
    op.drop_table("bulk_jobs")
