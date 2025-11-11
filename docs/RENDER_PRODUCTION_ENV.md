# Render Production Environment Variables

**Date:** 2025-01-27  
**Purpose:** Complete list of environment variables required for production deployment on Render

## Critical Variables (Required)

### 1. Disable Stub Mode
```bash
USE_STUBS=false
```
**Why:** Without this, the app uses mock data instead of real OCR/storage.  
**Impact:** OCR and file storage will fail in production.

### 2. Database (Supabase PostgreSQL)
```bash
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:6543/postgres
DIRECT_DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres
```
**Why:** `DATABASE_URL` is required for app runtime (port 6543 = pooled).  
**Why:** `DIRECT_DATABASE_URL` is required for migrations (port 5432 = direct).  
**Impact:** App won't start without `DATABASE_URL`. Migrations will fail without `DIRECT_DATABASE_URL`.

### 3. Authentication (Supabase)
```bash
SUPABASE_ISSUER=https://your-project.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_JWKS_URL=https://your-project.supabase.co/auth/v1/.well-known/jwks.json
```
**Why:** Required for JWT token validation.  
**Impact:** Authentication will fail without these.

### 4. Security
```bash
SECRET_KEY=your-secure-random-secret-key-here
```
**Why:** Used for signing tokens, sessions. **MUST NOT** be the default `"dev-secret-key-change-in-production"`.  
**Impact:** Security vulnerability if default is used. App logs a critical warning in production.

### 5. Google Cloud Document AI (OCR) - Required if USE_STUBS=false
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_DOCUMENTAI_LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/apps/api/gcp-key.json
```
**Why:** Required for OCR processing. `DocumentAIService` raises `ValueError` if missing.  
**Impact:** OCR will fail. App logs startup warning if missing.  
**Note:** For Render, upload the service account JSON key file and set the path, OR use Render's Secret Files feature.

### 6. AWS S3 (File Storage) - Required if USE_STUBS=false
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=lcopilot-documents
```
**Why:** Required for file uploads/downloads. `S3Service` initializes boto3 client which needs credentials.  
**Impact:** File operations will fail. `TextractFallback` raises `ConfigError` if AWS credentials missing.

## Production Environment Settings

```bash
ENVIRONMENT=production
DEBUG=false
```
**Why:** Enables production-specific behavior (security headers, error handling, CORS validation).  
**Impact:** Security warnings if `ENVIRONMENT` is not `production`.

## CORS Configuration

```bash
CORS_ALLOW_ORIGINS=https://trdrhub.com,https://www.trdrhub.com,https://trdrhub.vercel.app
```
**Why:** Restricts which frontend domains can access the API.  
**Impact:** CORS errors if frontend domain not in list. Defaults to `["*"]` if not set (insecure in production).

## Frontend URL (Optional but Recommended)

```bash
FRONTEND_URL=https://trdrhub.com
API_BASE_URL=https://api.trdrhub.com
```
**Why:** Used for generating links in emails/notifications.  
**Impact:** Links may point to wrong domain if not set.

## AI/LLM Configuration (Optional - for AI features)

```bash
# Choose one provider:
LLM_PROVIDER=openai  # or "anthropic"
OPENAI_API_KEY=sk-...  # if LLM_PROVIDER=openai
ANTHROPIC_API_KEY=sk-ant-...  # if LLM_PROVIDER=anthropic
LLM_MODEL_VERSION=gpt-4o-mini  # OpenAI model
ANTHROPIC_MODEL_VERSION=claude-3-haiku-20240307  # Anthropic model
AI_ENRICHMENT=true  # Enable AI enrichment in validation
```
**Why:** Required for AI features (letter generation, summaries, translations, chat).  
**Impact:** AI features will fail with `ValueError("OpenAI API key not configured")` or `ValueError("Anthropic API key not configured")`.

## Rules System (Optional)

```bash
USE_JSON_RULES=true  # Enable JSON ruleset validation
RULESET_CACHE_TTL_MINUTES=10
```
**Why:** Enables JSON-based ruleset validation instead of database rules.  
**Impact:** Uses database rules if `false` or not set.

## RulHub Integration (Optional - Phase 7)

```bash
USE_RULHUB_API=false
RULHUB_API_URL=https://api.rulhub.com
RULHUB_API_KEY=your-rulhub-api-key
```
**Why:** External rules API integration.  
**Impact:** Not used if `false` or not set.

## Payment Providers (Optional - for billing)

### Stripe
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PROFESSIONAL=price_...
STRIPE_PRICE_ENTERPRISE=price_...
```

### SSLCommerz
```bash
SSLCOMMERZ_STORE_ID=your-store-id
SSLCOMMERZ_STORE_PASSWORD=your-store-password
SSLCOMMERZ_SANDBOX=false  # Set to false for production
```

## Rate Limiting (Optional - has defaults)

```bash
API_RATE_LIMIT=100
API_RATE_WINDOW=60
AI_RATE_LIMIT_PER_USER_PER_MIN=10
AI_RATE_LIMIT_PER_TENANT_PER_MIN=50
AI_MIN_INTERVAL_PER_LC_MS=2000
```

## Bank 2FA (Optional)

```bash
ENABLE_BANK_2FA=false
BANK_SESSION_IDLE_TIMEOUT_MINUTES=30
```

## Supabase Additional (Optional - if using Supabase Storage)

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```
**Why:** Required if using Supabase Storage for rules (`RulesStorage` raises `ValueError` if missing).  
**Impact:** Rules storage operations will fail without these.

