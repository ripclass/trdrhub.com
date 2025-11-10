-- Migration: Add bank_policy_application_events table for analytics
-- Revision: 20250122_add_bank_policy_application_events
-- Down Revision: 20250121_add_bank_policy_overlays

-- Create bank_policy_application_events table
CREATE TABLE IF NOT EXISTS bank_policy_application_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_session_id UUID NOT NULL REFERENCES validation_sessions(id),
    bank_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    overlay_id UUID REFERENCES bank_policy_overlays(id) ON DELETE SET NULL,
    overlay_version INTEGER,
    exception_id UUID REFERENCES bank_policy_exceptions(id) ON DELETE SET NULL,
    application_type VARCHAR(20) NOT NULL,  -- overlay, exception, both
    rule_code VARCHAR(100),
    exception_effect VARCHAR(20),  -- waive, downgrade, override
    discrepancies_before INTEGER NOT NULL DEFAULT 0,
    discrepancies_after INTEGER NOT NULL DEFAULT 0,
    severity_changes JSONB,
    result_summary JSONB,
    document_type VARCHAR(50),
    processing_time_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_policy_app_bank_created ON bank_policy_application_events(bank_id, created_at);
CREATE INDEX IF NOT EXISTS ix_policy_app_overlay_created ON bank_policy_application_events(overlay_id, created_at);
CREATE INDEX IF NOT EXISTS ix_policy_app_exception_created ON bank_policy_application_events(exception_id, created_at);
CREATE INDEX IF NOT EXISTS ix_policy_app_session ON bank_policy_application_events(validation_session_id);

