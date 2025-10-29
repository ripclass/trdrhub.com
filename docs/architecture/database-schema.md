# Database Schema

A normalized PostgreSQL schema will be used, defined and managed with a migration tool (Alembic) from day one. To protect the audit trail, critical tables like validation_sessions and reports will use a soft-delete pattern (deleted_at column) instead of ON DELETE CASCADE.