## Render-Specific Setup Steps

### 1. Add Environment Variables in Render Dashboard

1. Go to your Render service → **Environment** tab
2. Click **Add Environment Variable**
3. Add each variable from the **Critical Variables** section above
4. For sensitive values (keys, secrets), use Render's **Secret** toggle

### 2. Upload Google Service Account Key

**Option A: Using Render Secret Files**
1. Go to **Environment** tab
2. Scroll to **Secret Files** section
3. Upload your `gcp-key.json` file
4. Set `GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/apps/api/gcp-key.json`

**Option B: Using Environment Variable (Base64)**
1. Base64 encode your JSON key: `cat gcp-key.json | base64`
2. Set environment variable: `GOOGLE_CREDENTIALS_BASE64=<base64-string>`
3. Modify code to decode and write to file on startup (not recommended)

### 3. Verify Configuration

After deployment, check `/health/info` endpoint:
```bash
curl https://your-api.render.com/health/info
```

Look for:
- `"use_stubs": false`
- `"environment": "production"`
- No warnings about missing Google/AWS config

## Complete Render Environment Variables Checklist

Copy-paste this into Render's Environment tab:

```bash
# ============================================
# CRITICAL: Production Settings
# ============================================
USE_STUBS=false
ENVIRONMENT=production
DEBUG=false

# ============================================
# Database (Supabase)
# ============================================
DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:6543/postgres
DIRECT_DATABASE_URL=postgresql://postgres:password@db.project.supabase.co:5432/postgres

# ============================================
# Authentication (Supabase)
# ============================================
SUPABASE_ISSUER=https://your-project.supabase.co/auth/v1
SUPABASE_AUDIENCE=authenticated
SUPABASE_JWKS_URL=https://your-project.supabase.co/auth/v1/.well-known/jwks.json

# ============================================
# Security
# ============================================
SECRET_KEY=CHANGE-THIS-TO-A-SECURE-RANDOM-STRING

# ============================================
# Google Cloud Document AI (OCR)
# ============================================
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_DOCUMENTAI_PROCESSOR_ID=your-processor-id
GOOGLE_DOCUMENTAI_LOCATION=us
GOOGLE_APPLICATION_CREDENTIALS=/opt/render/project/src/apps/api/gcp-key.json

# ============================================
# AWS S3 (File Storage)
# ============================================
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
S3_BUCKET_NAME=lcopilot-documents

# ============================================
# CORS
# ============================================
CORS_ALLOW_ORIGINS=https://trdrhub.com,https://www.trdrhub.com,https://trdrhub.vercel.app

# ============================================
# Frontend URLs
# ============================================
FRONTEND_URL=https://trdrhub.com
API_BASE_URL=https://api.trdrhub.com

# ============================================
# AI/LLM (Optional)
# ============================================
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL_VERSION=gpt-4o-mini
AI_ENRICHMENT=true
```

## What Will Fail Without These Variables

| Variable | Failure Mode |
|----------|-------------|
| `USE_STUBS=false` + Missing Google OCR | OCR processing fails, startup warning |
| `USE_STUBS=false` + Missing AWS S3 | File uploads/downloads fail |
| Missing `DATABASE_URL` | App won't start |
| Missing `SECRET_KEY` (or default) | Security vulnerability, critical warning |
| Missing `SUPABASE_JWKS_URL` | Authentication fails |
| Missing `GOOGLE_CLOUD_PROJECT` | `DocumentAIService` raises `ValueError` |
| Missing `AWS_ACCESS_KEY_ID` | `TextractFallback` raises `ConfigError` |

## Post-Deployment Verification

1. **Check Health Endpoint:**
   ```bash
   curl https://your-api.render.com/health/info
   ```
   Should show `"use_stubs": false` and no warnings.

2. **Test OCR Upload:**
   - Upload a test LC document
   - Should process with real OCR (not stub)

3. **Check Logs:**
   - No warnings about missing Google/AWS config
   - No "Stub mode enabled in production" warnings

4. **Test Authentication:**
   - Login should work
   - JWT tokens should validate

## Notes

- **Google Credentials:** Render doesn't support mounting files easily. Use Secret Files feature or base64 encode and decode on startup.
- **AWS Credentials:** Can use IAM roles if Render supports it, otherwise use access keys.
- **Database:** Supabase uses port 6543 for pooled connections (app runtime) and 5432 for direct connections (migrations).
- **CORS:** Must include all frontend domains (production, staging, preview deployments).

