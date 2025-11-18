-- Direct SQL to create AI usage tables (bypasses Alembic migration chain issues)
-- Run this in Supabase SQL Editor or via psql if Alembic fails

-- Create ai_usage_records table
CREATE TABLE IF NOT EXISTS ai_usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    validation_session_id UUID REFERENCES validation_sessions(id),
    feature VARCHAR(50) NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create indexes for ai_usage_records
CREATE INDEX IF NOT EXISTS ix_ai_usage_records_tenant_id ON ai_usage_records(tenant_id);
CREATE INDEX IF NOT EXISTS ix_ai_usage_records_user_id ON ai_usage_records(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_usage_records_validation_session_id ON ai_usage_records(validation_session_id);

-- Create ai_assist_events table
CREATE TABLE IF NOT EXISTS ai_assist_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES validation_sessions(id),
    user_id UUID NOT NULL REFERENCES users(id),
    company_id UUID NOT NULL REFERENCES companies(id),
    output_type VARCHAR(50) NOT NULL,
    confidence_level VARCHAR(20) NOT NULL,
    language VARCHAR(5) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    input_data JSONB NOT NULL,
    ai_output TEXT NOT NULL,
    fallback_used BOOLEAN NOT NULL DEFAULT false,
    tokens_in INTEGER,
    tokens_out INTEGER,
    estimated_cost_usd VARCHAR(20),
    lc_session_id UUID REFERENCES validation_sessions(id),
    rule_references JSONB,
    prompt_template_id VARCHAR(100) NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

-- Create indexes for ai_assist_events
CREATE INDEX IF NOT EXISTS ix_ai_assist_events_session_id ON ai_assist_events(session_id);
CREATE INDEX IF NOT EXISTS ix_ai_assist_events_user_id ON ai_assist_events(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_assist_events_company_id ON ai_assist_events(company_id);

-- Mark migration as applied (if alembic_version table exists)
-- This prevents Alembic from trying to run the migration again
INSERT INTO alembic_version (version_num) 
VALUES ('20251116_add_ai_usage_and_events')
ON CONFLICT (version_num) DO NOTHING;

