# Apply AI Usage Records Migration

This guide shows how to apply the `20251116_add_ai_usage_and_events` migration to create the `ai_usage_records` and `ai_assist_events` tables.

## Option 1: Run via Render Shell (Recommended)

1. **Go to Render Dashboard** → Your `trdrhub-api` service
2. **Click "Shell"** tab (or use Render's SSH access)
3. **Run the migration**:
   ```bash
   cd /opt/render/project/src/apps/api
   alembic upgrade head
   ```

## Option 2: Run Locally Against Production DB

If you have `DIRECT_DATABASE_URL` set to your production database:

```bash
# From project root
cd apps/api

# Set production database URL (use Render's DIRECT_DATABASE_URL)
# This should be the direct connection (port 5432), not pooled (port 6543)
export DIRECT_DATABASE_URL="postgresql://postgres:password@db.project.supabase.co:5432/postgres"

# Run migration
poetry run alembic upgrade head
# OR if using pip:
# alembic upgrade head
```

**⚠️ Warning**: Only do this if you're certain `DIRECT_DATABASE_URL` points to production.

## Option 3: Manual SQL (If Alembic Fails)

If you can't run Alembic, you can execute the SQL directly:

```sql
-- Create ai_usage_records table
CREATE TABLE IF NOT EXISTS ai_usage_records (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES companies(id),
    user_id UUID REFERENCES users(id),
    validation_session_id UUID REFERENCES validation_sessions(id),
    feature VARCHAR(50) NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_ai_usage_records_tenant_id ON ai_usage_records(tenant_id);
CREATE INDEX IF NOT EXISTS ix_ai_usage_records_user_id ON ai_usage_records(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_usage_records_validation_session_id ON ai_usage_records(validation_session_id);

-- Create ai_assist_events table
CREATE TABLE IF NOT EXISTS ai_assist_events (
    id UUID PRIMARY KEY,
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

CREATE INDEX IF NOT EXISTS ix_ai_assist_events_session_id ON ai_assist_events(session_id);
CREATE INDEX IF NOT EXISTS ix_ai_assist_events_user_id ON ai_assist_events(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_assist_events_company_id ON ai_assist_events(company_id);

-- Mark migration as applied (optional, if using Alembic version table)
INSERT INTO alembic_version (version_num) 
VALUES ('20251116_add_ai_usage_and_events')
ON CONFLICT (version_num) DO NOTHING;
```

**To run this SQL:**
1. Connect to your Supabase database (use direct connection, port 5432)
2. Run the SQL in Supabase SQL Editor or via `psql`

## Option 4: Wait for Next Deployment

If you prefer, the migration will run automatically on the next Render deployment (configured in `render.yaml`):

```yaml
postDeployCommand: alembic upgrade head
```

Just push your code and Render will apply the migration during deployment.

## Verification

After applying the migration, verify the tables exist:

```sql
-- Check tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('ai_usage_records', 'ai_assist_events');

-- Check indexes
SELECT indexname 
FROM pg_indexes 
WHERE tablename IN ('ai_usage_records', 'ai_assist_events');
```

## Troubleshooting

### Error: "relation already exists"

The tables may already exist. Check with:
```sql
SELECT EXISTS (
    SELECT FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'ai_usage_records'
);
```

If they exist, the migration may have already been applied. Check Alembic version:
```sql
SELECT * FROM alembic_version;
```

### Error: "permission denied"

Ensure you're using a database user with CREATE TABLE permissions. For Supabase, use the `postgres` role or a user with appropriate privileges.

### Error: "connection refused"

- Verify `DIRECT_DATABASE_URL` uses port **5432** (direct), not 6543 (pooled)
- Check that your IP is allowed in Supabase's network restrictions
- Ensure the database is accessible from your current location

